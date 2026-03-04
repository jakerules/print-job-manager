# Backend API

Flask backend for the Print Job Manager system.

## Structure

- `src/` - Print processing logic from original copy-form
- `api/` - REST API routes and WebSocket handlers
- `config/` - Configuration files
- `database/` - SQLite database files
- `migrations/` - Database migration scripts

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
# Development
python -m api.app

# Production
gunicorn api.app:app
```
