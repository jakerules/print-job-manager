"""
User repository for database operations.
"""
from datetime import datetime, timezone
from typing import Optional, List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_config import get_connection
from api.models import User, NotificationPreferences


class UserRepository:
    """Repository for user database operations."""
    
    def create(self, user: User) -> Optional[User]:
        """Create a new user."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.username, user.email, user.password_hash, user.role, user.is_active))
            
            user.id = cursor.lastrowid
            
            # Create default notification preferences
            cursor.execute('''
                INSERT INTO notification_preferences (user_id)
                VALUES (?)
            ''', (user.id,))
            
            conn.commit()
            return user
        except Exception as e:
            conn.rollback()
            print(f"Error creating user: {e}")
            return None
        finally:
            conn.close()
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User.from_db_row(row)
        return None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User.from_db_row(row)
        return None
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User.from_db_row(row)
        return None
    
    def get_all(self, include_inactive: bool = False) -> List[User]:
        """Get all users."""
        conn = get_connection()
        cursor = conn.cursor()
        
        if include_inactive:
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        else:
            cursor.execute('SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [User.from_db_row(row) for row in rows]
    
    def update(self, user: User) -> bool:
        """Update user."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users
                SET username = ?, email = ?, password_hash = ?, role = ?, is_active = ?, last_login = ?
                WHERE id = ?
            ''', (user.username, user.email, user.password_hash, user.role, user.is_active,
                  user.last_login.isoformat() if user.last_login else None, user.id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating user: {e}")
            return False
        finally:
            conn.close()
    
    def delete(self, user_id: int) -> bool:
        """Delete user (or mark as inactive)."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Soft delete by setting is_active to False
            cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting user: {e}")
            return False
        finally:
            conn.close()
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET last_login = ? WHERE id = ?
        ''', (datetime.now(timezone.utc).isoformat(), user_id))
        
        conn.commit()
        conn.close()
    
    def username_exists(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if username already exists."""
        conn = get_connection()
        cursor = conn.cursor()
        
        if exclude_user_id:
            cursor.execute('SELECT COUNT(*) FROM users WHERE username = ? AND id != ?',
                         (username, exclude_user_id))
        else:
            cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email already exists."""
        conn = get_connection()
        cursor = conn.cursor()
        
        if exclude_user_id:
            cursor.execute('SELECT COUNT(*) FROM users WHERE email = ? AND id != ?',
                         (email, exclude_user_id))
        else:
            cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
