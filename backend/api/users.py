"""
User management routes (Admin only).
"""
from flask import Blueprint, request, jsonify
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import User
from api.user_repository import UserRepository
from api.auth_decorators import token_required, role_required

users_bp = Blueprint('users', __name__, url_prefix='/api/users')
user_repo = UserRepository()


@users_bp.route('', methods=['GET'])
@token_required
@role_required('manager')
def list_users(current_user):
    """
    List all users.
    
    Query params:
        include_inactive: Include inactive users (default: false)
        
    Response:
        {
            "success": true,
            "users": [...]
        }
    """
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
    users = user_repo.get_all(include_inactive=include_inactive)
    
    return jsonify({
        'success': True,
        'users': [user.to_dict() for user in users]
    }), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
@token_required
@role_required('manager')
def get_user(current_user, user_id):
    """
    Get user by ID.
    
    Response:
        {
            "success": true,
            "user": {...}
        }
    """
    user = user_repo.get_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 200


@users_bp.route('', methods=['POST'])
@token_required
@role_required('admin')
def create_user(current_user):
    """
    Create a new user (Admin only).
    
    Request body:
        {
            "username": "string",
            "email": "string",
            "password": "string",
            "role": "admin|manager|staff|submitter"
        }
        
    Response:
        {
            "success": true,
            "user": {...}
        }
    """
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'role']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate role
    valid_roles = ['admin', 'manager', 'staff', 'submitter']
    if data['role'] not in valid_roles:
        return jsonify({'error': 'Invalid role'}), 400
    
    # Check if username exists
    if user_repo.username_exists(data['username']):
        return jsonify({'error': 'Username already exists'}), 409
    
    # Check if email exists
    if user_repo.email_exists(data['email']):
        return jsonify({'error': 'Email already exists'}), 409
    
    # Validate password
    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Create user
    user = User(
        username=data['username'],
        email=data['email'],
        role=data['role'],
        is_active=data.get('is_active', True)
    )
    user.set_password(data['password'])
    
    created_user = user_repo.create(user)
    
    if created_user:
        return jsonify({
            'success': True,
            'user': created_user.to_dict()
        }), 201
    else:
        return jsonify({'error': 'Failed to create user'}), 500


@users_bp.route('/<int:user_id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_user(current_user, user_id):
    """
    Update user (Admin only).
    
    Request body:
        {
            "username": "string" (optional),
            "email": "string" (optional),
            "role": "string" (optional),
            "is_active": boolean (optional),
            "password": "string" (optional)
        }
        
    Response:
        {
            "success": true,
            "user": {...}
        }
    """
    user = user_repo.get_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update username if provided
    if 'username' in data and data['username'] != user.username:
        if user_repo.username_exists(data['username'], exclude_user_id=user_id):
            return jsonify({'error': 'Username already exists'}), 409
        user.username = data['username']
    
    # Update email if provided
    if 'email' in data and data['email'] != user.email:
        if user_repo.email_exists(data['email'], exclude_user_id=user_id):
            return jsonify({'error': 'Email already exists'}), 409
        user.email = data['email']
    
    # Update role if provided
    if 'role' in data:
        valid_roles = ['admin', 'manager', 'staff', 'submitter']
        if data['role'] not in valid_roles:
            return jsonify({'error': 'Invalid role'}), 400
        user.role = data['role']
    
    # Update is_active if provided
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    
    # Update password if provided
    if 'password' in data:
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        user.set_password(data['password'])
    
    # Save changes
    if user_repo.update(user):
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
    else:
        return jsonify({'error': 'Failed to update user'}), 500


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_user(current_user, user_id):
    """
    Delete user (Admin only). Soft delete by setting is_active to False.
    
    Response:
        {
            "success": true,
            "message": "User deleted successfully"
        }
    """
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    user = user_repo.get_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user_repo.delete(user_id):
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200
    else:
        return jsonify({'error': 'Failed to delete user'}), 500
