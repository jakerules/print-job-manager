"""
JWT authentication utilities.
"""
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Secret key for JWT (should be in environment variable in production)
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 30


def generate_token(user_id: int, username: str, role: str, 
                   expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT token for a user.
    
    Args:
        user_id: User's database ID
        username: User's username
        role: User's role (admin, manager, staff, submitter)
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': expire,
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def generate_refresh_token(user_id: int) -> str:
    """
    Generate a long-lived refresh token.
    
    Args:
        user_id: User's database ID
        
    Returns:
        Refresh token string
    """
    expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        'user_id': user_id,
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Extract token from Authorization header.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        Token string or None
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]


def check_role_permission(user_role: str, required_role: str) -> bool:
    """
    Check if user's role has permission for required role.
    Role hierarchy: admin > manager > staff > submitter
    
    Args:
        user_role: User's actual role
        required_role: Required role for the operation
        
    Returns:
        True if user has permission
    """
    role_hierarchy = {
        'admin': 4,
        'manager': 3,
        'staff': 2,
        'submitter': 1
    }
    
    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level
