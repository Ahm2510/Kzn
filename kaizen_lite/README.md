# Kaizen Lite

A Streamlit-based MVP for CA firms to analyze client financial health.

## Deployment Options

### Option 1: Streamlit Cloud (Recommended for Production)

Kaizen Lite is now configured for Streamlit Cloud deployment with:
- **PostgreSQL** database (via ElephantSQL, Neon, or similar)
- **AWS S3** for file storage (PDFs, uploads)
- **Streamlit Secrets** for configuration

#### Prerequisites

1. **PostgreSQL Database**
   - Get a free database from [ElephantSQL](https://www.elephantsql.com/) or [Neon](https://neon.tech/)
   - Note the connection string: `postgresql://user:password@host:port/database`

2. **File Storage (AWS S3 or Cloudflare R2)**
   
   **Option A: Cloudflare R2 (Free - Recommended)**
   - Create account at [Cloudflare R2](https://dash.cloudflare.com/)
   - Go to R2 → Create bucket
   - Get R2 API token from [Profile → API Tokens](https://dash.cloudflare.com/profile/api-tokens)
   - Note the account ID, access key ID, secret access key, and bucket name
   
   **Option B: AWS S3**
   - Create an S3 bucket in AWS
   - Create an IAM user with `s3:PutObject` and `s3:GetObject` permissions
   - Note the access key ID, secret access key, and bucket name

3. **Streamlit Cloud Account**
   - Sign up at [share.streamlit.io](https://share.streamlit.io)

#### Deployment Steps

1. **Push to GitHub**
   ```bash
   git add kaizen_lite/
   git commit -m "Add Kaizen Lite for Streamlit Cloud"
   git push
   ```

2. **Create Streamlit Cloud App**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your GitHub repository
   - Set main file path to `kaizen_lite/main.py`

3. **Configure Secrets**
   In Streamlit Cloud, go to your app's Settings → Secrets and add:

   ```toml
   # Database
   database_url = "postgresql://user:password@host:port/database"
   
   # File Storage (choose one)
   
   # Option A: Cloudflare R2 (Free)
   s3_endpoint_url = "https://<account-id>.r2.cloudflarestorage.com"
   r2_access_key_id = "your-r2-access-key-id"
   r2_secret_access_key = "your-r2-secret-access-key"
   s3_bucket_name = "your-r2-bucket-name"
   
   # Option B: AWS S3
   # aws_access_key_id = "your-aws-access-key-id"
   # aws_secret_access_key = "your-aws-secret-access-key"
   # aws_region = "us-east-1"
   # s3_bucket_name = "your-bucket-name"
   
   # Authentication
   cookie_secret = "random-secret-key-for-cookies"
   admin_secret = "random-secret-key-for-admin-access"
   
   # Firm credentials (add for each firm)
   [credentials.usernames.abc_co]
   email = "ca@abc.com"
   name = "ABC & Co"
   password = "hashed_password_here"
   ```

   To hash a password:
   ```bash
   python -c "import streamlit_authenticator; print(streamlit_authenticator.Hasher(['your_password']).generate()[0])"
   ```

4. **Add First Firm Account**
   - Access the admin view at: `https://your-app-url.streamlit.app?view=admin`
   - Enter the `admin_secret` from your secrets
   - Fill in firm details and create account
   - Copy the generated credentials and add them to Streamlit secrets under `credentials.usernames.{username}`

5. **Deploy**
   - Streamlit Cloud will auto-deploy on push
   - Monitor the deployment logs for any errors

#### Adding New Firms

1. Access admin view: `https://your-app-url.streamlit.app?view=admin`
2. Enter admin secret
3. Fill in firm details
4. Copy the generated credentials
5. Add credentials to Streamlit secrets
6. Share login details with the firm

---

### Option 2: Local Development

For local testing, you can still run with SQLite and local file storage:

1. **Install dependencies:**
   ```bash
   cd kaizen_lite
   pip install -r requirements.txt
   ```

2. **Set up local secrets:**
   ```bash
   mkdir -p .streamlit
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   # Edit .streamlit/secrets.toml with your local settings
   ```

3. **Run the app:**
   ```bash
   streamlit run main.py
   ```

---

## Architecture

- **main.py**: Main entrypoint with routing logic
- **auth.py**: Streamlit-authenticator integration (uses Streamlit secrets)
- **db.py**: PostgreSQL database helper with scoped queries
- **storage.py**: AWS S3 helper for file uploads/downloads
- **analysis_engine.py**: In-process calls to service_b modules
- **delta_computation.py**: Period-over-period delta logic
- **views/**: Homepage, dashboard, client detail, admin

## Data Isolation

All database queries are scoped by `firm_id`:
- `get_scoped_clients(firm_id)` - only returns that firm's clients
- `get_scoped_reports(firm_id, client_id)` - only returns reports for that firm's client

## Folder Structure

```
/kaizen_lite/
  main.py                  # Streamlit entrypoint
  auth.py                  # Login/session logic
  db.py                    # PostgreSQL helper
  storage.py               # S3 storage helper
  analysis_engine.py       # Service B integration
  delta_computation.py     # Delta logic
  requirements.txt
  .streamlit/
    secrets.toml.example   # Secrets template
  views/
    __init__.py
    homepage.py            # Public homepage
    dashboard.py           # Authenticated dashboard
    client_detail.py       # Client detail view
    admin.py               # Admin view for adding firms
```

## Cloud Architecture

```
Streamlit Cloud App
    ↓
PostgreSQL Database (ElephantSQL/Neon)
    ↓
AWS S3 (PDFs, uploads)
    ↓
Service B (imported via sys.path)
```

## Security Notes

- All credentials stored in Streamlit secrets (never in code)
- Admin view protected by `admin_secret`
- Database queries scoped by `firm_id` for tenant isolation
- S3 bucket should have bucket policy restricting access
