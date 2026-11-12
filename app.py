#!/usr/bin/env python3
"""
Spacebring Lab Instrument Bridge (CLI & Server Entrypoint)
"""

import sys
import argparse
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from bridge.db import init_db, seed_default_instruments, DEFAULT_DB_PATH
from bridge.importer import SpacebringImporter
from bridge.instruments import InstrumentManager
from bridge.billing import BillingReconciliationManager
from bridge.sample_loader import load_all_sample_data
from bridge.server import run_server

def main():
    parser = argparse.ArgumentParser(
        description="Spacebring Lab Instrument Bridge — Local-First Laboratory Operating & Instrument Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py serve                      # Launch local interactive web dashboard
  python app.py import-file export.csv     # Ingest a single Spacebring export file
  python app.py import-folder ./tenant_data# Scan & sync a folder of customer files
  python app.py seed-demo                  # Seed demo tenant & instrument bookings
  python app.py export-billing             # Export invoice reconciliation CSV
        """
    )
    parser.add_argument("--db", default=None, help="Custom SQLite database file path (default: ~/.lab_bridge/lab_bridge.db)")

    subparsers = parser.add_subparsers(dest="command")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Start the local web UI dashboard and REST API")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")

    # Command: import-file
    file_parser = subparsers.add_parser("import-file", help="Ingest a Spacebring CSV, TSV, or JSON export file")
    file_parser.add_argument("path", help="Path to the file to import")

    # Command: import-folder
    folder_parser = subparsers.add_parser("import-folder", help="Scan and ingest a directory of customer/tenant files")
    folder_parser.add_argument("path", help="Path to the directory to scan")

    # Command: seed-demo
    subparsers.add_parser("seed-demo", help="Populate database with realistic demo Spacebring tenants and reservations")

    # Command: list-instruments
    subparsers.add_parser("list-instruments", help="Display all registered laboratory instruments")

    # Command: list-companies
    subparsers.add_parser("list-companies", help="Display all synced Spacebring tenant companies")

    # Command: export-billing
    bill_parser = subparsers.add_parser("export-billing", help="Export unbilled usage ledger formatted for Spacebring invoicing")
    bill_parser.add_argument("--output", "-o", default=None, help="Destination CSV file path (prints to stdout if omitted)")
    bill_parser.add_argument("--company", "-c", default=None, help="Filter export to a specific company ID")

    args = parser.parse_args()

    db_path = Path(args.db).resolve() if args.db else DEFAULT_DB_PATH
    init_db(db_path)
    seed_default_instruments(db_path)

    cmd = args.command or "serve"

    if cmd == "serve":
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8080)
        run_server(host=host, port=port, db_path=db_path)

    elif cmd == "import-file":
        importer = SpacebringImporter(db_path)
        print(f"[*] Ingesting file: {args.path}")
        res = importer.import_file(args.path)
        print(f"[+] Success: Synced {res['companies_synced']} companies and {res['members_synced']} members.")

    elif cmd == "import-folder":
        importer = SpacebringImporter(db_path)
        print(f"[*] Scanning folder: {args.path}")
        res = importer.import_folder(args.path)
        print(f"[+] Success: Scanned {res['files_scanned']} files. Synced {res['companies_synced']} companies and {res['members_synced']} members.")

    elif cmd == "seed-demo":
        res = load_all_sample_data(db_path)
        print(f"[+] {res['message']}")
        print(f"    - Companies seeded: {res['companies_seeded']}")
        print(f"    - Members seeded: {res['members_seeded']}")
        print(f"    - Certifications: {res['qualifications_seeded']}")
        print(f"    - Bookings & Logs: {res['reservations_seeded']}")

    elif cmd == "list-instruments":
        mgr = InstrumentManager(db_path)
        insts = mgr.list_instruments()
        print(f"\nRegistered Lab Instruments ({len(insts)}):")
        print("-" * 80)
        print(f"{'ID':<15} {'Name':<35} {'Rate ($/hr)':<12} {'Training Level':<15}")
        print("-" * 80)
        for i in insts:
            print(f"{i['id']:<15} {i['name'][:34]:<35} ${i['hourly_rate']:<11.2f} {i['min_training_level']:<15}")
        print("-" * 80)

    elif cmd == "list-companies":
        from bridge.db import get_db_connection
        conn = get_db_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, name, plan_tier, status, contact_email FROM companies ORDER BY name")
        rows = cur.fetchall()
        conn.close()
        print(f"\nSynced Spacebring Companies ({len(rows)}):")
        print("-" * 80)
        print(f"{'ID':<20} {'Company Name':<28} {'Plan Tier':<20} {'Status':<10}")
        print("-" * 80)
        for r in rows:
            print(f"{r['id']:<20} {r['name'][:27]:<28} {r['plan_tier'][:19]:<20} {r['status']:<10}")
        print("-" * 80)

    elif cmd == "export-billing":
        mgr = BillingReconciliationManager(db_path)
        csv_data = mgr.export_spacebring_invoice_csv(getattr(args, "company", None))
        if args.output:
            out_path = Path(args.output).resolve()
            out_path.write_text(csv_data, encoding="utf-8")
            print(f"[+] Spacebring invoice CSV written to: {out_path}")
        else:
            print(csv_data)

if __name__ == "__main__":
    main()
