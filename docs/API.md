# Print Job Manager API Documentation

## Base URL
```
http://localhost:5000/api
```

## Authentication
All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

## Endpoints

### Authentication

#### POST /auth/login
Login and receive JWT tokens.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "success": true,
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@printjobmanager.local",
    "role": "admin",
    "is_active": true
  }
}
```

#### POST /auth/logout
Logout (client should delete tokens).

#### POST /auth/refresh
Refresh access token using refresh token.

#### GET /auth/me
Get current user information.

#### POST /auth/change-password
Change user password.

### User Management (Admin/Manager)

#### GET /users
List all users. Requires Manager or Admin role.

**Query Parameters:**
- `include_inactive` (boolean): Include inactive users

#### POST /users (Admin only)
Create new user.

**Request:**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "password123",
  "role": "staff"
}
```

#### GET /users/:id
Get user details.

#### PUT /users/:id (Admin only)
Update user.

#### DELETE /users/:id (Admin only)
Soft delete user (sets is_active to false).

### Job Management

#### GET /jobs
List jobs with filtering and pagination.

**Query Parameters:**
- `status`: Filter by status (pending, acknowledged, completed)
- `search`: Search by job ID, email, or room
- `limit`: Number of results (default: 50)
- `offset`: Offset for pagination (default: 0)

**Response:**
```json
{
  "success": true,
  "jobs": [...],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

#### GET /jobs/:job_id
Get job details by ID.

#### PUT /jobs/:job_id/status (Staff+)
Update job status.

**Request:**
```json
{
  "acknowledged": true,
  "completed": false
}
```

#### PUT /jobs/:job_id/notes (Staff+)
Update staff notes.

**Request:**
```json
{
  "notes": "Printed and delivered to room 305"
}
```

#### GET /jobs/stats
Get job statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total": 150,
    "pending": 45,
    "acknowledged": 78,
    "completed": 27
  }
}
```

## WebSocket Events

Connect to: `ws://localhost:5000`

### Client Events

#### connect
Triggered when client connects.

#### join_notifications
Join notification room for real-time updates.

**Emit:**
```json
{
  "user_id": 1
}
```

### Server Events

#### connected
Server acknowledges connection.

#### job:new
New job added to queue.

```json
{
  "job": {...},
  "timestamp": "2026-03-04T19:59:00"
}
```

#### job:updated
Job status updated.

```json
{
  "job_id": "9E8B7BBF",
  "action": "acknowledged",
  "job": {...},
  "timestamp": "2026-03-04T19:59:00"
}
```

#### stats:update
Statistics updated.

```json
{
  "stats": {
    "total": 150,
    "pending": 45,
    "acknowledged": 79,
    "completed": 26
  },
  "timestamp": "2026-03-04T19:59:00"
}
```

#### notification
User-specific notification.

```json
{
  "type": "info",
  "message": "New job submitted",
  "data": {...},
  "timestamp": "2026-03-04T19:59:00"
}
```

## User Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full system access, user management |
| **manager** | View all jobs, manage jobs, view stats |
| **staff** | Scan barcodes, update job status, view all jobs |
| **submitter** | Submit jobs, view own jobs only |

## Error Responses

All errors follow this format:

```json
{
  "error": "Description of the error"
}
```

**Status Codes:**
- `400` - Bad Request (missing/invalid parameters)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (duplicate username/email)
- `500` - Internal Server Error

## Rate Limiting

Currently no rate limiting. Will be added in production.

## Examples

### Login and List Jobs

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

# List jobs
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/jobs?limit=10

# Get stats
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/jobs/stats
```

### Update Job Status

```bash
curl -X PUT http://localhost:5000/api/jobs/9E8B7BBF/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged": true}'
```

### Job Submission

#### POST /jobs/submit
Submit a new print job directly (bypasses Google Forms).

**Auth:** Any authenticated user

**Request:**
```json
{
  "email": "user@example.com",
  "room": "301",
  "quantity": 25,
  "paper_size": "Letter",
  "two_sided": false,
  "color": false,
  "stapled": false,
  "deadline": "2026-03-15",
  "notes": "Special instructions",
  "file_url": "/uploads/abc123.pdf"
}
```

**Response (201):**
```json
{
  "success": true,
  "job_id": "9E8B7BBF",
  "message": "Job 9E8B7BBF submitted successfully"
}
```

#### POST /jobs/upload-file
Upload a file for a print job.

**Auth:** Any authenticated user

**Request:** `multipart/form-data` with `file` field

**Response (200):**
```json
{
  "success": true,
  "file_url": "/uploads/abc123def456.pdf",
  "original_name": "homework.pdf",
  "size": 1234567
}
```

---

### Notifications

#### GET /notifications/preferences
Get notification preferences for current user.

**Auth:** Any authenticated user

**Response (200):**
```json
{
  "success": true,
  "preferences": {
    "browser_notifications": true,
    "sound_alerts": true,
    "email_notifications": false
  }
}
```

#### PUT /notifications/preferences
Update notification preferences.

**Auth:** Any authenticated user

**Request (all fields optional):**
```json
{
  "browser_notifications": true,
  "sound_alerts": false,
  "email_notifications": true
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Preferences updated"
}
```

---

### WebSocket Events

Connect via Socket.IO at `ws://localhost:5000`

#### Client → Server
| Event | Payload | Description |
|-------|---------|-------------|
| `connect` | — | Establish connection |
| `disconnect` | — | Disconnect |

#### Server → Client
| Event | Payload | Description |
|-------|---------|-------------|
| `job:new` | `{job: {...}}` | New job submitted |
| `job:updated` | `{job: {...}}` | Job status changed |
| `stats:update` | `{stats: {...}}` | Job statistics changed |
| `notification` | `{message, type}` | User notification |
