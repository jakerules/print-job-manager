"""
Notification preferences routes.
"""
from flask import Blueprint, request, jsonify
from api.auth_decorators import token_required
from database.db_config import get_connection

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@notifications_bp.route('/preferences', methods=['GET'])
@token_required
def get_preferences(current_user):
    """Get notification preferences for current user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM notification_preferences WHERE user_id = ?', (current_user.id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({
            'success': True,
            'preferences': {
                'browser_notifications': True,
                'sound_alerts': True,
                'email_notifications': False,
                'dnd_enabled': False,
                'dnd_start': '22:00',
                'dnd_end': '07:00',
            }
        }), 200

    return jsonify({
        'success': True,
        'preferences': {
            'browser_notifications': bool(row['browser_notifications']),
            'sound_alerts': bool(row['sound_alerts']),
            'email_notifications': bool(row['email_notifications']),
            'dnd_enabled': bool(row['dnd_enabled']) if 'dnd_enabled' in row.keys() else False,
            'dnd_start': row['dnd_start'] if 'dnd_start' in row.keys() else '22:00',
            'dnd_end': row['dnd_end'] if 'dnd_end' in row.keys() else '07:00',
        }
    }), 200


@notifications_bp.route('/preferences', methods=['PUT'])
@token_required
def update_preferences(current_user):
    """
    Update notification preferences.

    Request body (all optional):
        {
            "browser_notifications": true,
            "sound_alerts": true,
            "email_notifications": false
        }
    """
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()

    # Check if preferences exist
    cursor.execute('SELECT id FROM notification_preferences WHERE user_id = ?', (current_user.id,))
    existing = cursor.fetchone()

    fields = ['browser_notifications', 'sound_alerts', 'email_notifications', 'dnd_enabled']
    str_fields = ['dnd_start', 'dnd_end']

    if existing:
        updates = []
        values = []
        for f in fields:
            if f in data:
                updates.append(f'{f} = ?')
                values.append(1 if data[f] else 0)
        for f in str_fields:
            if f in data:
                updates.append(f'{f} = ?')
                values.append(str(data[f]))
        if updates:
            values.append(current_user.id)
            cursor.execute(
                f'UPDATE notification_preferences SET {", ".join(updates)} WHERE user_id = ?',
                values
            )
    else:
        cursor.execute(
            'INSERT INTO notification_preferences (user_id, browser_notifications, sound_alerts, email_notifications, dnd_enabled, dnd_start, dnd_end) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                current_user.id,
                1 if data.get('browser_notifications', True) else 0,
                1 if data.get('sound_alerts', True) else 0,
                1 if data.get('email_notifications', False) else 0,
                1 if data.get('dnd_enabled', False) else 0,
                data.get('dnd_start', '22:00'),
                data.get('dnd_end', '07:00'),
            )
        )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Preferences updated'
    }), 200
