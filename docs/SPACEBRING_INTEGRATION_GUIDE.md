# Spacebring Integration Guide

This guide describes how to bridge Spacebring tenant management with wet-lab instrument scheduling and usage billing.

---

## 1. The Challenge
Spacebring excels at coworking and incubator administration:
- Tenant company profiles and membership plans
- Conference room bookings and shared desk assignments
- Monthly subscription invoicing

However, wet-lab incubators (such as university or regional biotech incubators) have specialized requirements:
- Complex scientific instruments (Cytometers, HPLC, Centrifuges, Confocal Microscopes)
- Safety and operational training certifications
- Hourly machine usage tracking
- Billing instrument charges back to the tenant's primary Spacebring account

The **Spacebring Lab Instrument Bridge** connects both worlds without requiring custom enterprise cloud integrations or subscription fees.

---

## 2. Ingesting Data from Spacebring

### Step 1: Export Data from Spacebring
1. In your Spacebring Administrator dashboard, navigate to **Members & Companies**.
2. Select **Export** to download your current customer roster as CSV or JSON.
3. Save the exported files to a designated folder on your machine (e.g., `C:\Spacebring_Exports\`).

### Step 2: Sync with the Bridge
You can sync using the Web UI or the CLI:

#### Via Web Dashboard:
1. Navigate to the **Data Ingestion** tab.
2. In **Option 1 (Ingest Local Folder)**, enter your export directory path (e.g. `C:\Spacebring_Exports`).
3. Click **Scan & Sync Folder**.
4. The tool automatically maps columns (`company_name`, `email`, `role`, `plan`) into your local database.

#### Via Command Line:
```bash
python app.py import-folder "C:\Spacebring_Exports"
```
Or for a single file:
```bash
python app.py import-file "C:\Spacebring_Exports\members_2026.csv"
```

---

## 3. Managing Lab Operations

1. **Register Instruments**:
   - Go to **Lab Instruments** -> **+ Add Instrument**.
   - Set the hourly rate and required training certification level (e.g. "Certified Operator").

2. **Grant Operator Certifications**:
   - Go to **Training Matrix** -> **+ Grant Certification**.
   - Select a Spacebring member, choose the instrument, set their clearance level, and specify an expiration date.

3. **Booking & Enforcement**:
   - Members or lab admins create bookings.
   - If a member lacks the required certification or their company is past due, the system blocks the booking and explains why.
   - During operation, click **Check In** when starting a run and **Check Out** when finished. The system computes exact duration and billable cost.

---

## 4. Reconciling with Spacebring Invoicing

At the end of your billing cycle:
1. Navigate to the **Billing Reconciliation** tab.
2. Review the unbilled summary table grouped by Spacebring tenant.
3. Click **Export Spacebring CSV** to generate a pre-formatted CSV file containing:
   - Tenant / Company Name
   - Operator Name
   - Instrument Description
   - Session Date
   - Billable Duration (Hours)
   - Hourly Rate
   - Total Amount Due
   - Reference Booking ID
4. Import this CSV into Spacebring as invoice line items or attach it to the tenant's monthly subscription invoice.
