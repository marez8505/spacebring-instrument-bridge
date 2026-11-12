import csv
import json
import os
import uuid
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

from .db import get_db_connection

def clean_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", key.strip().lower())

def normalize_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    return {clean_key(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

def parse_csv_or_tsv(file_path: Path) -> List[Dict[str, Any]]:
    delimiter = "\t" if file_path.suffix.lower() == ".tsv" else ","
    rows = []
    with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            rows.append(normalize_dict(row))
    return rows

def parse_json_file(file_path: Path) -> List[Dict[str, Any]]:
    with open(file_path, mode="r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [normalize_dict(item) if isinstance(item, dict) else {} for item in data]
    elif isinstance(data, dict):
        for key in ["users", "members", "companies", "customers", "data", "results", "items"]:
            if key in data and isinstance(data[key], list):
                return [normalize_dict(item) if isinstance(item, dict) else {} for item in data[key]]
        return [normalize_dict(data)]
    return []

def extract_company_info(record: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    # Returns (id, name, plan_tier, status, contact_email)
    name = (
        record.get("company_name") or
        record.get("company") or
        record.get("organization") or
        record.get("account_name") or
        record.get("account") or
        ""
    )
    comp_id = (
        record.get("company_id") or
        record.get("organization_id") or
        record.get("account_id") or
        ""
    )
    if not comp_id and name:
        comp_id = "comp-" + re.sub(r"[^a-z0-9]", "-", name.lower()).strip("-")

    plan = (
        record.get("plan_tier") or
        record.get("plan") or
        record.get("membership_plan") or
        record.get("tier") or
        "Standard"
    )
    status = record.get("company_status") or record.get("status") or "Active"
    contact = record.get("company_email") or record.get("billing_email") or record.get("email") or ""

    return comp_id, name, plan, status, contact

def extract_member_info(record: Dict[str, Any], default_company_id: str = "") -> Tuple[str, str, str, str, str, str]:
    # Check if record has any member-identifying attributes
    has_member_field = any([
        record.get("full_name"),
        record.get("name"),
        record.get("member_name"),
        record.get("first_name"),
        record.get("last_name"),
        record.get("member_id"),
        record.get("user_id"),
        record.get("member_email")
    ])
    if not has_member_field:
        return "", "", "", "", "", ""

    first = record.get("first_name", "")
    last = record.get("last_name", "")
    name = record.get("full_name") or record.get("name") or record.get("member_name")
    if not name and (first or last):
        name = f"{first} {last}".strip()
    if not name:
        return "", "", "", "", "", ""

    email = record.get("member_email") or record.get("email") or ""
    email = email.strip() or None

    mem_id = record.get("member_id") or record.get("user_id") or record.get("id") or ""
    if not mem_id:
        if email:
            mem_id = "mem-" + re.sub(r"[^a-z0-9]", "-", email.lower()).strip("-")
        else:
            mem_id = f"mem-{uuid.uuid4().hex[:8]}"

    comp_id = record.get("company_id") or default_company_id
    if not comp_id:
        c_name = record.get("company") or record.get("company_name") or record.get("organization") or ""
        if c_name:
            comp_id = "comp-" + re.sub(r"[^a-z0-9]", "-", c_name.lower()).strip("-")

    role = record.get("role") or record.get("title") or record.get("job_title") or "Member"
    status = record.get("member_status") or record.get("status") or "Active"

    return mem_id, comp_id, name, email, role, status

class SpacebringImporter:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path

    def import_file(self, file_path: str | Path) -> Dict[str, Any]:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        if ext in [".csv", ".tsv"]:
            records = parse_csv_or_tsv(path)
        elif ext in [".json"]:
            records = parse_json_file(path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported formats are .csv, .tsv, .json")

        return self._process_records(records, source_name=str(path), sync_type="File")

    def import_folder(self, folder_path: str | Path) -> Dict[str, Any]:
        folder = Path(folder_path).resolve()
        if not folder.exists() or not folder.is_dir():
            raise NotADirectoryError(f"Directory not found: {folder}")

        all_records = []
        files_found = []
        for ext in ("*.csv", "*.tsv", "*.json"):
            for f in folder.rglob(ext):
                files_found.append(f)
                try:
                    if f.suffix.lower() in [".csv", ".tsv"]:
                        recs = parse_csv_or_tsv(f)
                    else:
                        recs = parse_json_file(f)
                    for r in recs:
                        r["_source_file_path"] = str(f)
                    all_records.extend(recs)
                except Exception as e:
                    print(f"Warning: Failed parsing {f}: {e}")

        if not files_found:
            return {
                "success": True,
                "message": "No CSV or JSON files found in directory.",
                "files_scanned": 0,
                "companies_synced": 0,
                "members_synced": 0
            }

        result = self._process_records(all_records, source_name=str(folder), sync_type="Folder")
        result["files_scanned"] = len(files_found)
        return result

    def _process_records(self, records: List[Dict[str, Any]], source_name: str, sync_type: str) -> Dict[str, Any]:
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        now = datetime.now().isoformat()

        companies_synced = 0
        members_synced = 0

        # Step 1: Ingest companies
        for r in records:
            c_id, c_name, c_plan, c_status, c_contact = extract_company_info(r)
            if c_id and c_name:
                cur.execute("""
                    INSERT INTO companies (id, name, plan_tier, status, contact_email, source_file, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        plan_tier=excluded.plan_tier,
                        status=excluded.status,
                        contact_email=CASE WHEN excluded.contact_email != '' THEN excluded.contact_email ELSE companies.contact_email END,
                        source_file=excluded.source_file,
                        updated_at=excluded.updated_at
                """, (c_id, c_name, c_plan, c_status, c_contact, source_name, now, now))
                companies_synced += 1

        # Step 2: Ingest members
        for r in records:
            m_id, m_comp_id, m_name, m_email, m_role, m_status = extract_member_info(r)
            if not m_name:
                continue

            # Ensure foreign key validity if company exists
            if m_comp_id:
                cur.execute("SELECT id FROM companies WHERE id = ?", (m_comp_id,))
                if not cur.fetchone():
                    m_comp_id = None

            # Check if member exists by email or id
            existing_id = None
            if m_email:
                cur.execute("SELECT id FROM members WHERE email = ?", (m_email,))
                row = cur.fetchone()
                if row:
                    existing_id = row["id"]
            if not existing_id and m_id:
                cur.execute("SELECT id FROM members WHERE id = ?", (m_id,))
                row = cur.fetchone()
                if row:
                    existing_id = row["id"]

            if existing_id:
                cur.execute("""
                    UPDATE members
                    SET company_id = COALESCE(?, company_id),
                        full_name = ?,
                        email = COALESCE(?, email),
                        role = ?,
                        status = ?,
                        source_file = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (m_comp_id, m_name, m_email, m_role, m_status, source_name, now, existing_id))
            else:
                cur.execute("""
                    INSERT INTO members (id, company_id, full_name, email, role, status, source_file, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (m_id, m_comp_id, m_name, m_email, m_role, m_status, source_name, now, now))
            members_synced += 1

        # Step 3: Record sync log
        log_id = f"log-{uuid.uuid4().hex[:8]}"
        cur.execute("""
            INSERT INTO sync_logs (id, timestamp, source_path, sync_type, companies_synced, members_synced, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (log_id, now, source_name, sync_type, companies_synced, members_synced, f"Processed {len(records)} raw data records."))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "source": source_name,
            "sync_type": sync_type,
            "companies_synced": companies_synced,
            "members_synced": members_synced,
            "total_records_processed": len(records)
        }
