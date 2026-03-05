"""
Settings API routes — admin-managed application configuration.
"""
from flask import Blueprint, request, jsonify

from api.auth_decorators import token_required, role_required
from api.settings_repository import SettingsRepository

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')
settings_repo = SettingsRepository()


@settings_bp.route('', methods=['GET'])
@token_required
@role_required('manager')
def get_all_settings(current_user):
    """Return all settings grouped by category."""
    try:
        settings = settings_repo.get_all()
        return jsonify({'success': True, 'settings': settings}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch settings: {str(e)}'}), 500


@settings_bp.route('/<category>', methods=['GET'])
@token_required
@role_required('manager')
def get_category_settings(current_user, category):
    """Return settings for a single category."""
    try:
        settings = settings_repo.get_by_category(category)
        return jsonify({'success': True, 'settings': settings}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch settings: {str(e)}'}), 500


@settings_bp.route('', methods=['PUT'])
@token_required
@role_required('admin')
def update_settings(current_user):
    """
    Bulk update settings.

    Request body:
        {"settings": {"key1": "value1", "key2": "value2"}}
    """
    try:
        data = request.get_json()
        settings = data.get('settings', {})

        if not settings:
            return jsonify({'error': 'No settings provided'}), 400

        if not settings_repo.set_many(settings):
            return jsonify({'error': 'Failed to save settings'}), 500

        return jsonify({
            'success': True,
            'message': f'{len(settings)} setting(s) updated',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to update settings: {str(e)}'}), 500
