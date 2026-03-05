"""
Sync API routes — manual trigger, status, and toggle for Google Sheets sync.
"""
from flask import Blueprint, request, jsonify

from api.auth_decorators import token_required, role_required
from api import sync_service

sync_bp = Blueprint('sync', __name__, url_prefix='/api/sync')


@sync_bp.route('/status', methods=['GET'])
@token_required
@role_required('manager')
def sync_status(current_user):
    """Return current sync status."""
    return jsonify({'success': True, **sync_service.get_status()}), 200


@sync_bp.route('/trigger', methods=['POST'])
@token_required
@role_required('admin')
def sync_trigger(current_user):
    """Manually trigger a full bidirectional sync."""
    try:
        result = sync_service.sync()
        return jsonify(result), 200 if result['success'] else 207
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@sync_bp.route('/toggle', methods=['PUT'])
@token_required
@role_required('admin')
def sync_toggle(current_user):
    """Enable or disable background sync."""
    data = request.get_json() or {}
    enabled = data.get('enabled', False)
    sync_service.toggle_sync(bool(enabled))
    return jsonify({
        'success': True,
        'enabled': enabled,
        'message': f"Background sync {'enabled' if enabled else 'disabled'}",
    }), 200
