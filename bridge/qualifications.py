import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from .db import get_db_connection

TRAINING_LEVEL_HIERARCHY = {
    "None": 0,
    "Basic": 1,
    "Advanced": 2,
    "Certified Operator": 3
}

class QualificationManager:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path

    def assign_certification(self, member_id: str, instrument_id: str, training_level: str = "Basic",
                             certified_date: Optional[str] = None, expires_date: Optional[str] = None,
                             certified_by: str = "Lab Admin", notes: str = "") -> Dict[str, Any]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()

        # Check if certification already exists
        cur.execute("SELECT id FROM qualifications WHERE member_id = ? AND instrument_id = ?", (member_id, instrument_id))
        row = cur.fetchone()

        now = datetime.now().isoformat()
        c_date = certified_date or date.today().isoformat()

        if row:
            qual_id = row["id"]
            cur.execute("""
                UPDATE qualifications
                SET training_level = ?, certified_date = ?, expires_date = ?, certified_by = ?, notes = ?
                WHERE id = ?
            """, (training_level, c_date, expires_date, certified_by, notes, qual_id))
        else:
            qual_id = f"QUAL-{uuid.uuid4().hex[:6].upper()}"
            cur.execute("""
                INSERT INTO qualifications (id, member_id, instrument_id, training_level, certified_date, expires_date, certified_by, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (qual_id, member_id, instrument_id, training_level, c_date, expires_date, certified_by, notes, now))

        conn.commit()
        conn.close()
        return self.get_qualification(qual_id)

    def get_qualification(self, qual_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT q.*, m.full_name as member_name, m.email as member_email, c.name as company_name, i.name as instrument_name
            FROM qualifications q
            JOIN members m ON q.member_id = m.id
            LEFT JOIN companies c ON m.company_id = c.id
            JOIN instruments i ON q.instrument_id = i.id
            WHERE q.id = ?
        """, (qual_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def list_qualifications(self, instrument_id: Optional[str] = None, member_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        query = """
            SELECT q.*, m.full_name as member_name, m.email as member_email, c.name as company_name, i.name as instrument_name
            FROM qualifications q
            JOIN members m ON q.member_id = m.id
            LEFT JOIN companies c ON m.company_id = c.id
            JOIN instruments i ON q.instrument_id = i.id
            WHERE 1=1
        """
        params = []
        if instrument_id:
            query += " AND q.instrument_id = ?"
            params.append(instrument_id)
        if member_id:
            query += " AND q.member_id = ?"
            params.append(member_id)

        query += " ORDER BY q.certified_date DESC"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def verify_operator_eligibility(self, member_id: str, instrument_id: str) -> Tuple[bool, str]:
        """
        Verifies if a Spacebring member is authorized to book or operate an instrument.
        Returns (is_eligible, reason_message)
        """
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()

        # Check instrument
        cur.execute("SELECT * FROM instruments WHERE id = ?", (instrument_id,))
        inst = cur.fetchone()
        if not inst:
            conn.close()
            return False, f"Instrument {instrument_id} does not exist."

        # Check member and status
        cur.execute("SELECT m.*, c.status as company_status FROM members m LEFT JOIN companies c ON m.company_id = c.id WHERE m.id = ?", (member_id,))
        mem = cur.fetchone()
        if not mem:
            conn.close()
            return False, f"Member {member_id} does not exist."

        if mem["status"] != "Active":
            conn.close()
            return False, f"Spacebring member account status is '{mem['status']}'. Must be 'Active'."

        if mem["company_status"] and mem["company_status"] not in ["Active", "Good Standing"]:
            conn.close()
            return False, f"Member's Spacebring company account is suspended or inactive ('{mem['company_status']}')."

        if not inst["requires_training"]:
            conn.close()
            return True, "No specific training certification required for this instrument."

        # Check training certification
        cur.execute("SELECT * FROM qualifications WHERE member_id = ? AND instrument_id = ?", (member_id, instrument_id))
        qual = cur.fetchone()
        conn.close()

        if not qual:
            return False, f"Missing required certification. Required level: '{inst['min_training_level']}'."

        required_rank = TRAINING_LEVEL_HIERARCHY.get(inst["min_training_level"], 1)
        actual_rank = TRAINING_LEVEL_HIERARCHY.get(qual["training_level"], 0)

        if actual_rank < required_rank:
            return False, f"Insufficient certification rank: has '{qual['training_level']}', but requires '{inst['min_training_level']}'."

        if qual["expires_date"]:
            try:
                exp = datetime.fromisoformat(qual["expires_date"]).date()
                if exp < date.today():
                    return False, f"Certification expired on {qual['expires_date']}."
            except Exception:
                pass

        return True, f"Verified eligible ({qual['training_level']} certification active)."
