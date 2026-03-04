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
                'email_notifications': False
            }
        }), 200

    return jsonify({
        'success': True,
        'preferences': {
            'browser_notifications': bool(row['browser_notifications']),
            'sound_alerts': bool(row['sound_alerts']),
            'email_notifications': bool(row['email_notifications'])
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

    fields = ['browser_notifications', 'sound_alerts', 'email_notifications']

    if existing:
        updates = []
        values = []
        for f in fields:
            if f in data:
                updates.append(f'{f} = ?')
                values.append(1 if data[f] else 0)
        if updates:
            values.append(current_user.id)
            cursor.execute(
                f'UPDATE notification_preferences SET {", ".join(updates)} WHERE user_id = ?',
                values
            )
    else:
        cursor.execute(
            'INSERT INTO notification_preferences (user_id, browser_notifications, sound_alerts, email_notifications) VALUES (?, ?, ?, ?)',
            (
                current_user.id,
                1 if data.get('browser_notifications', True) else 0,
                1 if data.get('sound_alerts', True) else 0,
                1 if data.get('email_notifications', False) else 0,
            )
        )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Preferences updated'
    }), 200
