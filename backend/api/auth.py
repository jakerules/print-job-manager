"""
Authentication routes for login, logout, and token management.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import User
from api.user_repository import UserRepository
from api.auth_utils import generate_token, generate_refresh_token, verify_token
from api.auth_decorators import token_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
user_repo = UserRepository()


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint.
    
    Request body:
        {
            "username": "string",
            "password": "string"
        }
        
    Response:
        {
            "success": true,
            "access_token": "string",
            "refresh_token": "string",
            "user": {...}
        }
    """
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    username = data['username']
    password = data['password']
    
    # Find user
    user = user_repo.get_by_username(username)
    
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Verify password
    if not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Check if user is active
    if not user.is_active:
        return jsonify({'error': 'User account is inactive'}), 403
    
    # Update last login
    user_repo.update_last_login(user.id)
    
    # Generate tokens
    access_token = generate_token(user.id, user.username, user.role)
    refresh_token = generate_refresh_token(user.id)
    
    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """
    User logout endpoint.
    
    Response:
        {
            "success": true,
            "message": "Logged out successfully"
        }
    """
    # In a more complex system, we would invalidate the token here
    # For now, client will just delete the token
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Refresh access token using refresh token.
    
    Request body:
        {
            "refresh_token": "string"
        }
        
    Response:
        {
            "success": true,
            "access_token": "string"
        }
    """
    data = request.get_json()
    
    if not data or not data.get('refresh_token'):
        return jsonify({'error': 'Refresh token required'}), 400
    
    refresh_token = data['refresh_token']
    
    # Verify refresh token
    payload = verify_token(refresh_token)
    
    if not payload or payload.get('type') != 'refresh':
        return jsonify({'error': 'Invalid refresh token'}), 401
    
    # Get user
    user = user_repo.get_by_id(payload['user_id'])
    
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    # Generate new access token
    access_token = generate_token(user.id, user.username, user.role)
    
    return jsonify({
        'success': True,
        'access_token': access_token
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """
    Get current user information.
    
    Response:
        {
            "success": true,
            "user": {...}
        }
    """
    return jsonify({
        'success': True,
        'user': current_user.to_dict()
    }), 200


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """
    Change user password.
    
    Request body:
        {
            "current_password": "string",
            "new_password": "string"
        }
        
    Response:
        {
            "success": true,
            "message": "Password changed successfully"
        }
    """
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Current and new password required'}), 400
    
    # Verify current password
    if not current_user.check_password(data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Validate new password
    if len(data['new_password']) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    
    # Set new password
    current_user.set_password(data['new_password'])
    
    # Update in database
    if user_repo.update(current_user):
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
    else:
        return jsonify({'error': 'Failed to update password'}), 500
