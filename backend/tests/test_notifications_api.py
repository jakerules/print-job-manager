"""
Tests for notification preferences API.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from api.notifications import notifications_bp


@pytest.fixture
def notif_app(temp_db):
    """Flask app with notifications blueprint."""
    from flask import Flask
    from flask_cors import CORS
    from api.auth import auth_bp
    app = Flask(__name__)
    app.config['TESTING'] = True
    CORS(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(notifications_bp)
    return app


@pytest.fixture
def notif_client(notif_app):
    return notif_app.test_client()


@pytest.fixture
def notif_token(notif_client, admin_user):
    resp = notif_client.post('/api/auth/login', json={
        'username': 'testadmin', 'password': 'password123'
    })
    return resp.get_json()['access_token']


class TestGetPreferences:

    def test_get_default_preferences(self, notif_client, notif_token):
        resp = notif_client.get('/api/notifications/preferences', headers={
            'Authorization': f'Bearer {notif_token}'
        })
        assert resp.status_code == 200
        prefs = resp.get_json()['preferences']
        assert prefs['browser_notifications'] is True
        assert prefs['sound_alerts'] is True
        assert prefs['email_notifications'] is False

    def test_get_preferences_no_auth(self, notif_client, temp_db):
        resp = notif_client.get('/api/notifications/preferences')
        assert resp.status_code == 401


class TestUpdatePreferences:

    def test_update_preferences(self, notif_client, notif_token):
        resp = notif_client.put('/api/notifications/preferences', headers={
            'Authorization': f'Bearer {notif_token}'
        }, json={
            'sound_alerts': False,
            'email_notifications': True
        })
        assert resp.status_code == 200

        # Verify
        resp = notif_client.get('/api/notifications/preferences', headers={
            'Authorization': f'Bearer {notif_token}'
        })
        prefs = resp.get_json()['preferences']
        assert prefs['sound_alerts'] is False
        assert prefs['email_notifications'] is True
        assert prefs['browser_notifications'] is True  # unchanged

    def test_update_without_existing_row(self, notif_client, notif_token):
        # Delete existing preferences first
        from database.db_config import get_connection
        conn = get_connection()
        conn.execute('DELETE FROM notification_preferences')
        conn.commit()
        conn.close()

        resp = notif_client.put('/api/notifications/preferences', headers={
            'Authorization': f'Bearer {notif_token}'
        }, json={'browser_notifications': False})
        assert resp.status_code == 200

        resp = notif_client.get('/api/notifications/preferences', headers={
            'Authorization': f'Bearer {notif_token}'
        })
        prefs = resp.get_json()['preferences']
        assert prefs['browser_notifications'] is False
