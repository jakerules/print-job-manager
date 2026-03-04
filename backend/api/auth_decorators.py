"""
Flask-Login integration and user loader.
"""
from functools import wraps
from flask import request, jsonify
from api.auth_utils import get_token_from_header, verify_token, check_role_permission
from api.user_repository import UserRepository


def token_required(f):
    """
    Decorator to require valid JWT token for route access.
    Adds 'current_user' to kwargs.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header(request.headers.get('Authorization'))
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        # Load user from database
        user_repo = UserRepository()
        user = user_repo.get_by_id(payload['user_id'])
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Add current_user to kwargs
        kwargs['current_user'] = user
        return f(*args, **kwargs)
    
    return decorated


def role_required(required_role: str):
    """
    Decorator to require specific role for route access.
    Must be used after @token_required.
    
    Args:
        required_role: Minimum role required (admin, manager, staff, submitter)
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user = kwargs.get('current_user')
            
            if not current_user:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not check_role_permission(current_user.role, required_role):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    @role_required('admin')
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated


def get_current_user_from_token(token: str):
    """
    Get current user object from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        User object or None
    """
    payload = verify_token(token)
    if not payload:
        return None
    
    user_repo = UserRepository()
    return user_repo.get_by_id(payload['user_id'])
