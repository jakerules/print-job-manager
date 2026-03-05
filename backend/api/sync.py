"""
Sync API routes — manual trigger, status, toggle, and OAuth flow for Google Sheets.
"""
import os
from flask import Blueprint, request, jsonify, redirect
from urllib.parse import urljoin

# Allow OAuth over HTTP in dev / behind TLS-terminating proxy
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

from api.auth_decorators import token_required, role_required
from api import sync_service
from api import sheets_client
from api.settings_repository import SettingsRepository

sync_bp = Blueprint('sync', __name__, url_prefix='/api/sync')


def _build_redirect_uri():
    """Build the OAuth callback URI from the current request.

    Priority: 1) Referer/Origin header (most reliable behind proxies)
              2) X-Forwarded-* headers
              3) request.scheme + request.host
    """
    # Try to derive base URL from the Referer (the frontend that made the call)
    referer = request.headers.get('Referer', '')
    if referer:
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return urljoin(base, '/api/sync/oauth/callback')

    proto = request.headers.get('X-Forwarded-Proto', request.scheme)
    host = request.headers.get('X-Forwarded-Host', request.host)
    base = f"{proto}://{host}"
    return urljoin(base, '/api/sync/oauth/callback')


@sync_bp.route('/status', methods=['GET'])
@token_required
@role_required('manager')
def sync_status(current_user):
    """Return current sync status + Google connection state."""
    status = sync_service.get_status()
    status['google_connected'] = sheets_client.is_connected()
    return jsonify({'success': True, **status}), 200


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


# ── OAuth web flow ───────────────────────────────────────────────────

@sync_bp.route('/oauth/start', methods=['POST'])
@token_required
@role_required('admin')
def oauth_start(current_user):
    """Generate a Google OAuth authorization URL.

    The frontend will open this URL in a new tab/popup.
    """
    redirect_uri = _build_redirect_uri()
    url = sheets_client.build_oauth_url(redirect_uri)
    if not url:
        return jsonify({
            'success': False,
            'error': 'Google credentials not configured. Paste your credentials.json content in settings first.',
        }), 400
    return jsonify({'success': True, 'auth_url': url}), 200


@sync_bp.route('/oauth/callback', methods=['GET'])
def oauth_callback():
    """Handle the OAuth redirect from Google.

    This is NOT behind auth — Google redirects the browser here directly.
    On success we redirect to the frontend settings page.
    """
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        return redirect(f'/app-settings?oauth_error={error}')

    if not code:
        return redirect('/app-settings?oauth_error=no_code')

    redirect_uri = _build_redirect_uri()
    if sheets_client.exchange_code(code, redirect_uri):
        return redirect('/app-settings?oauth_success=1')
    else:
        return redirect('/app-settings?oauth_error=exchange_failed')


@sync_bp.route('/oauth/disconnect', methods=['POST'])
@token_required
@role_required('admin')
def oauth_disconnect(current_user):
    """Remove stored Google OAuth token."""
    sheets_client.disconnect()
    return jsonify({'success': True, 'message': 'Google Sheets disconnected'}), 200
