"""
Tests for User model and password hashing.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.models import User


class TestUserModel:

    def test_set_and_check_password(self):
        user = User(username='test', email='test@test.com')
        user.set_password('mypassword')
        assert user.password_hash != 'mypassword'
        assert user.check_password('mypassword')
        assert not user.check_password('wrongpassword')

    def test_password_hash_is_unique(self):
        u1 = User(username='a', email='a@a.com')
        u2 = User(username='b', email='b@b.com')
        u1.set_password('same')
        u2.set_password('same')
        # bcrypt salts should make hashes different
        assert u1.password_hash != u2.password_hash

    def test_to_dict_excludes_password(self):
        user = User(id=1, username='test', email='test@test.com', role='admin')
        user.set_password('secret')
        d = user.to_dict()
        assert 'password_hash' not in d
        assert d['username'] == 'test'
        assert d['role'] == 'admin'
        assert d['id'] == 1

    def test_default_role_is_submitter(self):
        user = User(username='x', email='x@x.com')
        assert user.role == 'submitter'

    def test_default_is_active(self):
        user = User(username='x', email='x@x.com')
        assert user.is_active is True
