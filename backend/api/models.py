"""
SQLAlchemy models for user management.
"""
from datetime import datetime, timezone
from typing import Optional
import bcrypt


class User:
    """User model for authentication and authorization."""
    
    def __init__(self, id: Optional[int] = None, username: str = '', email: str = '',
                 password_hash: str = '', role: str = 'submitter', is_active: bool = True,
                 created_at: Optional[datetime] = None, last_login: Optional[datetime] = None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role  # admin, manager, staff, submitter
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_login = last_login
    
    def set_password(self, password: str):
        """Hash and set the user's password."""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Verify a password against the hash."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self) -> dict:
        """Convert user to dictionary (excluding password)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @classmethod
    def from_db_row(cls, row):
        """Create User instance from database row."""
        try:
            created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        except (ValueError, TypeError):
            created_at = None
        try:
            last_login = datetime.fromisoformat(row['last_login']) if row['last_login'] else None
        except (ValueError, TypeError):
            last_login = None
        return cls(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            password_hash=row['password_hash'],
            role=row['role'],
            is_active=bool(row['is_active']),
            created_at=created_at,
            last_login=last_login
        )


class Session:
    """Session model for token management."""
    
    def __init__(self, id: Optional[int] = None, user_id: int = 0, token: str = '',
                 expires_at: Optional[datetime] = None, created_at: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at
        self.created_at = created_at or datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.now(timezone.utc) > self.expires_at if self.expires_at else True
    
    @classmethod
    def from_db_row(cls, row):
        """Create Session instance from database row."""
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            token=row['token'],
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )


class NotificationPreferences:
    """Notification preferences model."""
    
    def __init__(self, id: Optional[int] = None, user_id: int = 0,
                 browser_notifications: bool = True, sound_alerts: bool = True,
                 email_notifications: bool = False):
        self.id = id
        self.user_id = user_id
        self.browser_notifications = browser_notifications
        self.sound_alerts = sound_alerts
        self.email_notifications = email_notifications
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'browser_notifications': self.browser_notifications,
            'sound_alerts': self.sound_alerts,
            'email_notifications': self.email_notifications
        }
    
    @classmethod
    def from_db_row(cls, row):
        """Create instance from database row."""
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            browser_notifications=bool(row['browser_notifications']),
            sound_alerts=bool(row['sound_alerts']),
            email_notifications=bool(row['email_notifications'])
        )


class AuditLog:
    """Audit log model for tracking user actions."""
    
    def __init__(self, id: Optional[int] = None, user_id: Optional[int] = None,
                 action: str = '', resource_type: Optional[str] = None,
                 resource_id: Optional[str] = None, details: Optional[str] = None,
                 ip_address: Optional[str] = None, timestamp: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details
        self.ip_address = ip_address
        self.timestamp = timestamp or datetime.now(timezone.utc)
    
    @classmethod
    def from_db_row(cls, row):
        """Create instance from database row."""
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            action=row['action'],
            resource_type=row['resource_type'],
            resource_id=row['resource_id'],
            details=row['details'],
            ip_address=row['ip_address'],
            timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None
        )
