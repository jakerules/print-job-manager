# Admin Guide — Print Job Manager

## Initial Setup

### 1. Configure Google Sheets
1. Place `credentials.json` (Google Service Account key) in `backend/web_app/`
2. Edit `backend/web_app/config.ini`:
   ```ini
   [Google]
   spreadsheet_id = YOUR_SHEET_ID
   sheet_name = Form Responses 1
   ```
3. Share the Google Sheet with the service account email

### 2. Start the Application
```bash
# Development
./deploy.sh dev

# Production (Docker)
./deploy.sh prod
```

### 3. Default Login
- **Username**: `admin`
- **Password**: `admin123`
- ⚠️ Change this immediately after first login

---

## User Management

Navigate to **Admin → Users** tab.

### Roles
| Role | Description |
|------|-------------|
| **Admin** | Full access: user management, settings, all jobs |
| **Manager** | View all jobs, audit log, system status |
| **Staff** | Scan barcodes, update job status, view queue |
| **Submitter** | Submit jobs, view own jobs only |

### Creating Users
1. Click **Add User**
2. Fill in username, email, password, and role
3. Click **Create**

### Deactivating Users
- Edit user → uncheck **Active** → Save
- Deactivated users cannot log in but their data is preserved

---

## System Health

Navigate to **Admin → Health** tab.

- **Database**: Shows connection status, user count, and DB size
- **Google Sheets**: Shows connection status with a **Test Connection** button
- **Uptime**: How long the backend has been running

---

## Activity Log

Navigate to **Admin → Activity** tab.

- View all user actions (logins, scans, updates, deletions)
- Filter by action type
- Paginated for performance

---

## Job Workflow

```
New Job → Pending → Acknowledged (printed) → Completed
```

1. Jobs arrive via Google Form or the **Submit Job** page
2. The print processor picks them up and prints receipts with barcodes
3. Staff scan barcodes or use the Queue Manager to acknowledge/complete
4. Dashboard shows real-time statistics

---

## Barcode Scanning

### USB/Bluetooth Scanners
- Navigate to **Scanner** page
- Focus the input field
- Scan a barcode — the job ID auto-populates
- Click **Mark Acknowledged** or **Mark Completed**

### Camera Scanning
- Toggle **Use Camera** on the Scanner page
- Point camera at the barcode on the printed receipt
- Requires HTTPS in production (browser camera security requirement)

---

## Docker Deployment

### Starting
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Environment Variables
Set in `docker/docker-compose.yml` or `.env`:
| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | JWT signing key | Random per restart |
| `FLASK_ENV` | `development` or `production` | `production` |
| `TZ` | Container timezone | `America/New_York` |

### SSL
For HTTPS, configure your certificates in `docker/nginx.conf` or use a reverse proxy (Cloudflare, Caddy, etc.).

---

## TrueNAS SCALE Deployment

### 1. Create a dataset
In the TrueNAS UI: **Storage → Create Dataset** (e.g., `pool/apps/print-job-manager`).

### 2. Download the TrueNAS compose file
```bash
cd /mnt/pool/apps/print-job-manager
curl -O https://raw.githubusercontent.com/jakerules/print-job-manager/master/docker/docker-compose.truenas.yml
mv docker-compose.truenas.yml docker-compose.yml
```

### 3. Set a JWT secret
Edit `docker-compose.yml` and replace `CHANGE-ME-use-a-random-string-here` with a random string:
```bash
# Generate one with:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Start
```bash
docker compose up --build -d
```

### 5. Access
Open **http://YOUR_TRUENAS_IP:9080** (port 9080 avoids conflict with TrueNAS UI).

### Notes for TrueNAS
- **Ports**: Frontend is on `9080`, backend API on `5080`. TrueNAS uses `80/443`.
- **Data**: SQLite database and uploads are stored on ZFS at `./database/` and `./uploads/`.
- **Backups**: Snapshot the dataset in TrueNAS for instant backup/rollback.
- **Updates**: `docker compose up --build -d` pulls latest code from GitHub and rebuilds.

---

## Backup & Restore

### Database
```bash
# Backup
cp backend/database/users.db backend/database/users.db.backup

# Restore
cp backend/database/users.db.backup backend/database/users.db
```

### Google Sheets
Job data lives in Google Sheets — use Google's built-in version history for recovery.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't log in | Check username/password. Reset via SQLite if locked out. |
| Google Sheets "not configured" | Verify `credentials.json` exists and `config.ini` has correct sheet ID |
| WebSocket not connecting | Check that port 5000 is accessible. Nginx must proxy `/socket.io/` |
| Camera not working | Requires HTTPS. Check browser permissions. |
| Thermal printer not printing | Windows only. Check `pywin32` is installed and printer name in config matches |
