# Print Job Manager and Tracking System

A modular print job management and tracking program built on top of the copy-form functionality with a modern React-based web interface, real-time notifications, and role-based access control.

## 🎉 Current Status: Core Implementation Complete!

✅ **Backend API** - 25+ REST API endpoints + WebSocket support  
✅ **Frontend** - React + TypeScript SPA with all core components  
✅ **Docker** - Containerized deployment ready  
⏳ **Testing** - Requires Node.js install to build frontend

## Features

### ✅ Dashboard
- Real-time stat cards (pending, in-progress, completed)
- Recent jobs list with status chips
- Notifications panel with unread badge
- Completion rate progress bar (Manager+)
- Quick action buttons (Scan, Queue, Refresh)
- Role-based visibility controls

### ✅ Job Queue Manager
- Searchable/filterable job table
- Job detail modal with full info
- Bulk select and complete operations
- CSV export of job list
- Real-time WebSocket updates
- Responsive columns (mobile-friendly)

### ✅ Barcode Scanner
- Manual/barcode entry with auto-uppercase
- Auto-update status on scan (pending→acknowledged→completed)
- Continuous scanning mode
- Scan history (last 50)
- Audio feedback on success/error
- Manual status override buttons

### ✅ Direct Job Submission
- Web-based form (bypasses Google Forms)
- Server-generated 8-char hex Job IDs
- File upload support
- Success page with tracking ID
- Works alongside existing Google Form method

### ✅ Admin Panel
- User CRUD with table view
- Create/edit/delete user dialogs
- Role assignment (admin/manager/staff/submitter)
- Active/disabled user toggle
- System settings tab

### ✅ Authentication & Security
- JWT access + refresh tokens
- 4 user roles with hierarchy
- Bcrypt password hashing
- Protected routes (frontend + backend)
- Audit logging capability

## Quick Start

### Backend
```bash
cd backend
source venv/bin/activate
python3 api/app.py
```

### Frontend (requires Node.js 18+)
```bash
cd frontend
npm install
npm run dev
```

### Docker
```bash
cd docker
docker-compose up --build
```

**Default Credentials:** admin / admin123

## Architecture

```
React SPA ←→ Flask API ←→ Google Sheets
   ↕              ↕
Socket.IO     SQLite (users)
```

- **Frontend:** React 18, TypeScript, Vite, MUI, Redux Toolkit, Socket.IO client
- **Backend:** Flask, Flask-SocketIO, JWT, bcrypt, Google Sheets API
- **Database:** SQLite (users/auth) + Google Sheets (jobs)
- **Deploy:** Docker + Nginx reverse proxy

## Project Structure

```
print-job-manager/
├── backend/
│   ├── api/              # Flask API (app, auth, jobs, users, websocket)
│   ├── database/         # SQLite database
│   ├── src/              # Original print processing logic
│   ├── web_app/          # Original copy-form (imported by jobs.py)
│   └── venv/             # Python virtual environment
├── frontend/
│   └── src/
│       ├── components/   # Dashboard, QueueManager, Scanner, AdminPanel, JobSubmission
│       ├── services/     # API client, auth, jobs, websocket
│       ├── store/        # Redux (auth, jobs)
│       └── types/        # TypeScript interfaces
├── docker/               # Dockerfiles + docker-compose + nginx
├── docs/                 # API.md, DEPLOYMENT.md
├── GETTING_STARTED.md
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | Login |
| POST | /api/auth/refresh | Refresh token |
| GET | /api/jobs | List jobs (filter, search, paginate) |
| GET | /api/jobs/:id | Get job details |
| POST | /api/jobs/submit | Submit new job |
| POST | /api/jobs/upload-file | Upload print file |
| PUT | /api/jobs/:id/status | Update status |
| PUT | /api/jobs/:id/notes | Update notes |
| GET | /api/jobs/stats | Job statistics |
| GET/POST/PUT/DELETE | /api/users/* | User CRUD (admin) |

See [docs/API.md](docs/API.md) for full reference.

## Progress

- ✅ 69 tasks complete
- ⏳ 37 tasks remaining (mostly testing, deployment polish, optional features)
- 📊 65% complete

**Phases Complete:** 1-8.5 (Backend + Frontend + Job Submission)  
**Remaining:** Testing, deployment polish, optional features (camera scan, email notifications, etc.)

## Documentation

- [Getting Started](GETTING_STARTED.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
