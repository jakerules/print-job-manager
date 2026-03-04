"""
Tests for authentication API endpoints.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestLogin:

    def test_successful_login(self, client, admin_user):
        resp = client.post('/api/auth/login', json={
            'username': 'testadmin',
            'password': 'password123'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['user']['username'] == 'testadmin'

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post('/api/auth/login', json={
            'username': 'testadmin',
            'password': 'wrongpassword'
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client, temp_db):
        resp = client.post('/api/auth/login', json={
            'username': 'nobody',
            'password': 'password123'
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client, temp_db):
        resp = client.post('/api/auth/login', json={})
        assert resp.status_code == 400

    def test_login_inactive_user(self, client, admin_user, user_repo):
        user_repo.delete(admin_user.id)  # soft-delete
        resp = client.post('/api/auth/login', json={
            'username': 'testadmin',
            'password': 'password123'
        })
        assert resp.status_code == 403


class TestRefreshToken:

    def test_refresh_token(self, client, admin_user):
        # First login
        login_resp = client.post('/api/auth/login', json={
            'username': 'testadmin',
            'password': 'password123'
        })
        refresh_token = login_resp.get_json()['refresh_token']

        # Refresh
        resp = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'access_token' in data

    def test_refresh_with_invalid_token(self, client, temp_db):
        resp = client.post('/api/auth/refresh', json={
            'refresh_token': 'invalid.token.here'
        })
        assert resp.status_code == 401

    def test_refresh_missing_token(self, client, temp_db):
        resp = client.post('/api/auth/refresh', json={})
        assert resp.status_code == 400


class TestAuthenticatedEndpoints:

    def test_get_me(self, client, admin_token):
        resp = client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['user']['username'] == 'testadmin'

    def test_get_me_no_token(self, client, temp_db):
        resp = client.get('/api/auth/me')
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, client, temp_db):
        resp = client.get('/api/auth/me', headers={
            'Authorization': 'Bearer invalid.token'
        })
        assert resp.status_code == 401

    def test_logout(self, client, admin_token):
        resp = client.post('/api/auth/logout', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        assert resp.status_code == 200

    def test_change_password(self, client, admin_token):
        resp = client.post('/api/auth/change-password', headers={
            'Authorization': f'Bearer {admin_token}'
        }, json={
            'current_password': 'password123',
            'new_password': 'newpassword456'
        })
        assert resp.status_code == 200

        # Verify new password works
        resp = client.post('/api/auth/login', json={
            'username': 'testadmin',
            'password': 'newpassword456'
        })
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, client, admin_token):
        resp = client.post('/api/auth/change-password', headers={
            'Authorization': f'Bearer {admin_token}'
        }, json={
            'current_password': 'wrongcurrent',
            'new_password': 'newpass'
        })
        assert resp.status_code == 401

    def test_change_password_too_short(self, client, admin_token):
        resp = client.post('/api/auth/change-password', headers={
            'Authorization': f'Bearer {admin_token}'
        }, json={
            'current_password': 'password123',
            'new_password': 'ab'
        })
        assert resp.status_code == 400
