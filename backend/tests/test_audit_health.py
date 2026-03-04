"""
Tests for audit log and system health API endpoints.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from api.audit import audit_bp
from api.health import health_bp


@pytest.fixture
def extended_app(temp_db):
    """Flask app with audit and health blueprints."""
    from flask import Flask
    from flask_cors import CORS
    from api.auth import auth_bp
    from api.users import users_bp
    app = Flask(__name__)
    app.config['TESTING'] = True
    CORS(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(health_bp)
    return app


@pytest.fixture
def ext_client(extended_app):
    return extended_app.test_client()


@pytest.fixture
def mgr_token(ext_client, temp_db, user_repo):
    """Create a manager user and get token."""
    from api.models import User
    user = User(username='testmanager', email='mgr@test.com', role='manager')
    user.set_password('password123')
    user_repo.create(user)
    resp = ext_client.post('/api/auth/login', json={
        'username': 'testmanager', 'password': 'password123'
    })
    return resp.get_json()['access_token']


@pytest.fixture
def ext_admin_token(ext_client, admin_user):
    resp = ext_client.post('/api/auth/login', json={
        'username': 'testadmin', 'password': 'password123'
    })
    return resp.get_json()['access_token']


class TestAuditLog:

    def test_get_empty_audit_log(self, ext_client, mgr_token):
        resp = ext_client.get('/api/audit/log', headers={
            'Authorization': f'Bearer {mgr_token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['total'] == 0

    def test_create_and_retrieve_audit_entry(self, ext_client, mgr_token):
        # Create entry
        resp = ext_client.post('/api/audit/log', headers={
            'Authorization': f'Bearer {mgr_token}'
        }, json={
            'action': 'test_action',
            'resource_type': 'job',
            'resource_id': 'ABC123',
            'details': 'Test audit entry'
        })
        assert resp.status_code == 201

        # Retrieve
        resp = ext_client.get('/api/audit/log', headers={
            'Authorization': f'Bearer {mgr_token}'
        })
        data = resp.get_json()
        assert data['total'] == 1
        assert data['entries'][0]['action'] == 'test_action'
        assert data['entries'][0]['resource_id'] == 'ABC123'

    def test_audit_log_pagination(self, ext_client, mgr_token):
        # Create multiple entries
        for i in range(5):
            ext_client.post('/api/audit/log', headers={
                'Authorization': f'Bearer {mgr_token}'
            }, json={'action': f'action_{i}'})

        resp = ext_client.get('/api/audit/log?limit=2&offset=0', headers={
            'Authorization': f'Bearer {mgr_token}'
        })
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['entries']) == 2

    def test_audit_log_filter_by_action(self, ext_client, mgr_token):
        ext_client.post('/api/audit/log', headers={
            'Authorization': f'Bearer {mgr_token}'
        }, json={'action': 'login'})
        ext_client.post('/api/audit/log', headers={
            'Authorization': f'Bearer {mgr_token}'
        }, json={'action': 'scan_job'})

        resp = ext_client.get('/api/audit/log?action=login', headers={
            'Authorization': f'Bearer {mgr_token}'
        })
        data = resp.get_json()
        assert data['total'] == 1
        assert data['entries'][0]['action'] == 'login'

    def test_submitter_cannot_view_audit_log(self, ext_client, submitter_token):
        resp = ext_client.get('/api/audit/log', headers={
            'Authorization': f'Bearer {submitter_token}'
        })
        assert resp.status_code == 403

    def test_audit_stats(self, ext_client, mgr_token):
        ext_client.post('/api/audit/log', headers={
            'Authorization': f'Bearer {mgr_token}'
        }, json={'action': 'login'})

        resp = ext_client.get('/api/audit/stats', headers={
            'Authorization': f'Bearer {mgr_token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] >= 1


class TestSystemHealth:

    def test_public_health_check(self, ext_client, temp_db):
        resp = ext_client.get('/api/system/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'healthy'
        assert 'uptime_seconds' in data

    def test_detailed_status_requires_manager(self, ext_client, submitter_token):
        resp = ext_client.get('/api/system/status', headers={
            'Authorization': f'Bearer {submitter_token}'
        })
        assert resp.status_code == 403

    def test_detailed_status_for_manager(self, ext_client, mgr_token):
        resp = ext_client.get('/api/system/status', headers={
            'Authorization': f'Bearer {mgr_token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['database']['status'] == 'connected'
        assert data['database']['user_count'] >= 1
        assert 'uptime_seconds' in data
