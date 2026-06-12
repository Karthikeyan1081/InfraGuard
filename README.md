# InfraGuard - Infrastructure Inventory Reconciliation System

InfraGuard is a full-stack, enterprise-grade Infrastructure Inventory Reconciliation System. It aligns expected physical/virtual machine inventories (originating from CMDB databases) against actual infrastructure scans. 

The core reconciliation engine relies on a deterministic business rules engine. However, the application also includes an **Agentic AI layer** leveraging OpenAI, Google Gemini, and MongoDB Atlas Vector Search (or ChromaDB) to provide intelligent discrepancy summarizations and an interactive chatbot experience.

---

## Technical Stack
- **Backend Framework:** FastAPI (Async/Await architecture)
- **Database Engine:** SQLite + `aiosqlite` (Async Database interface)
- **Validation layer:** Pydantic (Type and field boundary validation)
- **Reporting Engine:** ReportLab (Document templates, dynamic layout flows, page number tracking canvas)
- **Frontend Dashboard:** Vanilla HTML5, CSS Grid/Flexbox styling (dark slate theme), and Vanilla JavaScript (AJAX requests and direct 2D Canvas chart graphics).

---

## File Architecture
```
InfraGuard/
├── api/
│   ├── upload.py           # File upload handling (POST /api/upload)
│   ├── analyze.py          # Reconciliation & statistics (POST /api/analyze, GET /api/analyses)
│   └── report.py           # Report compiles (GET /api/reports/{id})
├── database/
│   └── db.py               # SQLite tables initialization & async connection dependency
├── services/
│   ├── ingestion_service.py      # Parses CSV & JSON configurations (Pydantic validation)
│   ├── normalization_service.py  # Standardizes hostnames, IPs, RAM (MB to GB), OS versions, and statuses
│   ├── reconciliation_service.py # Core stages comparing assets (ID -> IP -> Hostname match cascade)
│   ├── investigation_service.py  # Systematic pattern detectors (untracked subnets, systematic OS upgrades)
│   ├── risk_service.py           # Evaluation of severity levels (High, Medium, Low)
│   ├── recommendation_service.py # Generates action guidelines for technical teams
│   └── report_service.py         # Generates PDF documents using ReportLab
├── static/
│   ├── index.html          # Enterprise dashboard structure
│   ├── styles.css          # Theme styles, cards, tables, and badge layouts
│   └── app.js              # Ingestion submit queues, selectors filtering, and canvas drawing
├── uploads/                # Temporary directory for uploaded CSV/JSON datasets (created automatically)
├── reports/                # Output path storing generated PDF reports (created automatically)
├── data_samples/           # Folder for demo CSV and JSON (created by utility script)
├── main.py                 # Core app bootstrap, startup event, and routes assembly
├── requirements.txt        # Python package dependencies
└── generate_sample_data.py # Demo data generator
```

---

## Reconciliation Analysis Logic

The reconciliation engine employs standard business rules:
1. **Normalization:** Prior to comparison, IP addresses are trimmed, hostnames are lowercased, RAM numbers over 256 are divided by 1024 (e.g. 16384 MB becomes 16 GB), and OS names are resolved to standard naming patterns (e.g. `Ubuntu 22.04.2 LTS` becomes `Ubuntu 22.04`).
2. **Cascaded Matching:** Assets are mapped across inventories starting with `external_id`. If not matching, they fallback to `ip_address` alignment, and finally to `hostname` matching.
3. **Discrepancy Identification:**
   - **Missing Asset:** Present in CMDB but absent from the live scan.
   - **Untracked Asset:** Discovered on live infrastructure but missing from CMDB registries.
   - **Naming Mismatch:** Matched by ID or IP, but system names differ.
   - **Attribute Mismatch:** Matched by ID/IP, but RAM, CPU cores, OS distribution, or status attributes differ.
   - **Duplicate Asset:** Repeating critical attributes (ID/IP/Hostname) inside a single inventory list.
4. **Severity Evaluation:**
   - **High Risk:** Missing production machines (active, resource-intensive, or containing "prod", "db", "mail", "sql" in hostname), or live production nodes marked "Inactive" in CMDB.
   - **Medium Risk:** Attribute resource drift or naming mismatches on production systems, or missing active dev/test servers.
   - **Low Risk:** Discrepancies on test environments, duplicates, or missing inactive CMDB entries.

---

## Installation & Setup Instructions

### Prerequisites
- Python 3.9 or higher

### 1. Clone or Copy the Workspace
Ensure you are in the project root directory containing `requirements.txt` and `main.py`.

### 2. Create and Activate a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Package Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Ensure that you have a `.env` file in the root directory containing your API keys and connection strings (e.g. `OPENAI_API_KEY`, `GEMINI_API_KEY`, `MONGODB_ATLAS_URI`).

### 5. Create Sample Auditing Feeds
Run the generation script to output testing files in `data_samples/`:
```bash
python generate_sample_data.py
```
This generates:
- `data_samples/cmdb_inventory.csv` (CMDB data)
- `data_samples/actual_infrastructure.json` (Live discovery scan)

### 5. Start the Application Server
Run the FastAPI application via Uvicorn:
```bash
python main.py
```
*Alternatively, run: `uvicorn main:app --host 127.0.0.1 --port 8000 --reload`*

### 6. Access the Dashboard
Open your web browser and navigate to:
[Visit_Here](https://huggingface.co/spaces/luci-07/InfraGuard)

---

## Verifying Features In Browser
1. In the **Execute New Audit** card:
   - Enter a run name (e.g., `Corporate Audit June 2026`).
   - Select `data_samples/cmdb_inventory.csv` in the CMDB input box.
   - Select `data_samples/actual_infrastructure.json` in the Actual input box.
   - Click **Reconcile Datasets**.
2. Once complete, the sidebar history list updates and auto-focuses on the new run details.
3. The dashboard displays:
   - Counts cards for discrepancies.
   - Canvas-rendered doughnut charts.
   - Systematic warning alerts (e.g., un-inventoried subnet warnings on `10.0.3.x`).
   - Interactive severity/type filters above the table.
   - Action recommendations in the rightmost column of the log table.
4. Click **Download PDF Report** to download the ReportLab PDF document.
