"""
Tests for user management API endpoints.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestListUsers:

    def test_admin_can_list_users(self, client, admin_token, staff_user):
        resp = client.get('/api/users', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'users' in data
        assert len(data['users']) >= 2

    def test_submitter_cannot_list_users(self, client, submitter_token):
        resp = client.get('/api/users', headers={
            'Authorization': f'Bearer {submitter_token}'
        })
        assert resp.status_code == 403

    def test_no_token_rejected(self, client, temp_db):
        resp = client.get('/api/users')
        assert resp.status_code == 401


class TestCreateUser:

    def test_admin_can_create_user(self, client, admin_token):
        resp = client.post('/api/users', headers={
            'Authorization': f'Bearer {admin_token}'
        }, json={
            'username': 'newbie',
            'email': 'newbie@test.com',
            'password': 'pass123',
            'role': 'staff'
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['user']['username'] == 'newbie'
        assert data['user']['role'] == 'staff'

    def test_create_user_missing_fields(self, client, admin_token):
        resp = client.post('/api/users', headers={
            'Authorization': f'Bearer {admin_token}'
        }, json={
            'username': 'incomplete'
        })
        assert resp.status_code == 400

    def test_staff_cannot_create_users(self, client, staff_token):
        resp = client.post('/api/users', headers={
            'Authorization': f'Bearer {staff_token}'
        }, json={
            'username': 'x', 'email': 'x@x.com', 'password': 'pass', 'role': 'staff'
        })
        assert resp.status_code == 403

    def test_duplicate_username_rejected(self, client, admin_token, admin_user):
        resp = client.post('/api/users', headers={
            'Authorization': f'Bearer {admin_token}'
        }, json={
            'username': 'testadmin',
            'email': 'unique@test.com',
            'password': 'pass123',
            'role': 'staff'
        })
        assert resp.status_code in (400, 409)


class TestGetUser:

    def test_admin_can_get_user(self, client, admin_token, staff_user):
        resp = client.get(f'/api/users/{staff_user.id}', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        assert resp.status_code == 200
        assert resp.get_json()['user']['username'] == 'teststaff'

    def test_get_nonexistent_user(self, client, admin_token):
        resp = client.get('/api/users/9999', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        assert resp.status_code == 404


class TestUpdateUser:

    def test_admin_can_update_user(self, client, admin_token, staff_user):
        resp = client.put(f'/api/users/{staff_user.id}', headers={
            'Authorization': f'Bearer {admin_token}'
        }, json={
            'email': 'updated@test.com',
            'role': 'manager'
        })
        assert resp.status_code == 200

    def test_update_nonexistent_user(self, client, admin_token):
        resp = client.put('/api/users/9999', headers={
            'Authorization': f'Bearer {admin_token}'
        }, json={'email': 'x@x.com'})
        assert resp.status_code == 404


class TestDeleteUser:

    def test_admin_can_delete_user(self, client, admin_token, staff_user):
        resp = client.delete(f'/api/users/{staff_user.id}', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        assert resp.status_code == 200

    def test_staff_cannot_delete_users(self, client, staff_token, admin_user):
        resp = client.delete(f'/api/users/{admin_user.id}', headers={
            'Authorization': f'Bearer {staff_token}'
        })
        assert resp.status_code == 403
