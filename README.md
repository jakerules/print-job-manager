# Print Job Manager and Tracking System

A modular print job management and tracking program built on top of the copy-form functionality with a modern React-based web interface, real-time notifications, and role-based access control.

## Quick Start (Docker — no clone needed)

Just download the compose file and run:

```bash
# Download the compose file
curl -O https://raw.githubusercontent.com/jakerules/print-job-manager/master/docker/docker-compose.yml

# Start the app (Docker fetches and builds everything from GitHub)
docker compose up --build -d
```

Then open **http://localhost** and log in with `admin` / `admin123`.

### Optional: Connect Google Sheets

Create a `config/` directory and `credentials.json` next to `docker-compose.yml`:

```
my-folder/
├── docker-compose.yml
├── credentials.json          ← Google Service Account key
└── config/
    └── config.ini            ← your spreadsheet ID + settings
```

`config.ini` example:
```ini
[Google]
spreadsheet_id = YOUR_SPREADSHEET_ID_HERE
sheet_name = Form Responses 1

[Columns]
google_drive_link = 0
quantity = 1
two_sided = 2
paper_size = 3
staples = 4
hole_punch = 5
date_submitted = 6
job_deadline = 7
processed = 8
acknowledged = 12
completed = 13
error_log = 21
```

Then restart: `docker compose up --build -d`

Without these files the app still runs — just without live Google Sheets job data.

## Development Setup (local)

```bash
git clone https://github.com/jakerules/print-job-manager.git
cd print-job-manager

# Backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python3 api/app.py

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Features

- **Dashboard** — Real-time stats, recent jobs, notifications, completion rate, quick actions
- **Job Queue** — Searchable table, detail modal, bulk complete, CSV export, WebSocket updates
- **Barcode Scanner** — USB/Bluetooth + camera scanning, continuous mode, audio feedback, scan history
- **Job Submission** — Web form that writes directly to Google Sheets alongside Google Forms
- **Job Timeline** — Visual timeline view with status icons and filtering
- **Admin Panel** — User CRUD, role assignment, activity log, system health, settings
- **Notifications** — WebSocket real-time, browser push, Do Not Disturb with quiet hours
- **Auth** — JWT tokens, 4 roles (admin/manager/staff/submitter), bcrypt passwords

## Architecture

```
React SPA ←→ Nginx ←→ Flask API ←→ Google Sheets
   ↕                      ↕
Socket.IO              SQLite (users/auth/audit)
```

| Layer | Tech |
|-------|------|
| Frontend | React 18, TypeScript, Vite, Material UI, Redux Toolkit, Socket.IO |
| Backend | Flask, Flask-SocketIO, JWT, bcrypt, Google Sheets API |
| Database | SQLite (users, auth, audit) + Google Sheets (jobs) |
| Deploy | Docker, Nginx reverse proxy, Gunicorn + gevent |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | Login |
| POST | /api/auth/refresh | Refresh token |
| GET | /api/jobs | List jobs (filter, search, paginate) |
| GET | /api/jobs/:id | Get job details |
| POST | /api/jobs/submit | Submit new job |
| POST | /api/jobs/upload-file | Upload print file |
| PUT | /api/jobs/:id/status | Update job status |
| GET | /api/jobs/stats | Job statistics |
| GET/POST/PUT/DELETE | /api/users/* | User CRUD (admin) |
| GET/PUT | /api/notifications/preferences | Notification settings |
| GET/POST | /api/audit/log | Activity log |
| GET | /api/system/health | Health check (public) |
| GET | /api/system/status | System status (manager+) |

See [docs/API.md](docs/API.md) for full reference.

## Documentation

- [Getting Started](GETTING_STARTED.md)
- [API Reference](docs/API.md)
- [Admin Guide](docs/ADMIN_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
