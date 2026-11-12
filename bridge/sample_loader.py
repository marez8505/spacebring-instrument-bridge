import uuid
from datetime import datetime, timedelta, date
from pathlib import Path
from .db import get_db_connection, seed_default_instruments

def load_all_sample_data(db_path: Path = None):
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    now = datetime.now()
    now_iso = now.isoformat()

    seed_default_instruments(db_path)

    # 1. Companies (as exported from Spacebring)
    companies = [
        ("comp-biosynthetix", "BioSynthetix Therapeutics", "Dedicated Lab 4B", "Active", "billing@biosynthetix.com", "sample_export_spacebring.csv", now_iso, now_iso),
        ("comp-neurovance", "NeuroVance Diagnostics", "Dedicated Bench A2", "Active", "ops@neurovance-bio.com", "sample_export_spacebring.csv", now_iso, now_iso),
        ("comp-kura", "Kura Oncology Solutions", "Flex Coworking + Wet Lab", "Active", "ap@kuraoncology.com", "sample_export_spacebring.csv", now_iso, now_iso),
        ("comp-verdant", "Verdant AgTech", "Private Suite 101", "Past Due", "finance@verdantag.io", "sample_export_spacebring.csv", now_iso, now_iso)
    ]
    cur.executemany("""
        INSERT INTO companies (id, name, plan_tier, status, contact_email, source_file, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET name=excluded.name, plan_tier=excluded.plan_tier, status=excluded.status
    """, companies)

    # 2. Members (as exported from Spacebring)
    members = [
        ("mem-elena", "comp-biosynthetix", "Dr. Elena Rostova", "elena@biosynthetix.com", "Lead Scientist", "Active", "sample_export_spacebring.csv", now_iso, now_iso),
        ("mem-marcus", "comp-biosynthetix", "Marcus Chen", "marcus.chen@biosynthetix.com", "Research Associate", "Active", "sample_export_spacebring.csv", now_iso, now_iso),
        ("mem-sarah", "comp-neurovance", "Dr. Sarah Jenkins", "sarah@neurovance-bio.com", "Founder & CSO", "Active", "sample_export_spacebring.csv", now_iso, now_iso),
        ("mem-tyler", "comp-neurovance", "Tyler Vance", "tyler.vance@neurovance-bio.com", "Lab Technician", "Active", "sample_export_spacebring.csv", now_iso, now_iso),
        ("mem-priya", "comp-kura", "Priya Patel", "priya@kuraoncology.com", "Senior Scientist", "Active", "sample_export_spacebring.csv", now_iso, now_iso),
        ("mem-david", "comp-verdant", "David Thorne", "david@verdantag.io", "Director", "Suspended", "sample_export_spacebring.csv", now_iso, now_iso)
    ]
    cur.executemany("""
        INSERT INTO members (id, company_id, full_name, email, role, status, source_file, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET full_name=excluded.full_name, company_id=excluded.company_id, role=excluded.role, status=excluded.status
    """, members)

    # 3. Qualifications
    next_year = (date.today() + timedelta(days=365)).isoformat()
    quals = [
        ("QUAL-001", "mem-elena", "INST-FLOW-01", "Certified Operator", date.today().isoformat(), next_year, "Lab Director", "Fully certified on 3-laser panel configuration", now_iso),
        ("QUAL-002", "mem-elena", "INST-HPLC-01", "Advanced", date.today().isoformat(), next_year, "Core Lab Tech", "Method development clearance granted", now_iso),
        ("QUAL-003", "mem-marcus", "INST-CENT-01", "Basic", date.today().isoformat(), next_year, "Safety Officer", "High-speed rotor balance certified", now_iso),
        ("QUAL-004", "mem-sarah", "INST-MICR-01", "Advanced", date.today().isoformat(), next_year, "Lab Director", "Confocal live-cell imaging certified", now_iso),
        ("QUAL-005", "mem-sarah", "INST-PCR-01", "Basic", date.today().isoformat(), next_year, "Core Lab Tech", "SYBR & TaqMan assay clearance", now_iso),
        ("QUAL-006", "mem-priya", "INST-FLOW-01", "Certified Operator", date.today().isoformat(), next_year, "Lab Director", "Immunophenotyping specialist", now_iso)
    ]
    cur.executemany("""
        INSERT INTO qualifications (id, member_id, instrument_id, training_level, certified_date, expires_date, certified_by, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
    """, quals)

    # 4. Realistic Usage & Reservations (Completed + Unbilled for immediate reconciliation demonstration)
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)
    three_days_ago = now - timedelta(days=3)
    tomorrow = now + timedelta(days=1)

    reservations = [
        # Elena on Flow Cytometer (BioSynthetix) - 3.5 hrs @ $75/hr = $262.50
        ("RES-001", "INST-FLOW-01", "mem-elena", "comp-biosynthetix",
         three_days_ago.strftime("%Y-%m-%dT09:00:00"), three_days_ago.strftime("%Y-%m-%dT12:30:00"),
         three_days_ago.strftime("%Y-%m-%dT09:05:00"), three_days_ago.strftime("%Y-%m-%dT12:35:00"),
         3.5, 75.0, 262.50, "Completed", "Antibody titration panel run", 0, now_iso),

        # Sarah on Confocal Microscope (NeuroVance) - 2.0 hrs @ $90/hr = $180.00
        ("RES-002", "INST-MICR-01", "mem-sarah", "comp-neurovance",
         two_days_ago.strftime("%Y-%m-%dT13:00:00"), two_days_ago.strftime("%Y-%m-%dT15:00:00"),
         two_days_ago.strftime("%Y-%m-%dT13:00:00"), two_days_ago.strftime("%Y-%m-%dT15:00:00"),
         2.0, 90.0, 180.00, "Completed", "Fluorescent neuron staining imaging", 0, now_iso),

        # Elena on HPLC (BioSynthetix) - 4.0 hrs @ $60/hr = $240.00
        ("RES-003", "INST-HPLC-01", "mem-elena", "comp-biosynthetix",
         yesterday.strftime("%Y-%m-%dT10:00:00"), yesterday.strftime("%Y-%m-%dT14:00:00"),
         yesterday.strftime("%Y-%m-%dT10:00:00"), yesterday.strftime("%Y-%m-%dT14:00:00"),
         4.0, 60.0, 240.00, "Completed", "Peptide purity assay", 0, now_iso),

        # Priya on Flow Cytometer (Kura Oncology) - 2.5 hrs @ $75/hr = $187.50
        ("RES-004", "INST-FLOW-01", "mem-priya", "comp-kura",
         yesterday.strftime("%Y-%m-%dT14:30:00"), yesterday.strftime("%Y-%m-%dT17:00:00"),
         yesterday.strftime("%Y-%m-%dT14:30:00"), yesterday.strftime("%Y-%m-%dT17:00:00"),
         2.5, 75.0, 187.50, "Completed", "CAR-T receptor screening", 0, now_iso),

        # Scheduled upcoming reservation for tomorrow
        ("RES-005", "INST-MICR-01", "mem-sarah", "comp-neurovance",
         tomorrow.strftime("%Y-%m-%dT10:00:00"), tomorrow.strftime("%Y-%m-%dT12:00:00"),
         None, None, 2.0, 90.0, 180.00, "Scheduled", "Z-stack confocal series", 0, now_iso)
    ]

    cur.executemany("""
        INSERT INTO reservations (id, instrument_id, member_id, company_id, start_time, end_time, actual_start, actual_end, duration_hours, hourly_rate, total_cost, status, notes, billed, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
    """, reservations)

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Sample Spacebring companies, members, qualifications, and instrument bookings loaded successfully.",
        "companies_seeded": len(companies),
        "members_seeded": len(members),
        "qualifications_seeded": len(quals),
        "reservations_seeded": len(reservations)
    }
