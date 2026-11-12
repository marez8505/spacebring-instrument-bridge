import http.server
import json
import urllib.parse
import os
import mimetypes
from pathlib import Path
from typing import Dict, Any

from .db import init_db, seed_default_instruments, get_db_connection
from .importer import SpacebringImporter
from .instruments import InstrumentManager
from .qualifications import QualificationManager
from .reservations import ReservationManager
from .billing import BillingReconciliationManager

class BridgeAPIHandler(http.server.SimpleHTTPRequestHandler):
    db_path = None
    frontend_dir = Path(__file__).parent / "static"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.frontend_dir), **kwargs)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, content_type: str = "text/plain", status: int = 200, filename: str = None):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if not path.startswith("/api/"):
            return super().do_GET()

        inst_mgr = InstrumentManager(self.db_path)
        qual_mgr = QualificationManager(self.db_path)
        res_mgr = ReservationManager(self.db_path)
        bill_mgr = BillingReconciliationManager(self.db_path)

        try:
            if path == "/api/stats":
                conn = get_db_connection(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM companies")
                total_companies = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM members WHERE status = 'Active'")
                total_members = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM instruments")
                total_instruments = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM qualifications")
                total_quals = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*), COALESCE(SUM(duration_hours), 0), COALESCE(SUM(total_cost), 0) FROM reservations WHERE status = 'Completed' AND billed = 0")
                unbilled_row = cur.fetchone()
                cur.execute("SELECT COUNT(*) FROM reservations WHERE status = 'Active'")
                active_reservations = cur.fetchone()[0]
                conn.close()

                return self._send_json({
                    "total_companies": total_companies,
                    "total_active_members": total_members,
                    "total_instruments": total_instruments,
                    "total_qualifications": total_quals,
                    "active_reservations": active_reservations,
                    "unbilled_bookings": unbilled_row[0],
                    "unbilled_hours": round(unbilled_row[1], 2),
                    "unbilled_revenue": round(unbilled_row[2], 2)
                })

            elif path == "/api/companies":
                conn = get_db_connection(self.db_path)
                cur = conn.cursor()
                cur.execute("""
                    SELECT c.*, COUNT(m.id) as member_count
                    FROM companies c
                    LEFT JOIN members m ON c.id = m.company_id
                    GROUP BY c.id
                    ORDER BY c.name ASC
                """)
                companies = [dict(r) for r in cur.fetchall()]
                conn.close()
                return self._send_json(companies)

            elif path == "/api/members":
                conn = get_db_connection(self.db_path)
                cur = conn.cursor()
                cur.execute("""
                    SELECT m.*, c.name as company_name, c.plan_tier as company_plan
                    FROM members m
                    LEFT JOIN companies c ON m.company_id = c.id
                    ORDER BY m.full_name ASC
                """)
                members = [dict(r) for r in cur.fetchall()]
                conn.close()
                return self._send_json(members)

            elif path == "/api/instruments":
                category = params.get("category", [None])[0]
                status = params.get("status", [None])[0]
                instruments = inst_mgr.list_instruments(category, status)
                return self._send_json(instruments)

            elif path == "/api/qualifications":
                inst_id = params.get("instrument_id", [None])[0]
                mem_id = params.get("member_id", [None])[0]
                quals = qual_mgr.list_qualifications(inst_id, mem_id)
                return self._send_json(quals)

            elif path == "/api/reservations":
                inst_id = params.get("instrument_id", [None])[0]
                comp_id = params.get("company_id", [None])[0]
                mem_id = params.get("member_id", [None])[0]
                status = params.get("status", [None])[0]
                reservations = res_mgr.list_reservations(inst_id, comp_id, mem_id, status)
                return self._send_json(reservations)

            elif path == "/api/billing/summary":
                summary = bill_mgr.get_unbilled_summary_by_company()
                return self._send_json(summary)

            elif path.startswith("/api/billing/ledger/"):
                comp_id = path.replace("/api/billing/ledger/", "")
                ledger = bill_mgr.get_company_itemized_ledger(comp_id)
                return self._send_json(ledger)

            elif path == "/api/billing/export-csv":
                comp_id = params.get("company_id", [None])[0]
                csv_data = bill_mgr.export_spacebring_invoice_csv(comp_id)
                filename = f"spacebring_lab_invoice_{comp_id or 'all'}.csv"
                return self._send_text(csv_data, content_type="text/csv", filename=filename)

            else:
                return self._send_json({"error": "Endpoint not found"}, status=404)

        except Exception as e:
            return self._send_json({"error": str(e)}, status=500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        inst_mgr = InstrumentManager(self.db_path)
        qual_mgr = QualificationManager(self.db_path)
        res_mgr = ReservationManager(self.db_path)
        bill_mgr = BillingReconciliationManager(self.db_path)
        importer = SpacebringImporter(self.db_path)

        try:
            if path == "/api/instruments":
                item = inst_mgr.create_instrument(
                    name=payload["name"],
                    category=payload.get("category", "General"),
                    location=payload.get("location", ""),
                    hourly_rate=float(payload.get("hourly_rate", 0.0)),
                    min_booking_minutes=int(payload.get("min_booking_minutes", 30)),
                    requires_training=bool(payload.get("requires_training", True)),
                    min_training_level=payload.get("min_training_level", "Basic"),
                    status=payload.get("status", "Available"),
                    model=payload.get("model", ""),
                    serial_number=payload.get("serial_number", ""),
                    custom_id=payload.get("custom_id", "")
                )
                return self._send_json(item, status=201)

            elif path == "/api/qualifications":
                item = qual_mgr.assign_certification(
                    member_id=payload["member_id"],
                    instrument_id=payload["instrument_id"],
                    training_level=payload.get("training_level", "Basic"),
                    certified_date=payload.get("certified_date"),
                    expires_date=payload.get("expires_date"),
                    certified_by=payload.get("certified_by", "Lab Admin"),
                    notes=payload.get("notes", "")
                )
                return self._send_json(item, status=201)

            elif path == "/api/qualifications/verify":
                eligible, reason = qual_mgr.verify_operator_eligibility(
                    member_id=payload["member_id"],
                    instrument_id=payload["instrument_id"]
                )
                return self._send_json({"eligible": eligible, "reason": reason})

            elif path == "/api/reservations":
                res = res_mgr.create_reservation(
                    instrument_id=payload["instrument_id"],
                    member_id=payload["member_id"],
                    start_time=payload["start_time"],
                    end_time=payload["end_time"],
                    notes=payload.get("notes", ""),
                    bypass_training_check=payload.get("bypass_training_check", False)
                )
                return self._send_json(res, status=201)

            elif path.endswith("/checkin") and "/api/reservations/" in path:
                res_id = path.split("/")[3]
                res = res_mgr.check_in(res_id)
                return self._send_json(res)

            elif path.endswith("/checkout") and "/api/reservations/" in path:
                res_id = path.split("/")[3]
                res = res_mgr.check_out(res_id)
                return self._send_json(res)

            elif path.endswith("/cancel") and "/api/reservations/" in path:
                res_id = path.split("/")[3]
                reason = payload.get("reason", "")
                res = res_mgr.cancel_reservation(res_id, reason)
                return self._send_json(res)

            elif path == "/api/billing/mark-billed":
                ids = payload.get("reservation_ids", [])
                updated = bill_mgr.mark_batch_billed(ids)
                return self._send_json({"updated_count": updated})

            elif path == "/api/import/file":
                file_path = payload.get("file_path")
                if not file_path:
                    return self._send_json({"error": "Missing 'file_path'"}, status=400)
                res = importer.import_file(file_path)
                return self._send_json(res)

            elif path == "/api/import/folder":
                folder_path = payload.get("folder_path")
                if not folder_path:
                    return self._send_json({"error": "Missing 'folder_path'"}, status=400)
                res = importer.import_folder(folder_path)
                return self._send_json(res)

            elif path == "/api/seed-samples":
                from .sample_loader import load_all_sample_data
                res = load_all_sample_data(self.db_path)
                return self._send_json(res)

            else:
                return self._send_json({"error": "Endpoint not found"}, status=404)

        except PermissionError as pe:
            return self._send_json({"error": str(pe), "code": "TRAINING_REQUIRED"}, status=403)
        except Exception as e:
            return self._send_json({"error": str(e)}, status=500)

def run_server(host: str = "127.0.0.1", port: int = 8080, db_path: Path = None):
    init_db(db_path)
    seed_default_instruments(db_path)

    BridgeAPIHandler.db_path = db_path
    server_address = (host, port)
    httpd = http.server.HTTPServer(server_address, BridgeAPIHandler)
    print(f"Spacebring Lab Instrument Bridge started at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down bridge server.")
        httpd.server_close()
