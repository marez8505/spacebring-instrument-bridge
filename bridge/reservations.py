import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from .db import get_db_connection
from .qualifications import QualificationManager

class ReservationManager:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path
        self.qual_mgr = QualificationManager(db_path)

    def create_reservation(self, instrument_id: str, member_id: str, start_time: str, end_time: str,
                           notes: str = "", bypass_training_check: bool = False) -> Dict[str, Any]:
        """
        Creates an instrument reservation. Verifies operator certification before booking.
        """
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()

        # Step 1: Verify eligibility
        if not bypass_training_check:
            eligible, reason = self.qual_mgr.verify_operator_eligibility(member_id, instrument_id)
            if not eligible:
                conn.close()
                raise PermissionError(f"Booking rejected: {reason}")

        # Step 2: Fetch instrument rate and member company
        cur.execute("SELECT * FROM instruments WHERE id = ?", (instrument_id,))
        inst = cur.fetchone()
        if not inst:
            conn.close()
            raise ValueError(f"Instrument {instrument_id} not found.")

        cur.execute("SELECT company_id FROM members WHERE id = ?", (member_id,))
        mem = cur.fetchone()
        company_id = mem["company_id"] if mem else None

        # Step 3: Check collision
        cur.execute("""
            SELECT id FROM reservations
            WHERE instrument_id = ?
              AND status IN ('Scheduled', 'Active')
              AND NOT (end_time <= ? OR start_time >= ?)
        """, (instrument_id, start_time, end_time))
        collision = cur.fetchone()
        if collision:
            conn.close()
            raise ValueError(f"Time slot collision: Instrument is already reserved during this window ({collision['id']}).")

        # Step 4: Calculate duration and cost
        t_start = datetime.fromisoformat(start_time)
        t_end = datetime.fromisoformat(end_time)
        duration_hours = max(0.0, (t_end - t_start).total_seconds() / 3600.0)
        hourly_rate = inst["hourly_rate"]
        total_cost = round(duration_hours * hourly_rate, 2)

        res_id = f"RES-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now().isoformat()

        cur.execute("""
            INSERT INTO reservations (id, instrument_id, member_id, company_id, start_time, end_time, duration_hours, hourly_rate, total_cost, status, notes, billed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (res_id, instrument_id, member_id, company_id, start_time, end_time, duration_hours, hourly_rate, total_cost, 'Scheduled', notes, now))

        conn.commit()
        conn.close()
        return self.get_reservation(res_id)

    def get_reservation(self, res_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*,
                   i.name as instrument_name, i.location as instrument_location, i.category as instrument_category,
                   m.full_name as member_name, m.email as member_email,
                   c.name as company_name, c.plan_tier as company_plan
            FROM reservations r
            JOIN instruments i ON r.instrument_id = i.id
            JOIN members m ON r.member_id = m.id
            LEFT JOIN companies c ON r.company_id = c.id
            WHERE r.id = ?
        """, (res_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def list_reservations(self, instrument_id: Optional[str] = None, company_id: Optional[str] = None,
                          member_id: Optional[str] = None, status: Optional[str] = None,
                          billed: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        query = """
            SELECT r.*,
                   i.name as instrument_name, i.location as instrument_location,
                   m.full_name as member_name, m.email as member_email,
                   c.name as company_name, c.plan_tier as company_plan
            FROM reservations r
            JOIN instruments i ON r.instrument_id = i.id
            JOIN members m ON r.member_id = m.id
            LEFT JOIN companies c ON r.company_id = c.id
            WHERE 1=1
        """
        params = []
        if instrument_id:
            query += " AND r.instrument_id = ?"
            params.append(instrument_id)
        if company_id:
            query += " AND r.company_id = ?"
            params.append(company_id)
        if member_id:
            query += " AND r.member_id = ?"
            params.append(member_id)
        if status:
            query += " AND r.status = ?"
            params.append(status)
        if billed is not None:
            query += " AND r.billed = ?"
            params.append(billed)

        query += " ORDER BY r.start_time DESC"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def check_in(self, res_id: str) -> Dict[str, Any]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute("""
            UPDATE reservations
            SET status = 'Active', actual_start = ?
            WHERE id = ? AND status = 'Scheduled'
        """, (now, res_id))
        conn.commit()
        conn.close()
        return self.get_reservation(res_id)

    def check_out(self, res_id: str) -> Dict[str, Any]:
        res = self.get_reservation(res_id)
        if not res:
            raise ValueError(f"Reservation {res_id} not found.")

        now = datetime.now().isoformat()
        actual_start_str = res.get("actual_start") or res["start_time"]
        t_start = datetime.fromisoformat(actual_start_str)
        t_end = datetime.fromisoformat(now)
        actual_duration = max(0.25, round((t_end - t_start).total_seconds() / 3600.0, 2))
        total_cost = round(actual_duration * res["hourly_rate"], 2)

        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            UPDATE reservations
            SET status = 'Completed', actual_end = ?, duration_hours = ?, total_cost = ?
            WHERE id = ?
        """, (now, actual_duration, total_cost, res_id))
        conn.commit()
        conn.close()
        return self.get_reservation(res_id)

    def cancel_reservation(self, res_id: str, reason: str = "") -> Dict[str, Any]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            UPDATE reservations
            SET status = 'Cancelled', notes = CASE WHEN notes != '' THEN notes || ' | ' || ? ELSE ? END
            WHERE id = ?
        """, (f"Cancelled: {reason}", f"Cancelled: {reason}", res_id))
        conn.commit()
        conn.close()
        return self.get_reservation(res_id)
