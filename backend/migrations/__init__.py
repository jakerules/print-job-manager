"""
Database migrations and seed functions.
"""
import os
from api.models import User
from api.user_repository import UserRepository

DEFAULT_ADMIN_PASSWORD = 'admin123'


def seed_admin():
    """Create default admin user if no users exist, and optionally reset the admin password."""
    try:
        user_repo = UserRepository()
        users = user_repo.get_all(include_inactive=True)
        if len(users) == 0:
            admin = User(
                username='admin',
                email='admin@printjobmanager.local',
                role='admin',
                is_active=True
            )
            admin.set_password(DEFAULT_ADMIN_PASSWORD)
            user_repo.create(admin)
            print("✓ Default admin created (admin / admin123)")
        elif os.environ.get('RESET_ADMIN_PASSWORD'):
            # Allow resetting the admin password via environment variable
            admin = user_repo.get_by_username('admin')
            if admin:
                admin.set_password(DEFAULT_ADMIN_PASSWORD)
                user_repo.update(admin)
                print("✓ Admin password reset to default (admin / admin123)")
    except Exception as e:
        print(f"⚠ Admin seed skipped: {e}")
