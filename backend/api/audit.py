"""
Audit log routes - view user activity and system events.
"""
from flask import Blueprint, request, jsonify
from api.auth_decorators import token_required, role_required
from database.db_config import get_connection

audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit')


@audit_bp.route('/log', methods=['GET'])
@token_required
@role_required('manager')
def get_audit_log(current_user):
    """
    Get audit log entries with pagination.

    Query params:
        limit: Max results (default 50)
        offset: Pagination offset (default 0)
        user_id: Filter by user (optional)
        action: Filter by action type (optional)
    """
    limit = min(int(request.args.get('limit', 50)), 200)
    offset = int(request.args.get('offset', 0))
    user_id = request.args.get('user_id')
    action = request.args.get('action')

    conn = get_connection()
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if user_id:
        where_clauses.append('a.user_id = ?')
        params.append(int(user_id))
    if action:
        where_clauses.append('a.action LIKE ?')
        params.append(f'%{action}%')

    where_sql = f'WHERE {" AND ".join(where_clauses)}' if where_clauses else ''

    # Count
    cursor.execute(f'SELECT COUNT(*) FROM audit_log a {where_sql}', params)
    total = cursor.fetchone()[0]

    # Fetch with user join
    cursor.execute(f'''
        SELECT a.*, u.username
        FROM audit_log a
        LEFT JOIN users u ON a.user_id = u.id
        {where_sql}
        ORDER BY a.timestamp DESC
        LIMIT ? OFFSET ?
    ''', params + [limit, offset])

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'username': row['username'],
            'action': row['action'],
            'resource_type': row['resource_type'],
            'resource_id': row['resource_id'],
            'details': row['details'],
            'ip_address': row['ip_address'],
            'timestamp': row['timestamp'],
        })

    return jsonify({
        'success': True,
        'entries': entries,
        'total': total,
        'limit': limit,
        'offset': offset,
    }), 200


@audit_bp.route('/log', methods=['POST'])
@token_required
def create_audit_entry(current_user):
    """Log an audit event. Used internally and by staff."""
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        current_user.id,
        data.get('action', 'unknown'),
        data.get('resource_type'),
        data.get('resource_id'),
        data.get('details'),
        request.remote_addr,
    ))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Audit entry logged'}), 201


@audit_bp.route('/stats', methods=['GET'])
@token_required
@role_required('manager')
def get_audit_stats(current_user):
    """Get audit log statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM audit_log')
    total = cursor.fetchone()[0]

    cursor.execute('''
        SELECT action, COUNT(*) as count
        FROM audit_log
        GROUP BY action
        ORDER BY count DESC
        LIMIT 10
    ''')
    by_action = [{'action': r['action'], 'count': r['count']} for r in cursor.fetchall()]

    cursor.execute('''
        SELECT u.username, COUNT(*) as count
        FROM audit_log a
        JOIN users u ON a.user_id = u.id
        GROUP BY a.user_id
        ORDER BY count DESC
        LIMIT 10
    ''')
    by_user = [{'username': r['username'], 'count': r['count']} for r in cursor.fetchall()]

    conn.close()

    return jsonify({
        'success': True,
        'total': total,
        'by_action': by_action,
        'by_user': by_user,
    }), 200
