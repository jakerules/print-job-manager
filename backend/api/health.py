"""
System health monitoring routes.
"""
import os
import sys
import time
from flask import Blueprint, jsonify
from api.auth_decorators import token_required, role_required
from database.db_config import get_connection, DB_PATH

health_bp = Blueprint('health', __name__, url_prefix='/api/system')

_start_time = time.time()


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Public health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'print-job-manager',
        'uptime_seconds': int(time.time() - _start_time),
    }), 200


@health_bp.route('/status', methods=['GET'])
@token_required
@role_required('manager')
def system_status(current_user):
    """Detailed system status (Manager+)."""
    # Database check
    db_ok = False
    db_size = 0
    user_count = 0
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        conn.close()
        db_ok = True
        if os.path.exists(DB_PATH):
            db_size = os.path.getsize(DB_PATH)
    except Exception:
        pass

    # Google Sheets check
    sheets_ok = False
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web_app'))
        from web_app.app import get_sheets_service
        svc = get_sheets_service()
        sheets_ok = svc is not None
    except Exception:
        pass

    return jsonify({
        'success': True,
        'uptime_seconds': int(time.time() - _start_time),
        'python_version': sys.version,
        'database': {
            'status': 'connected' if db_ok else 'error',
            'path': str(DB_PATH),
            'size_bytes': db_size,
            'user_count': user_count,
        },
        'google_sheets': {
            'status': 'connected' if sheets_ok else 'not configured',
        },
        'disk': {
            'uploads_dir': os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')),
        },
    }), 200
