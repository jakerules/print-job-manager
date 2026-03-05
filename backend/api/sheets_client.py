"""
Reusable Google Sheets client.

Reads all configuration (credentials, token, spreadsheet_id, sheet_name)
from the settings DB table — no filesystem files needed.

Supports a web-based OAuth flow so admins can authorize from the browser.
"""
import json
import logging
from typing import Optional, List, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from api.settings_repository import SettingsRepository

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Column layout matching the Google Form / Sheet structure
TIMESTAMP_COL = 0       # A
STAFF_NOTES_COL = 1     # B
EMAIL_COL = 2           # C
ROOM_COL = 9            # J
QUANTITY_COL = 1
TWO_SIDED_COL = 2
PAPER_SIZE_COL = 3
DATE_SUBMITTED_COL = 6
JOB_DEADLINE_COL = 7
USER_NOTES_COL = 11     # L
ACKNOWLEDGED_COL = 12   # M
COMPLETED_COL = 13      # N
JOB_ID_COL = 14         # O

DEFAULT_COLUMN_MAP = {
    'google_drive_link': 0,
    'quantity': 1,
    'two_sided': 2,
    'paper_size': 3,
    'staples': 4,
    'hole_punch': 5,
    'date_submitted': 6,
    'job_deadline': 7,
    'processed': 8,
    'acknowledged': 12,
    'completed': 13,
}

_sheets_service = None


# ── Credentials from DB ─────────────────────────────────────────────

def _get_credentials():
    """Load or refresh Google OAuth credentials from the DB settings table."""
    sr = SettingsRepository()
    token_json = sr.get('google_token_json')
    if not token_json:
        logger.info("No Google token stored — run OAuth flow from Settings UI")
        return None

    try:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    except Exception as e:
        logger.error(f"Invalid stored token: {e}")
        return None

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Persist refreshed token back to DB
                sr.set('google_token_json', creds.to_json(), category='google')
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return None
        else:
            logger.warning("Token invalid and cannot be refreshed — re-authorize from Settings")
            return None

    return creds


def _get_client_config() -> Optional[dict]:
    """Return the OAuth client config dict stored in DB (credentials.json content)."""
    sr = SettingsRepository()
    raw = sr.get('google_credentials_json')
    if not raw:
        return None
    try:
        data = json.loads(raw)
        # credentials.json wraps under "installed" or "web" key
        if 'installed' in data:
            return data
        if 'web' in data:
            return data
        # Bare client config — wrap it
        return {'installed': data}
    except (json.JSONDecodeError, TypeError):
        return None


def get_client_type() -> Optional[str]:
    """Return 'installed' or 'web' based on stored credentials, or None."""
    config = _get_client_config()
    if not config:
        return None
    if 'web' in config:
        return 'web'
    return 'installed'


def _coerce_to_web_config(client_config: dict, redirect_uri: str) -> dict:
    """Convert an 'installed' client config to 'web' format.

    Google OAuth client_id/client_secret work for both installed and web
    flows — only the wrapper key and redirect_uris differ. By re-wrapping
    as 'web' with our server callback, we can use the redirect flow even
    with Desktop-type credentials.
    """
    if 'web' in client_config:
        return client_config

    installed = client_config.get('installed', {})
    return {
        'web': {
            'client_id': installed['client_id'],
            'client_secret': installed['client_secret'],
            'auth_uri': installed.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
            'token_uri': installed.get('token_uri', 'https://oauth2.googleapis.com/token'),
            'redirect_uris': [redirect_uri],
        }
    }


def build_oauth_url(redirect_uri: str) -> Optional[tuple]:
    """Generate the Google OAuth authorization URL.

    Always uses the server-side redirect flow. For 'installed' (Desktop)
    credentials, we re-wrap them as 'web' type so the redirect to our
    callback URL is allowed by Google.

    Returns (auth_url, flow_type) or None.
    """
    client_config = _get_client_config()
    if not client_config:
        return None

    # Always use web-style redirect flow
    web_config = _coerce_to_web_config(client_config, redirect_uri)
    flow = Flow.from_client_config(web_config, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
    )
    return auth_url, 'redirect'


def exchange_code(code: str, redirect_uri: str) -> tuple:
    """Exchange an OAuth authorization code for tokens and store in DB.

    Returns (True, None) on success or (False, error_message) on failure.
    """
    client_config = _get_client_config()
    if not client_config:
        return False, 'No client credentials configured'

    web_config = _coerce_to_web_config(client_config, redirect_uri)

    try:
        flow = Flow.from_client_config(web_config, scopes=SCOPES, redirect_uri=redirect_uri)
        flow.fetch_token(code=code)
        creds = flow.credentials
        # Store token JSON in DB
        sr = SettingsRepository()
        sr.set('google_token_json', creds.to_json(), category='google')
        reset_service()  # force rebuild with new creds
        logger.info("Google OAuth token stored successfully")
        return True, None
    except Exception as e:
        logger.error(f"OAuth code exchange failed: {e}")
        logger.error(f"  redirect_uri used: {redirect_uri}")
        logger.error(f"  client type: {'web' if 'web' in client_config else 'installed'}")
        return False, str(e)


def is_connected() -> bool:
    """Check whether we have valid (or refreshable) Google credentials."""
    return _get_credentials() is not None


def disconnect():
    """Remove stored token (admin wants to re-authorize or disconnect)."""
    sr = SettingsRepository()
    sr.set('google_token_json', '', category='google')
    reset_service()

    return creds


def get_sheets_service():
    """Get or create the Google Sheets API service (cached)."""
    global _sheets_service
    if _sheets_service:
        return _sheets_service

    creds = _get_credentials()
    if not creds:
        return None

    try:
        _sheets_service = build('sheets', 'v4', credentials=creds)
        return _sheets_service
    except Exception as e:
        logger.error(f"Failed to build Sheets service: {e}")
        return None


def reset_service():
    """Force re-auth on next call (e.g. after credential changes)."""
    global _sheets_service
    _sheets_service = None


def _get_sheet_config() -> Tuple[Optional[str], Optional[str]]:
    """Read spreadsheet_id and sheet_name from settings DB."""
    sr = SettingsRepository()
    sid = sr.get('spreadsheet_id')
    sname = sr.get('sheet_name') or 'Sheet1'
    return sid, sname


def read_all_rows() -> Optional[List[list]]:
    """Read all rows from the configured Google Sheet.

    Returns list of rows (each row is a list of cell values), or None on error.
    First row is the header.
    """
    svc = get_sheets_service()
    if not svc:
        return None

    sid, sname = _get_sheet_config()
    if not sid:
        logger.warning("spreadsheet_id not configured — cannot read sheet")
        return None

    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=sid,
            range=f"{sname}!A:Z",
        ).execute()
        return result.get('values', [])
    except Exception as e:
        logger.error(f"Failed to read sheet: {e}")
        return None


def append_row(row: list) -> bool:
    """Append a single row to the sheet."""
    svc = get_sheets_service()
    if not svc:
        return False

    sid, sname = _get_sheet_config()
    if not sid:
        return False

    try:
        svc.spreadsheets().values().append(
            spreadsheetId=sid,
            range=f"{sname}!A:O",
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]},
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to append row: {e}")
        return False


def update_cell(row_index: int, col_index: int, value) -> bool:
    """Update a single cell by 0-based row and column index."""
    svc = get_sheets_service()
    if not svc:
        return False

    sid, sname = _get_sheet_config()
    if not sid:
        return False

    col_letter = chr(ord('A') + col_index)
    range_name = f"{sname}!{col_letter}{row_index + 1}"

    try:
        svc.spreadsheets().values().update(
            spreadsheetId=sid,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body={'values': [[value]]},
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update cell: {e}")
        return False


def update_status_checkbox(row_index: int, col_index: int, value: bool) -> bool:
    """Update a checkbox cell (boolean) via batchUpdate."""
    svc = get_sheets_service()
    if not svc:
        return False

    sid, sname = _get_sheet_config()
    if not sid:
        return False

    try:
        sheet_id = _get_sheet_id(svc, sid, sname)
        if sheet_id is None:
            return False

        body = {'requests': [{
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': row_index,
                    'endRowIndex': row_index + 1,
                    'startColumnIndex': col_index,
                    'endColumnIndex': col_index + 1,
                },
                'cell': {'userEnteredValue': {'boolValue': value}},
                'fields': 'userEnteredValue',
            }
        }]}
        svc.spreadsheets().batchUpdate(spreadsheetId=sid, body=body).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update checkbox: {e}")
        return False


def _get_sheet_id(svc, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
    """Get numeric sheet ID for a given sheet name."""
    try:
        meta = svc.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sheet in meta['sheets']:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        return None
    except Exception as e:
        logger.error(f"Error getting sheet ID: {e}")
        return None


def row_to_job_dict(row: list) -> dict:
    """Convert a Sheet row to a dict matching the local DB job schema.

    Uses the same column indices as web_app/app.py.
    """
    def safe(idx):
        return row[idx] if len(row) > idx else ''

    ack_val = safe(ACKNOWLEDGED_COL)
    comp_val = safe(COMPLETED_COL)

    def parse_bool(val):
        if isinstance(val, bool):
            return val
        return str(val).strip().upper() in ('TRUE', 'YES', '1', 'CHECKED', '✓')

    return {
        'job_id': safe(JOB_ID_COL),
        'email': safe(EMAIL_COL),
        'room': safe(ROOM_COL),
        'quantity': safe(DEFAULT_COLUMN_MAP['quantity']),
        'paper_size': safe(DEFAULT_COLUMN_MAP['paper_size']),
        'two_sided': safe(DEFAULT_COLUMN_MAP['two_sided']),
        'date_submitted': safe(DEFAULT_COLUMN_MAP['date_submitted']),
        'job_deadline': safe(DEFAULT_COLUMN_MAP['job_deadline']),
        'staff_notes': safe(STAFF_NOTES_COL),
        'user_notes': safe(USER_NOTES_COL),
        'acknowledged': parse_bool(ack_val),
        'completed': parse_bool(comp_val),
    }


def job_dict_to_row(job: dict) -> list:
    """Convert a local DB job dict to a Sheet row (list of cell values).

    Matches the Google Form column structure used by submit_job in jobs.py.
    """
    return [
        job.get('date_submitted', ''),            # A: Timestamp
        job.get('staff_notes', ''),                # B: Staff Notes
        job.get('email', ''),                      # C: Email
        '',                                        # D
        '',                                        # E
        '',                                        # F
        '',                                        # G
        '',                                        # H
        '',                                        # I
        job.get('room', ''),                       # J: Room (col 9)
        '',                                        # K
        job.get('user_notes', job.get('notes', '')),  # L: User Notes
        'TRUE' if job.get('acknowledged') else 'FALSE',  # M
        'TRUE' if job.get('completed') else 'FALSE',     # N
        job.get('job_id', ''),                     # O: Job ID
    ]
