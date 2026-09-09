# Streamlit Cloud Refactoring Summary

## Changes Made

### 1. Database: SQLite → PostgreSQL
- **File**: `db.py`
- **Changes**:
  - Replaced `sqlite3` with `sqlalchemy` + `psycopg2-binary`
  - Connection string from `st.secrets.get("database_url")`
  - All queries now use SQLAlchemy with parameterized queries
  - `SERIAL` instead of `AUTOINCREMENT` for primary keys
  - `TIMESTAMP` instead of `TEXT` for datetime fields

### 2. File Storage: Local → AWS S3
- **New File**: `storage.py`
- **Changes**:
  - Created S3 helper functions (upload, download, exists, delete)
  - S3 credentials from Streamlit secrets
  - PDF generation now returns bytes instead of writing to disk
  - Database stores S3 keys instead of local paths
- **Modified Files**:
  - `analysis_engine.py`: `generate_pdf()` now returns bytes
  - `client_detail.py`: Uses S3 for PDF upload/download

### 3. Authentication: YAML → Streamlit Secrets
- **File**: `auth.py`
- **Changes**:
  - Removed `yaml` dependency
  - Credentials loaded from `st.secrets.get("credentials")`
  - Cookie secret from `st.secrets.get("cookie_secret")`
  - No more `config/firms.yaml` file

### 4. Admin: CLI → Web UI
- **Removed**: `add_firm.py` (CLI script)
- **New File**: `views/admin.py`
- **Changes**:
  - Admin view accessible via `?view=admin` query param
  - Protected by `admin_secret` from Streamlit secrets
  - Web form to add firms
  - Password generation/hashing in-browser
  - Shows existing firms

### 5. Homepage: CSV → Contact Info
- **File**: `views/homepage.py`
- **Changes**:
  - Removed `pending_requests.csv` functionality
  - Changed request access to contact info message
  - Streamlined for cloud deployment

### 6. Dependencies
- **File**: `requirements.txt`
- **Changes**:
  - Added `psycopg2-binary>=2.9.9` (PostgreSQL)
  - Added `boto3>=1.34.0` (AWS S3)
  - Removed `python-dotenv` (no longer needed)

### 7. Configuration
- **New File**: `.streamlit/secrets.toml.example`
- **Removed**: `config/firms.yaml`, `.env.example`
- **Changes**:
  - All configuration now via Streamlit secrets
  - Template provided for local development

### 8. Routing
- **File**: `app.py`
- **Changes**:
  - Added admin view routing via query params
  - Imported `views/admin`

### 9. Git Ignore
- **File**: `.gitignore`
- **Changes**:
  - Updated Kaizen Lite ignores for cloud deployment
  - Added `.streamlit/secrets.toml` (local only)

## Deployment Prerequisites

### Required Cloud Services
1. **PostgreSQL Database** (ElephantSQL, Neon, or similar)
2. **AWS S3 Bucket** with IAM user credentials
3. **Streamlit Cloud Account**

### Required Streamlit Secrets
```toml
database_url = "postgresql://user:password@host:port/database"
aws_access_key_id = "your-aws-access-key-id"
aws_secret_access_key = "your-aws-secret-access-key"
aws_region = "us-east-1"
s3_bucket_name = "your-bucket-name"
cookie_secret = "random-secret-key-for-cookies"
admin_secret = "random-secret-key-for-admin-access"

[credentials.usernames.firm_username]
email = "firm@example.com"
name = "Firm Name"
password = "hashed_password_here"
```

## Deployment Steps

1. Push code to GitHub
2. Create Streamlit Cloud app pointing to `kaizen_lite/app.py`
3. Configure secrets in Streamlit Cloud
4. Access admin view at `?view=admin` to add first firm
5. Copy credentials to secrets
6. Share login with firm

## What Was NOT Changed

- **service_b/** - Still imported via sys.path (works on Streamlit Cloud)
- **Core analysis logic** - unchanged
- **Delta computation** - unchanged
- **Data isolation** - still scoped by firm_id
- **Frontend** - unchanged

## Files Removed

- `add_firm.py` (replaced by admin view)
- `config/firms.yaml` (replaced by secrets)
- `.env.example` (replaced by secrets)
- `pending_requests.csv` functionality (removed)

## Files Added

- `storage.py` (S3 helper)
- `views/admin.py` (admin web UI)
- `.streamlit/secrets.toml.example` (secrets template)

## Files Modified

- `db.py` (PostgreSQL)
- `auth.py` (Streamlit secrets)
- `analysis_engine.py` (PDF returns bytes)
- `client_detail.py` (S3 integration)
- `homepage.py` (removed CSV)
- `app.py` (admin routing)
- `requirements.txt` (cloud deps)
- `README.md` (cloud deployment guide)
- `.gitignore` (cloud ignores)
