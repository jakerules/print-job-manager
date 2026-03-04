"""
Tests for UserRepository database operations.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.models import User


class TestUserRepository:

    def test_create_user(self, user_repo):
        user = User(username='newuser', email='new@test.com', role='staff')
        user.set_password('pass123')
        created = user_repo.create(user)
        assert created is not None
        assert created.id is not None
        assert created.username == 'newuser'

    def test_get_by_id(self, user_repo, admin_user):
        fetched = user_repo.get_by_id(admin_user.id)
        assert fetched is not None
        assert fetched.username == 'testadmin'
        assert fetched.role == 'admin'

    def test_get_by_id_nonexistent(self, user_repo, temp_db):
        assert user_repo.get_by_id(9999) is None

    def test_get_by_username(self, user_repo, admin_user):
        fetched = user_repo.get_by_username('testadmin')
        assert fetched is not None
        assert fetched.id == admin_user.id

    def test_get_by_email(self, user_repo, admin_user):
        fetched = user_repo.get_by_email('admin@test.com')
        assert fetched is not None
        assert fetched.id == admin_user.id

    def test_get_all(self, user_repo, admin_user, staff_user):
        users = user_repo.get_all()
        assert len(users) >= 2
        usernames = [u.username for u in users]
        assert 'testadmin' in usernames
        assert 'teststaff' in usernames

    def test_update_user(self, user_repo, admin_user):
        admin_user.email = 'updated@test.com'
        result = user_repo.update(admin_user)
        assert result is True
        fetched = user_repo.get_by_id(admin_user.id)
        assert fetched.email == 'updated@test.com'

    def test_delete_user_soft(self, user_repo, staff_user):
        result = user_repo.delete(staff_user.id)
        assert result is True
        fetched = user_repo.get_by_id(staff_user.id)
        assert fetched is not None
        assert fetched.is_active is False

    def test_soft_deleted_excluded_from_get_all(self, user_repo, staff_user):
        user_repo.delete(staff_user.id)
        users = user_repo.get_all(include_inactive=False)
        ids = [u.id for u in users]
        assert staff_user.id not in ids

    def test_soft_deleted_included_when_requested(self, user_repo, staff_user):
        user_repo.delete(staff_user.id)
        users = user_repo.get_all(include_inactive=True)
        ids = [u.id for u in users]
        assert staff_user.id in ids

    def test_username_exists(self, user_repo, admin_user):
        assert user_repo.username_exists('testadmin') is True
        assert user_repo.username_exists('nonexistent') is False

    def test_email_exists(self, user_repo, admin_user):
        assert user_repo.email_exists('admin@test.com') is True
        assert user_repo.email_exists('nope@test.com') is False

    def test_username_exists_exclude_self(self, user_repo, admin_user):
        assert user_repo.username_exists('testadmin', exclude_user_id=admin_user.id) is False

    def test_duplicate_username_fails(self, user_repo, admin_user):
        dup = User(username='testadmin', email='other@test.com', role='staff')
        dup.set_password('pass')
        result = user_repo.create(dup)
        assert result is None

    def test_update_last_login(self, user_repo, admin_user):
        user_repo.update_last_login(admin_user.id)
        fetched = user_repo.get_by_id(admin_user.id)
        assert fetched.last_login is not None

    def test_password_survives_round_trip(self, user_repo):
        user = User(username='roundtrip', email='rt@test.com', role='staff')
        user.set_password('mysecret')
        created = user_repo.create(user)
        fetched = user_repo.get_by_id(created.id)
        assert fetched.check_password('mysecret')
        assert not fetched.check_password('wrong')
