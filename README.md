# Spacebring Lab Instrument Bridge

> **Local-first laboratory operating & instrument management utility marrying Spacebring coworking CRM data with scientific equipment scheduling, operator training enforcement, and billing reconciliation.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Zero-Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(Standard%20Library)-success)](requirements.txt)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local--First-brightgreen)](#local-first-guarantees)

---

## The Problem It Solves

Coworking and incubator management systems like **Spacebring** provide member rosters, desk/suite leases, and basic meeting room reservations. However, wet-lab and bioscience incubators operate shared scientific infrastructure (flow cytometers, HPLC systems, centrifuges, confocal microscopes) that require:

1. **Equipment Scheduling & Collision Prevention**: Real-time instrument availability, time buffers, and conflict detection.
2. **Operator Certification Verification**: Enforcing that only trained, certified personnel can book or operate sensitive instrumentation.
3. **Usage-Based Cost Accounting**: Tracking machine hours and calculating billable amounts based on instrument rate cards.
4. **Spacebring Billing Synchronization**: Mapping instrument charges back to tenant company accounts and generating invoice-ready addendums.

**Spacebring Lab Instrument Bridge** provides this missing bridge locally on your machine—no vendor lock-in, no cloud subscriptions, and zero external telemetry.

---

## Key Features

- **📂 Local Folder & File Ingestion**: Drag & drop or specify local directories containing Spacebring customer export files (`.csv`, `.tsv`, `.json`). The smart parser automatically reconciles companies, members, and membership tiers.
- **🔬 Core-Facility Instrument Registry**: Manage equipment categories, locations, calibration details, hourly rates, and required training certification ranks.
- **🛡️ Strict Training Matrix Enforcement**: Blocks unauthorized or uncertified users from scheduling instruments. Supports hierarchical clearance ranks (`None < Basic < Advanced < Certified Operator`) and expiration dates.
- **⏱️ Live Session Check-In & Check-Out**: Real-time tracking of actual machine time versus scheduled time.
- **💰 Spacebring Invoice Reconciliation**: Generates itemized billing summaries grouped by tenant company and exports one-click Spacebring-formatted invoice CSVs.
- **🌐 Zero-Dependency Web UI**: Includes a modern, responsive local web dashboard that runs entirely offline with Python's standard library.
- **💻 Full Command-Line Interface (CLI)**: Automate imports, status checks, and report generation headlessly.

---

## Quick Start

### 1. Clone & Navigate
```bash
git clone https://github.com/marez8505/spacebring-instrument-bridge.git
cd spacebring-instrument-bridge
```

### 2. Launch Local Web Dashboard
```bash
python app.py serve
```
Open your browser to:
👉 **[http://127.0.0.1:8080](http://127.0.0.1:8080)**

### 3. Load Sample Demo Data (Optional)
To test the full workflow with pre-configured biotech tenants, scientific instruments, and billing sessions:
- Click **"🧪 Load Demo Data"** in the top navigation bar of the web UI, OR run:
```bash
python app.py seed-demo
```

---

## Web Dashboard Overview

The web dashboard is organized into focused operational tabs:

| Tab | Purpose |
| :--- | :--- |
| **Overview** | Key performance indicators (active instruments, tenant companies, certified operators, unbilled lab revenue, and active sessions). |
| **Spacebring Roster** | View all synced tenant companies, membership plans, and laboratory operators. |
| **Lab Instruments** | Catalog of instruments, hourly rates, room locations, and minimum training levels. |
| **Training Matrix** | Operator certifications, expiration dates, and an instant **Eligibility Verifier**. |
| **Bookings & Usage** | Reservation calendar with live **Check In** and **Check Out** tracking. |
| **Billing Reconciliation**| Aggregate unbilled charges by Spacebring tenant and download invoice-ready CSV files. |
| **Data Ingestion** | Ingest local files or scan directories of customer data on demand. |

---

## Command-Line Usage

The utility provides commands for batch automation and headless environments:

```bash
# Ingest all Spacebring customer data files in a directory
python app.py import-folder "C:\Users\marez\Downloads\spacebring_exports"

# Ingest an individual customer export file
python app.py import-file "./samples/spacebring_tenants.csv"

# View all registered instruments and hourly rates
python app.py list-instruments

# View all synchronized Spacebring tenant companies
python app.py list-companies

# Export unbilled usage directly to a CSV file for Spacebring invoicing
python app.py export-billing --output monthly_lab_invoice.csv
```

For complete command options, see [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

---

## Sample Data Included

The repository includes ready-to-test sample data in the `samples/` directory:
- `samples/spacebring_tenants.csv`: Sample incubator tenant companies with tier levels.
- `samples/spacebring_members.json`: Sample scientists, research associates, and lab managers.

Ingest them with:
```bash
python app.py import-folder ./samples
```

---

## Documentation

- [System Architecture & Design](docs/ARCHITECTURE.md)
- [Spacebring Integration & Workflow Guide](docs/SPACEBRING_INTEGRATION_GUIDE.md)
- [CLI Reference Guide](docs/CLI_REFERENCE.md)

---

## Local-First Guarantees

- **100% Offline Capable**: Zero CDN dependencies or external script tags in the UI.
- **Private Data Storage**: Data is kept in a local SQLite file (`~/.lab_bridge/lab_bridge.db`), completely shielded from third-party cloud services.
- **Portability**: Single-directory design makes backups and air-gapped deployments trivial.

---

## License

MIT License. Designed for bioscience incubators, academic core facilities, and shared laboratory spaces.
