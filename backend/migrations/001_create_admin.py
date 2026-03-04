"""
Database migration script to create initial admin user.
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import User
from api.user_repository import UserRepository


def create_default_admin():
    """Create default admin user if no users exist."""
    user_repo = UserRepository()
    
    # Check if any users exist
    users = user_repo.get_all(include_inactive=True)
    
    if len(users) == 0:
        print("No users found. Creating default admin user...")
        
        admin = User(
            username='admin',
            email='admin@printjobmanager.local',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')  # Default password - CHANGE IN PRODUCTION
        
        created_admin = user_repo.create(admin)
        
        if created_admin:
            print(f"✓ Default admin user created successfully (ID: {created_admin.id})")
            print("  Username: admin")
            print("  Password: admin123")
            print("  ⚠️  IMPORTANT: Change this password immediately!")
            return True
        else:
            print("✗ Failed to create admin user")
            return False
    else:
        print(f"Database already has {len(users)} user(s). Skipping admin creation.")
        return True


if __name__ == '__main__':
    create_default_admin()
