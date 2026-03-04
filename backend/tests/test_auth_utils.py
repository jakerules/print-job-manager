"""
Tests for JWT token utilities.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import timedelta
from api.auth_utils import (
    generate_token, generate_refresh_token, verify_token,
    get_token_from_header, check_role_permission
)


class TestTokenGeneration:

    def test_generate_and_verify_access_token(self):
        token = generate_token(1, 'admin', 'admin')
        payload = verify_token(token)
        assert payload is not None
        assert payload['user_id'] == 1
        assert payload['username'] == 'admin'
        assert payload['role'] == 'admin'

    def test_generate_and_verify_refresh_token(self):
        token = generate_refresh_token(42)
        payload = verify_token(token)
        assert payload is not None
        assert payload['user_id'] == 42
        assert payload['type'] == 'refresh'

    def test_expired_token_returns_none(self):
        token = generate_token(1, 'u', 'admin', expires_delta=timedelta(seconds=-1))
        assert verify_token(token) is None

    def test_invalid_token_returns_none(self):
        assert verify_token('not.a.valid.token') is None
        assert verify_token('') is None

    def test_different_users_get_different_tokens(self):
        t1 = generate_token(1, 'user1', 'admin')
        t2 = generate_token(2, 'user2', 'staff')
        assert t1 != t2


class TestTokenFromHeader:

    def test_valid_bearer_header(self):
        assert get_token_from_header('Bearer abc123') == 'abc123'

    def test_missing_header(self):
        assert get_token_from_header(None) is None

    def test_no_bearer_prefix(self):
        assert get_token_from_header('abc123') is None

    def test_wrong_prefix(self):
        assert get_token_from_header('Token abc123') is None

    def test_extra_parts(self):
        assert get_token_from_header('Bearer abc 123') is None


class TestRolePermission:

    def test_admin_has_all_permissions(self):
        assert check_role_permission('admin', 'admin')
        assert check_role_permission('admin', 'manager')
        assert check_role_permission('admin', 'staff')
        assert check_role_permission('admin', 'submitter')

    def test_manager_permissions(self):
        assert not check_role_permission('manager', 'admin')
        assert check_role_permission('manager', 'manager')
        assert check_role_permission('manager', 'staff')
        assert check_role_permission('manager', 'submitter')

    def test_staff_permissions(self):
        assert not check_role_permission('staff', 'admin')
        assert not check_role_permission('staff', 'manager')
        assert check_role_permission('staff', 'staff')
        assert check_role_permission('staff', 'submitter')

    def test_submitter_permissions(self):
        assert not check_role_permission('submitter', 'admin')
        assert not check_role_permission('submitter', 'staff')
        assert check_role_permission('submitter', 'submitter')

    def test_unknown_role(self):
        assert not check_role_permission('unknown', 'submitter')
