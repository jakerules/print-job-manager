# Print Job Manager - Deployment Guide

## Project Status

✅ **Backend API: COMPLETE**
- Full authentication system with JWT
- User management (CRUD)
- Job management with Google Sheets integration
- Real-time WebSocket support
- Role-based access control
- 20+ API endpoints

⏳ **Frontend: READY FOR DEVELOPMENT**
- React + TypeScript setup required
- Vite build tooling
- Socket.IO client integration
- Material-UI or Tailwind CSS

## Quick Start

### Prerequisites
- Python 3.7+
- Google Cloud API credentials (for Google Sheets)
- Node.js 18+ (for frontend development)

### Backend Setup

1. **Navigate to backend directory:**
```bash
cd backend
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure Google Sheets:**
```bash
# Copy config example
cp config/config.ini.example config/config.ini

# Edit config/config.ini with your Google Sheet ID and credentials
nano config/config.ini
```

5. **Place Google API credentials:**
```bash
# Download credentials.json from Google Cloud Console
# Place in backend/ directory
cp /path/to/your/credentials.json ./credentials.json
```

6. **Initialize database:**
```bash
python3 database/db_config.py
python3 migrations/001_create_admin.py
```

7. **Start the API server:**
```bash
python3 api/app.py
```

The API will be available at:
- HTTP: `http://localhost:5000`
- WebSocket: `ws://localhost:5000`

### Default Credentials
```
Username: admin
Password: admin123
```

⚠️ **CHANGE IMMEDIATELY IN PRODUCTION**

## API Endpoints

See [docs/API.md](../docs/API.md) for complete API documentation.

**Key endpoints:**
- `POST /api/auth/login` - Authenticate
- `GET /api/jobs` - List jobs
- `GET /api/jobs/stats` - Get statistics
- `PUT /api/jobs/:id/status` - Update job status
- `GET /api/users` - List users (Admin/Manager)

## WebSocket Events

**Connect to:** `ws://localhost:5000`

**Events:**
- `job:new` - New job submitted
- `job:updated` - Job status changed
- `stats:update` - Statistics updated
- `notification` - User notification

## Frontend Development (Next Steps)

1. **Install Node.js dependencies:**
```bash
cd frontend
npm install
```

2. **Start development server:**
```bash
npm run dev
```

3. **Build for production:**
```bash
npm run build
```

## Production Deployment

### Using Docker (Recommended)

1. **Build backend image:**
```bash
docker build -t print-job-manager-backend ./backend
```

2. **Run with docker-compose:**
```bash
docker-compose up -d
```

### Manual Deployment

1. **Backend (Gunicorn):**
```bash
cd backend
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 --worker-class eventlet api.app:app
```

2. **Frontend (Nginx):**
```bash
cd frontend
npm run build
# Serve dist/ directory with nginx
```

3. **Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket
    location /socket.io {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

## Environment Variables

Create `.env` file in backend directory:

```env
# Flask
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# Database
DATABASE_PATH=./database/users.db

# Google Sheets
GOOGLE_CREDENTIALS_PATH=./credentials.json
SPREADSHEET_ID=your-spreadsheet-id
SHEET_NAME=Sheet1

# Server
PORT=5000
HOST=0.0.0.0
```

## Security Considerations

1. **Change default admin password immediately**
2. **Use strong SECRET_KEY in production**
3. **Enable HTTPS/WSS in production**
4. **Implement rate limiting**
5. **Secure Google API credentials**
6. **Regular security updates**

## Monitoring

**Health Check:**
```bash
curl http://localhost:5000/api/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "print-job-manager-api",
  "websocket": "enabled"
}
```

## Troubleshooting

### Database Issues
```bash
# Reset database
rm backend/database/users.db
python3 backend/database/db_config.py
python3 backend/migrations/001_create_admin.py
```

### Google Sheets Connection
```bash
# Test connection
python3 backend/web_app/app.py
# Check for authentication errors in logs
```

### WebSocket Not Connecting
- Ensure firewall allows port 5000
- Check CORS settings in `api/app.py`
- Verify Socket.IO client version matches server

## Support

For issues or questions:
1. Check logs in `backend/activity.log`
2. Review API documentation in `docs/API.md`
3. Check configuration in `backend/config/config.ini`

## Next Development Steps

1. ✅ Backend API complete
2. ⏳ Frontend React app (Phase 3-8)
3. ⏳ Testing suite (Phase 9)
4. ⏳ Production deployment (Phase 10)

See [PROGRESS.md](../PROGRESS.md) for detailed status.
