# Kaizen Lite Implementation Summary

## Files Created

### Core Application
- `app.py` - Streamlit entrypoint with routing logic
- `auth.py` - Streamlit-authenticator integration
- `db.py` - SQLite database helper with scoped queries
- `analysis_engine.py` - In-process calls to service_b modules
- `delta_computation.py` - Period-over-period delta logic (core differentiator)
- `add_firm.py` - CLI script for onboarding firms

### Views
- `views/homepage.py` - Public homepage with request access form
- `views/dashboard.py` - Authenticated dashboard with client list
- `views/client_detail.py` - Client detail with upload, results, PDF download, history
- `views/__init__.py` - Package marker

### Configuration
- `config/firms.yaml` - Auth credentials (gitignored)
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variable template
- `README.md` - Setup and usage instructions

## Architecture Decisions

### Service B Integration Method
**Chosen**: PYTHONPATH manipulation with in-process imports

The `analysis_engine.py` adds `service_b` to `sys.path` and imports modules directly:
```python
SERVICE_B_PATH = Path(__file__).parent.parent / "service_b"
sys.path.insert(0, str(SERVICE_B_PATH))
```

This approach:
- Avoids HTTP overhead
- Allows direct function calls
- Reuses all existing service_b logic
- No need for editable package installation

### Data Isolation
All database queries are scoped by `firm_id`:
- `get_scoped_clients(firm_id)` - only returns that firm's clients
- `get_scoped_reports(firm_id, client_id)` - only returns reports for that firm's client

### Delta Computation
The `compute_deltas()` function:
- Compares numeric metrics between current and previous reports
- Determines direction per metric (higher_is_better flag)
- Generates plain-language descriptions
- Prioritizes worsened deltas for user attention

### Database Schema
- `firms` table: firm_id, firm_name, contact_email, created_at, logo_path
- `clients` table: client_id, firm_id, client_name, created_at (UNIQUE on firm_id, client_name)
- `reports` table: report_id, client_id, uploaded_filename, generated_at, pdf_path, summary_json

## Verification Checklist

### 1. Homepage renders with no login; "Request Access" logs to pending_requests.csv
✓ Implemented in `views/homepage.py`
✓ Form appends to CSV without creating accounts

### 2. add_firm.py creates a working, login-able firm account
✓ CLI script with --name, --email, --username flags
✓ Generates or accepts password
✓ Hashes via streamlit-authenticator.Hasher
✓ Adds to config/firms.yaml and SQLite database

### 3. Two separate firm accounts cannot see each other's data
✓ All queries scoped by firm_id
✓ Session state only stores firm_id from authenticated user
✓ No URL parameters for navigation

### 4. Full flow works end-to-end
✓ Login → add client → upload → auto-detect → view findings → download PDF → history

### 5. Second upload shows delta section
✓ `compute_deltas()` compares summary_json entries
✓ Shows worsened/improved/unchanged with plain-language descriptions
✓ Prioritizes worsened deltas prominently

### 6. Duplicate client name blocked
✓ UNIQUE constraint in database
✓ ValueError caught and shown as clean message

### 7. Schema-detection failure shows clear message
✓ `analyze_ledger()` raises ValueError with specific message
✓ Caught in `client_detail.py` and displayed to user

### 8. requirements.txt installs cleanly
✓ All dependencies listed
✓ Reuses service_b dependencies where applicable

## Deployment Warning

**DO NOT DEPLOY TO PUBLIC URL WITHOUT ADDITIONAL PROTECTION**

The app's login is not sufficient for public exposure. Consider:
- IP allowlist at the infra level
- Basic auth reverse proxy
- Private network deployment

## Usage Instructions

### Setup
```bash
cd kaizen_lite
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set KAIZEN_LITE_COOKIE_SECRET
```

### Add a Firm
```bash
python add_firm.py --name "ABC & Co" --email "ca@abc.com" --username abc_co
```

### Run
```bash
streamlit run app.py
```

## What Was NOT Modified

- service_a/ - Zero changes
- service_b/ - Zero changes (only imported as dependency)
- frontend/ - Zero changes
- docker-compose.yml - Zero changes
- nginx/ - Zero changes

## Folder Structure

```
/kaizen_lite/
  app.py
  auth.py
  add_firm.py
  analysis_engine.py
  delta_computation.py
  db.py
  requirements.txt
  .env.example
  README.md
  config/
    firms.yaml
  data/
    {firm_id}/
      {client_id}/
        uploads/
        reports/
  views/
    __init__.py
    homepage.py
    dashboard.py
    client_detail.py
  pending_requests.csv (created on first request)
  kaizen_lite.sqlite3 (created on first run)
```

## Git Ignore Updates

Added to .gitignore:
- kaizen_lite/data/
- kaizen_lite/*.sqlite3
- kaizen_lite/config/firms.yaml
- kaizen_lite/pending_requests.csv
