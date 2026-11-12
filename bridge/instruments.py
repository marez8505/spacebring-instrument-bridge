import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from .db import get_db_connection

class InstrumentManager:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path

    def list_instruments(self, category: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        query = "SELECT * FROM instruments WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY category ASC, name ASC"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_instrument(self, instrument_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM instruments WHERE id = ?", (instrument_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_instrument(self, name: str, category: str, location: str, hourly_rate: float,
                          min_booking_minutes: int = 30, requires_training: bool = True,
                          min_training_level: str = "Basic", status: str = "Available",
                          model: str = "", serial_number: str = "", custom_id: str = "") -> Dict[str, Any]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        inst_id = custom_id or f"INST-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO instruments (id, name, category, location, hourly_rate, min_booking_minutes, requires_training, min_training_level, status, model, serial_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (inst_id, name, category, location, float(hourly_rate), int(min_booking_minutes), 1 if requires_training else 0, min_training_level, status, model, serial_number, now))
        conn.commit()
        conn.close()
        return self.get_instrument(inst_id)

    def update_instrument(self, instrument_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        allowed_fields = ["name", "category", "location", "hourly_rate", "min_booking_minutes", "requires_training", "min_training_level", "status", "model", "serial_number"]
        updates = []
        params = []
        for key, val in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                params.append(val)
        if not updates:
            return self.get_instrument(instrument_id)
        params.append(instrument_id)

        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(f"UPDATE instruments SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()
        return self.get_instrument(instrument_id)

    def delete_instrument(self, instrument_id: str) -> bool:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM instruments WHERE id = ?", (instrument_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
