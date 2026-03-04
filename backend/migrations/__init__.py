"""
Database migrations and seed functions.
"""
from api.models import User
from api.user_repository import UserRepository


def seed_admin():
    """Create default admin user if no users exist."""
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
            admin.set_password('admin123')
            user_repo.create(admin)
            print("✓ Default admin created (admin / admin123)")
    except Exception as e:
        print(f"⚠ Admin seed skipped: {e}")
