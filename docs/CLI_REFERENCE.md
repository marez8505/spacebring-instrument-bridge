# Command-Line Interface (CLI) Reference

The utility can be operated entirely via the command-line interface for scripting, headless server environments, or automated batch processing.

---

## Global Options

```bash
python app.py [--db PATH] <command> [options]
```

- `--db PATH`: Specify a custom path for the SQLite database. If omitted, defaults to `~/.lab_bridge/lab_bridge.db`.

---

## Commands

### 1. `serve`
Start the local HTTP web server and embedded REST API.

```bash
python app.py serve [--host 127.0.0.1] [--port 8080]
```
- `--host`: Network interface to bind (default: `127.0.0.1` for local-only privacy).
- `--port`: Port number to listen on (default: `8080`).

---

### 2. `import-file`
Ingest a single CSV, TSV, or JSON export file from Spacebring.

```bash
python app.py import-file <file_path>
```
*Example:*
```bash
python app.py import-file ./samples/spacebring_tenants.csv
```

---

### 3. `import-folder`
Recursively scan a local directory for all `.csv`, `.tsv`, and `.json` files, merging all discovered companies and members.

```bash
python app.py import-folder <folder_path>
```
*Example:*
```bash
python app.py import-folder ./samples
```

---

### 4. `list-instruments`
Print a formatted console table of all registered laboratory instruments, rates, and training prerequisites.

```bash
python app.py list-instruments
```

---

### 5. `list-companies`
Print a list of all synced Spacebring tenant companies and their membership tiers.

```bash
python app.py list-companies
```

---

### 6. `export-billing`
Generate a Spacebring invoice reconciliation CSV.

```bash
python app.py export-billing [--output filename.csv] [--company company_id]
```
- `--output`, `-o`: File path to write the output. If omitted, outputs directly to stdout.
- `--company`, `-c`: Optional company ID filter.

*Example:*
```bash
python app.py export-billing -o november_lab_usage.csv
```

---

### 7. `seed-demo`
Populate the database with realistic demonstration data (sample Spacebring companies, researchers, scientific instruments, training certifications, and completed usage sessions).

```bash
python app.py seed-demo
```
