import csv
import json
import io
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from .db import get_db_connection

class BillingReconciliationManager:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path

    def get_unbilled_summary_by_company(self) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COALESCE(c.id, 'UNASSIGNED') as company_id,
                COALESCE(c.name, 'Independent / Unassigned') as company_name,
                c.plan_tier,
                c.contact_email,
                COUNT(r.id) as reservation_count,
                ROUND(SUM(r.duration_hours), 2) as total_instrument_hours,
                ROUND(SUM(r.total_cost), 2) as total_amount_due
            FROM reservations r
            LEFT JOIN companies c ON r.company_id = c.id
            WHERE r.status = 'Completed' AND r.billed = 0
            GROUP BY c.id
            ORDER BY total_amount_due DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_company_itemized_ledger(self, company_id: str, include_billed: bool = False) -> Dict[str, Any]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        company = cur.fetchone()
        comp_dict = dict(company) if company else {"id": company_id, "name": "Unknown", "plan_tier": "N/A"}

        query = """
            SELECT r.*,
                   i.name as instrument_name, i.category as instrument_category,
                   m.full_name as member_name, m.email as member_email
            FROM reservations r
            JOIN instruments i ON r.instrument_id = i.id
            JOIN members m ON r.member_id = m.id
            WHERE r.company_id = ? AND r.status = 'Completed'
        """
        if not include_billed:
            query += " AND r.billed = 0"
        query += " ORDER BY r.start_time ASC"

        cur.execute(query, (company_id,))
        items = [dict(r) for r in cur.fetchall()]

        total_hours = sum(item["duration_hours"] for item in items)
        total_cost = sum(item["total_cost"] for item in items)

        conn.close()
        return {
            "company": comp_dict,
            "period_generated": datetime.now().isoformat(),
            "item_count": len(items),
            "total_hours": round(total_hours, 2),
            "total_cost": round(total_cost, 2),
            "line_items": items
        }

    def export_spacebring_invoice_csv(self, company_id: Optional[str] = None) -> str:
        """
        Exports a CSV formatted specifically for importing into Spacebring as invoice line items.
        Format includes: Customer/Company Name, Member, Item Description, Quantity (Hours), Unit Price, Total, Date
        """
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()

        query = """
            SELECT r.id as booking_id,
                   c.name as company_name,
                   c.contact_email as company_email,
                   m.full_name as member_name,
                   i.name as instrument_name,
                   r.start_time,
                   r.end_time,
                   r.duration_hours,
                   r.hourly_rate,
                   r.total_cost
            FROM reservations r
            JOIN instruments i ON r.instrument_id = i.id
            JOIN members m ON r.member_id = m.id
            LEFT JOIN companies c ON r.company_id = c.id
            WHERE r.status = 'Completed' AND r.billed = 0
        """
        params = []
        if company_id:
            query += " AND r.company_id = ?"
            params.append(company_id)
        query += " ORDER BY c.name, r.start_time"

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Invoice Batch ID",
            "Spacebring Company",
            "Member / Operator",
            "Line Item Description",
            "Date",
            "Duration (Hours)",
            "Rate ($/hr)",
            "Line Total ($)",
            "Reference Booking ID"
        ])

        batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d')}"
        for row in rows:
            date_str = row["start_time"].split("T")[0] if "T" in row["start_time"] else row["start_time"][:10]
            desc = f"Lab Equipment Usage: {row['instrument_name']}"
            writer.writerow([
                batch_id,
                row["company_name"] or "Independent Member",
                row["member_name"],
                desc,
                date_str,
                f"{row['duration_hours']:.2f}",
                f"{row['hourly_rate']:.2f}",
                f"{row['total_cost']:.2f}",
                row["booking_id"]
            ])

        return output.getvalue()

    def mark_batch_billed(self, reservation_ids: List[str]) -> int:
        if not reservation_ids:
            return 0
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        placeholders = ",".join(["?"] * len(reservation_ids))
        cur.execute(f"UPDATE reservations SET billed = 1 WHERE id IN ({placeholders})", reservation_ids)
        updated = cur.rowcount
        conn.commit()
        conn.close()
        return updated
