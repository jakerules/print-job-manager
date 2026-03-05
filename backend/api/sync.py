"""
Sync API routes — manual trigger, status, toggle, and OAuth flow for Google Sheets.
"""
import os
from flask import Blueprint, request, jsonify, redirect, session
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
    status['oauth_callback_url'] = _build_redirect_uri()
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
    """Generate a Google OAuth authorization URL."""
    redirect_uri = _build_redirect_uri()
    result = sheets_client.build_oauth_url(redirect_uri)
    if not result:
        return jsonify({
            'success': False,
            'error': 'Google credentials not configured. Paste your credentials.json content in settings first.',
        }), 400
    auth_url, flow_type = result

    # Persist the exact redirect_uri so /oauth/callback uses the same one
    sr = SettingsRepository()
    sr.set('_oauth_redirect_uri', redirect_uri, category='google')

    return jsonify({'success': True, 'auth_url': auth_url, 'flow_type': flow_type}), 200


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

    # Reuse the EXACT redirect_uri from /oauth/start to avoid mismatch
    sr = SettingsRepository()
    redirect_uri = sr.get('_oauth_redirect_uri') or _build_redirect_uri()

    success, error_msg = sheets_client.exchange_code(code, redirect_uri)
    if success:
        return redirect('/app-settings?oauth_success=1')
    else:
        from urllib.parse import quote
        return redirect(f'/app-settings?oauth_error={quote(error_msg or "exchange_failed")}')


@sync_bp.route('/oauth/exchange', methods=['POST'])
@token_required
@role_required('admin')
def oauth_exchange(current_user):
    """Manually exchange an authorization code (for Desktop/installed clients).

    The user copies the code from Google's auth page and submits it here.
    """
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    if not code:
        return jsonify({'success': False, 'error': 'No authorization code provided'}), 400

    sr = SettingsRepository()
    redirect_uri = sr.get('_oauth_redirect_uri') or _build_redirect_uri()
    success, error_msg = sheets_client.exchange_code(code, redirect_uri)
    if success:
        return jsonify({'success': True, 'message': 'Google Sheets connected successfully'}), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to exchange code — it may have expired. Try again.'}), 400


@sync_bp.route('/oauth/disconnect', methods=['POST'])
@token_required
@role_required('admin')
def oauth_disconnect(current_user):
    """Remove stored Google OAuth token."""
    sheets_client.disconnect()
    return jsonify({'success': True, 'message': 'Google Sheets disconnected'}), 200
