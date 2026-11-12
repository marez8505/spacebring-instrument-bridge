# System Architecture & Technical Design

The **Spacebring Lab Instrument Bridge** solves the structural gap between coworking/incubator tenant management software (like Spacebring) and academic/incubator core laboratory operations (like Agilent iLab or Stratocore PPMS).

```
 +---------------------------------------------------------------+
 |                       Spacebring CRM                          |
 |  (Tenants, Members, Plans, Room Bookings, Invoicing & Billing)|
 +-------------------------------+-------------------------------+
                                 |  Export (CSV / JSON)
                                 v
 +---------------------------------------------------------------+
 |              Spacebring Lab Instrument Bridge                 |
 |                     (Local-First Engine)                      |
 |                                                               |
 |   [ Folder & File Ingester ] <---> [ SQLite Store: .db ]     |
 |                                                               |
 |   [ Lab Instrument Registry ]     [ Training Certification ]  |
 |   - Rates ($/hr)                  - Matrix & Rank Hierarchy   |
 |   - Status & Maintenance          - Expiration & Audit Trail  |
 |                                                               |
 |   [ Booking & Conflict Engine ]   [ Billing Reconciliation ]  |
 |   - Training Enforcer             - Spacebring Invoice CSV    |
 |   - Live Session Check-in/out     - Tenant Itemized Ledgers   |
 +-------------------------------+-------------------------------+
                                 |
           +---------------------+---------------------+
           |                                           |
           v                                           v
 [ Modern Local Web UI ]                     [ Python Script CLI ]
 (Zero-dependency, offline)                  (Batch automation)
```

## 1. Local-First Design & Privacy Guarantees
- **No Cloud Telemetry**: Binds to `127.0.0.1` by default.
- **Embedded Database**: Uses SQLite with WAL (write-ahead log) mode support. No database servers or third-party cloud services are required.
- **Zero Third-Party API Leakage**: Tenant details, member emails, and confidential instrument usage records remain strictly local to your workstation.

## 2. Core Subsystems

### A. Spacebring Data Ingester (`bridge/importer.py`)
- Normalizes diverse CSV, TSV, and JSON formats exported from Spacebring or custom CRM databases.
- Intelligently extracts Company, Plan Tier, Status, Billing Contact, and Member records.
- Supports both single-file uploads and whole-folder recursive batch scanning.

### B. Instrument Catalog (`bridge/instruments.py`)
- Maintains asset identifiers, model, serial numbers, facility locations, and hourly rates.
- Defines minimum operator training requirements (None, Basic, Advanced, Certified Operator).

### C. Training & Certification Enforcer (`bridge/qualifications.py`)
- Enforces an operator hierarchy:
  `None (0) < Basic (1) < Advanced (2) < Certified Operator (3)`
- Checks certification validity and expiration dates before permitting any instrument reservation.
- Verifies that the tenant company account is in good standing before allowing bookings.

### D. Reservation & Live Session Tracker (`bridge/reservations.py`)
- Detects and prevents time slot collisions on the same physical instrument.
- Supports scheduled reservations as well as real-time Check-in and Check-out timestamps.
- Automatically calculates actual billable hours and usage charges based on instrument rate cards.

### E. Billing & Reconciliation Ledger (`bridge/billing.py`)
- Groups completed, unbilled instrument hours by Spacebring company account.
- Generates Spacebring-compatible invoice CSV line items ready to attach or import into tenant monthly bills.
- Marks batches as billed upon reconciliation.
