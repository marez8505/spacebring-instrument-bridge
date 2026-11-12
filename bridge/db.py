import sqlite3
import os
from pathlib import Path
from datetime import datetime

DEFAULT_DB_PATH = Path(os.environ.get("LAB_BRIDGE_DB", Path.home() / ".lab_bridge" / "lab_bridge.db"))

def get_db_connection(db_path: Path = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Path = None):
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS companies (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        plan_tier TEXT DEFAULT 'Standard',
        status TEXT DEFAULT 'Active',
        contact_email TEXT,
        source_file TEXT,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS members (
        id TEXT PRIMARY KEY,
        company_id TEXT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE,
        role TEXT DEFAULT 'Member',
        status TEXT DEFAULT 'Active',
        source_file TEXT,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS instruments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT,
        hourly_rate REAL DEFAULT 0.0,
        min_booking_minutes INTEGER DEFAULT 30,
        requires_training INTEGER DEFAULT 1,
        min_training_level TEXT DEFAULT 'Basic',
        status TEXT DEFAULT 'Available',
        model TEXT,
        serial_number TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS qualifications (
        id TEXT PRIMARY KEY,
        member_id TEXT NOT NULL,
        instrument_id TEXT NOT NULL,
        training_level TEXT DEFAULT 'Basic',
        certified_date TEXT,
        expires_date TEXT,
        certified_by TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
        FOREIGN KEY (instrument_id) REFERENCES instruments(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS reservations (
        id TEXT PRIMARY KEY,
        instrument_id TEXT NOT NULL,
        member_id TEXT NOT NULL,
        company_id TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        actual_start TEXT,
        actual_end TEXT,
        duration_hours REAL DEFAULT 0.0,
        hourly_rate REAL DEFAULT 0.0,
        total_cost REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Scheduled',
        notes TEXT,
        billed INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (instrument_id) REFERENCES instruments(id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS sync_logs (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        source_path TEXT NOT NULL,
        sync_type TEXT NOT NULL,
        companies_synced INTEGER DEFAULT 0,
        members_synced INTEGER DEFAULT 0,
        details TEXT
    );
    """)

    conn.commit()
    conn.close()

def seed_default_instruments(db_path: Path = None):
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM instruments")
    count = cur.fetchone()[0]
    if count == 0:
        now = datetime.now().isoformat()
        sample_instruments = [
            ("INST-FLOW-01", "BD FACSCelesta Flow Cytometer", "Cytometry", "Room 204 - Bay A", 75.0, 30, 1, "Certified Operator", "Available", "FACSCelesta 3-Laser", "BD-98214", now),
            ("INST-HPLC-01", "Agilent 1260 Infinity II HPLC", "Chromatography", "Room 206 - Core Lab", 60.0, 60, 1, "Advanced", "Available", "1260 Infinity II", "AG-55102", now),
            ("INST-CENT-01", "Thermo Sorvall LYNX 6000 Centrifuge", "Centrifugation", "Room 202 - General Prep", 25.0, 30, 1, "Basic", "Available", "Sorvall LYNX 6000", "TH-33921", now),
            ("INST-MICR-01", "Nikon Eclipse Ti2-E Confocal Microscope", "Imaging", "Room 208 - Dark Room", 90.0, 60, 1, "Advanced", "Available", "Eclipse Ti2-E", "NK-77189", now),
            ("INST-PCR-01", "Bio-Rad CFX96 Touch Real-Time PCR", "Molecular Biology", "Room 202 - Prep Bench 4", 35.0, 45, 1, "Basic", "Available", "CFX96 Touch", "BR-12847", now),
            ("INST-AUTO-01", "Getinge Steam Sterilizer Autoclave", "Sterilization", "Wash Facility B1", 15.0, 30, 0, "None", "Available", "G-100LS", "GT-00122", now)
        ]
        cur.executemany("""
            INSERT INTO instruments (id, name, category, location, hourly_rate, min_booking_minutes, requires_training, min_training_level, status, model, serial_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_instruments)
        conn.commit()
    conn.close()
