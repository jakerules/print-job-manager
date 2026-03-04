# Print Job Manager - Getting Started

## Prerequisites

- **Python 3.10+** (backend)
- **Node.js 18+** (frontend, optional for development)
- **Google Cloud** credentials with Sheets API enabled
- **Docker** (optional, for production deployment)

## Quick Start

### 1. Clone & Setup

```bash
cd print-job-manager
./deploy.sh setup
```

Or manually:

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -c "from database.db_config import init_db; init_db()"
python3 migrations/run_migrations.py

# Frontend (requires Node.js)
cd ../frontend
npm install
```

### 2. Configure Google Sheets

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the Google Sheets API
3. Create a Service Account and download `credentials.json`
4. Place `credentials.json` in `backend/config/`
5. Copy `backend/config/config.ini.example` to `backend/config/config.ini`
6. Set your `spreadsheet_id` and `sheet_name` in `config.ini`
7. Share your Google Sheet with the service account email

### 3. Run

```bash
# Development (backend + frontend)
./deploy.sh dev

# Or separately:
cd backend && source venv/bin/activate && python3 api/app.py
cd frontend && npm run dev
```

- **Backend**: http://localhost:5000
- **Frontend**: http://localhost:5173
- **Login**: admin / admin123

### 4. Run Tests

```bash
./deploy.sh test
# or: cd backend && source venv/bin/activate && python3 -m pytest tests/ -v
```

## Google Sheets Column Format

Your Google Sheet must have this column layout (matching Google Forms output):

| Col | Field | Example |
|-----|-------|---------|
| A | Timestamp | 3/4/2026 14:30:00 |
| B | Staff Notes | (blank) |
| C | Email | user@example.com |
| D | Room | 301 |
| E | Quantity | 25 |
| F | Paper Size | Letter |
| G | Two-Sided | Yes/No |
| H | Color | Yes/No |
| I | Stapled | Yes/No |
| J | Deadline | 3/15/2026 |
| K | File URL | (Google Drive link) |
| L | User Notes | Special instructions |
| M | Acknowledged | TRUE/FALSE |
| N | Completed | TRUE/FALSE |
| O | Job ID | 9E8B7BBF |

## User Roles

| Role | Dashboard | Queue | Scanner | Submit | Admin |
|------|-----------|-------|---------|--------|-------|
| Admin | ✅ Full | ✅ Full | ✅ | ✅ | ✅ |
| Manager | ✅ Full | ✅ Full | ✅ | ✅ | ❌ |
| Staff | ✅ Basic | ✅ Update | ✅ | ✅ | ❌ |
| Submitter | ✅ Own jobs | ✅ View own | ❌ | ✅ | ❌ |

## API Quick Reference

```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Use the returned access_token:
TOKEN="eyJ..."

# List jobs
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/jobs?status=pending&limit=20

# Get job stats
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/jobs/stats

# Submit a new job
curl -X POST http://localhost:5000/api/jobs/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","room":"301","quantity":25,"paper_size":"Letter"}'

# Update job status
curl -X PUT http://localhost:5000/api/jobs/9E8B7BBF/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged":true,"completed":true}'
```

See [docs/API.md](docs/API.md) for the full endpoint reference.

## Production Deployment

### Docker (Recommended)

```bash
cd docker
docker compose up --build -d
```

This starts:
- **Backend** on port 5000 (Flask + gunicorn)
- **Frontend** on port 80 (nginx serving React build)

### Manual

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Nginx, systemd, and SSL setup.

## Troubleshooting

**"Google Sheets service unavailable"**
- Check that `credentials.json` exists in `backend/config/`
- Verify the service account has access to the spreadsheet
- Check `config.ini` has the correct `spreadsheet_id`

**"Token is invalid or expired"**
- Access tokens expire after 1 hour — use the refresh endpoint
- The frontend auto-refreshes tokens via axios interceptor

**Backend won't start**
- Activate the venv first: `source backend/venv/bin/activate`
- Check all deps installed: `pip install -r requirements.txt`

**Frontend won't build**
- Requires Node.js 18+: `node --version`
- Clear node_modules: `rm -rf node_modules && npm install`
