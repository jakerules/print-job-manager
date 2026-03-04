"""
Barcode Job Tracking Web Application

This Flask web app provides a barcode scanning interface for tracking print job status.
Staff can scan barcodes printed on receipts to mark jobs as acknowledged or completed.

Supports both local network deployment and cloud hosting.
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import configparser

# Add parent directory to path to import from main project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for flexible deployment

# Load configuration
config = configparser.ConfigParser()
config_path = os.path.join(PROJECT_ROOT, 'config', 'config.ini')
if not os.path.exists(config_path):
    logger.error("config.ini not found")
    sys.exit(1)
config.read(config_path)

# Google Sheets configuration
SPREADSHEET_ID = config.get('Google', 'spreadsheet_id')
SHEET_NAME = config.get('Google', 'sheet_name')

# Column indices from config
COLUMN_MAP = {
    'google_drive_link': config.getint('Columns', 'google_drive_link'),
    'quantity': config.getint('Columns', 'quantity'),
    'two_sided': config.getint('Columns', 'two_sided'),
    'paper_size': config.getint('Columns', 'paper_size'),
    'staples': config.getint('Columns', 'staples'),
    'hole_punch': config.getint('Columns', 'hole_punch'),
    'date_submitted': config.getint('Columns', 'date_submitted'),
    'job_deadline': config.getint('Columns', 'job_deadline'),
    'processed': config.getint('Columns', 'processed'),
    'acknowledged': config.getint('Columns', 'acknowledged', fallback=12),
    'completed': config.getint('Columns', 'completed', fallback=13),
}

# Additional column indices (hardcoded per project convention)
JOB_ID_COLUMN = 14
STAFF_NOTES_COLUMN = 1  # Column B (index 1)
USER_NOTES_COLUMN = 11  # Column L (index 11)

# Google Sheets API scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Cached sheets service
_sheets_service = None


def get_sheets_service():
    """Get or create Google Sheets API service."""
    global _sheets_service
    
    if _sheets_service:
        return _sheets_service
    
    creds = None
    # Support both Docker paths (/app/credentials/) and local paths (/app/)
    credentials_dir = os.path.join(PROJECT_ROOT, 'credentials')
    if os.path.exists(credentials_dir):
        token_path = os.path.join(credentials_dir, 'token.json')
        credentials_path = os.path.join(credentials_dir, 'credentials.json')
        logger.info(f"Using credentials directory: {credentials_dir}")
    else:
        token_path = os.path.join(PROJECT_ROOT, 'token.json')
        credentials_path = os.path.join(PROJECT_ROOT, 'credentials.json')
        logger.info(f"Using PROJECT_ROOT for credentials: {PROJECT_ROOT}")
    
    # Load existing credentials
    if os.path.exists(token_path):
        logger.info(f"Loading token from: {token_path}")
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        logger.warning(f"Token file not found at: {token_path}")
    
    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            try:
                creds.refresh(Request())
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")
                return None
        else:
            if not os.path.exists(credentials_path):
                logger.error(f"credentials.json not found at: {credentials_path}")
                logger.error(f"PROJECT_ROOT={PROJECT_ROOT}")
                logger.error(f"Credentials dir exists: {os.path.exists(credentials_dir)}")
                logger.error(f"Files in {PROJECT_ROOT}: {os.listdir(PROJECT_ROOT) if os.path.exists(PROJECT_ROOT) else 'N/A'}")
                if os.path.exists(credentials_dir):
                    logger.error(f"Files in {credentials_dir}: {os.listdir(credentials_dir)}")
                return None
            logger.warning("Running OAuth flow - this requires manual authorization")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"Token saved to: {token_path}")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
    
    try:
        _sheets_service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets service created successfully")
        return _sheets_service
    except Exception as e:
        logger.error(f"Failed to build sheets service: {e}")
        return None


def get_sheet_id(sheets_service, spreadsheet_id, sheet_name):
    """Get the sheet ID for a given sheet name."""
    try:
        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        for sheet in spreadsheet['sheets']:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        return None
    except Exception as e:
        logger.error(f"Error getting sheet ID: {e}")
        return None


def find_job_by_id(sheets_service, job_id):
    """Find a job row by Job ID.
    
    Returns:
        tuple: (row_index, row_data) or (None, None) if not found
    """
    try:
        # Read all data from sheet
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:Z"
        ).execute()
        
        rows = result.get('values', [])
        
        # Search for job ID (column index 14)
        for idx, row in enumerate(rows):
            if len(row) > JOB_ID_COLUMN and row[JOB_ID_COLUMN] == job_id:
                return idx, row
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error finding job {job_id}: {e}")
        return None, None


def get_job_status(row_data):
    """Check acknowledged and completed status of a job."""
    status = {
        'acknowledged': False,
        'completed': False
    }
    
    try:
        ack_col = COLUMN_MAP['acknowledged']
        comp_col = COLUMN_MAP['completed']
        
        # Check acknowledged
        if len(row_data) > ack_col:
            val = row_data[ack_col]
            if isinstance(val, bool):
                status['acknowledged'] = val
            elif isinstance(val, str):
                status['acknowledged'] = val.strip().upper() in ['TRUE', 'YES', '1', 'CHECKED', '✓']
        
        # Check completed
        if len(row_data) > comp_col:
            val = row_data[comp_col]
            if isinstance(val, bool):
                status['completed'] = val
            elif isinstance(val, str):
                status['completed'] = val.strip().upper() in ['TRUE', 'YES', '1', 'CHECKED', '✓']
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
    
    return status


def mark_job_status(sheets_service, row_number, status_type):
    """Mark a job as acknowledged or completed.
    
    Args:
        row_number: 0-based row index
        status_type: 'acknowledged' or 'completed'
        
    Returns:
        bool: True if successful
    """
    try:
        sheet_id = get_sheet_id(sheets_service, SPREADSHEET_ID, SHEET_NAME)
        if sheet_id is None:
            return False
        
        col_index = COLUMN_MAP[status_type]
        
        # Update checkbox to TRUE
        requests = [{
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': row_number,
                    'endRowIndex': row_number + 1,
                    'startColumnIndex': col_index,
                    'endColumnIndex': col_index + 1
                },
                'cell': {
                    'userEnteredValue': {
                        'boolValue': True
                    }
                },
                'fields': 'userEnteredValue'
            }
        }]
        
        body = {'requests': requests}
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        
        logger.info(f"Marked job at row {row_number + 1} as {status_type}")
        return True
        
    except Exception as e:
        logger.error(f"Error marking job as {status_type}: {e}")
        return False


def extract_job_details(row_data):
    """Extract relevant job details from row data."""
    try:
        return {
            'job_id': row_data[JOB_ID_COLUMN] if len(row_data) > JOB_ID_COLUMN else '',
            'email': row_data[2] if len(row_data) > 2 else '',
            'room': row_data[9] if len(row_data) > 9 else '',
            'quantity': row_data[COLUMN_MAP['quantity']] if len(row_data) > COLUMN_MAP['quantity'] else '',
            'paper_size': row_data[COLUMN_MAP['paper_size']] if len(row_data) > COLUMN_MAP['paper_size'] else '',
            'two_sided': row_data[COLUMN_MAP['two_sided']] if len(row_data) > COLUMN_MAP['two_sided'] else '',
            'date_submitted': row_data[COLUMN_MAP['date_submitted']] if len(row_data) > COLUMN_MAP['date_submitted'] else '',
            'job_deadline': row_data[COLUMN_MAP['job_deadline']] if len(row_data) > COLUMN_MAP['job_deadline'] else '',
            'staff_notes': row_data[STAFF_NOTES_COLUMN] if len(row_data) > STAFF_NOTES_COLUMN else '',
            'user_notes': row_data[USER_NOTES_COLUMN] if len(row_data) > USER_NOTES_COLUMN else '',
        }
    except Exception as e:
        logger.error(f"Error extracting job details: {e}")
        return {}


# ===== ROUTES =====

@app.route('/')
def index():
    """Serve the main barcode scanning interface."""
    return render_template('index.html')


@app.route('/api/scan', methods=['POST'])
def scan_barcode():
    """Handle barcode scan - supports optional auto-update via device setting.
    
    Request body:
        {
            "job_id": "9E8B7BBF",
            "auto_update": true/false  (optional - for device-specific setting)
        }
        
    Response:
        {
            "success": true,
            "action": "acknowledged" | "completed" | null,
            "job": {...job details...}
        }
    """
    try:
        # Parse JSON with better error handling
        try:
            data = request.get_json()
        except Exception as json_error:
            logger.error(f"JSON parsing error: {json_error}")
            logger.error(f"Request data: {request.data}")
            logger.error(f"Content-Type: {request.content_type}")
            return jsonify({
                'success': False,
                'error': f'Invalid JSON in request: {str(json_error)}'
            }), 400
        
        job_id = data.get('job_id', '').strip() if data else ''
        auto_update = data.get('auto_update', False) if data else False
        
        if not job_id:
            return jsonify({
                'success': False,
                'error': 'Job ID is required'
            }), 400
        
        # Get sheets service
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({
                'success': False,
                'error': 'Google Sheets service unavailable'
            }), 500
        
        # Find job by ID
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        
        if row_index is None:
            return jsonify({
                'success': False,
                'error': f'Job ID {job_id} not found'
            }), 404
        
        # Get current status
        status = get_job_status(row_data)
        action = None
        
        # Only auto-update if enabled by device setting
        if auto_update:
            if not status['acknowledged']:
                if mark_job_status(sheets_service, row_index, 'acknowledged'):
                    action = 'acknowledged'
                    status['acknowledged'] = True
            elif not status['completed']:
                if mark_job_status(sheets_service, row_index, 'completed'):
                    action = 'completed'
                    status['completed'] = True
            else:
                action = 'already_completed'
        
        # Extract job details
        job_details = extract_job_details(row_data)
        job_details['status'] = status
        
        return jsonify({
            'success': True,
            'action': action,
            'job': job_details
        })
        
    except Exception as e:
        logger.error(f"Error in /api/scan: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/job/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job details by Job ID.
    
    Response:
        {
            "success": true,
            "job": {...job details...}
        }
    """
    try:
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({
                'success': False,
                'error': 'Google Sheets service unavailable'
            }), 500
        
        # Find job
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        
        if row_index is None:
            return jsonify({
                'success': False,
                'error': f'Job ID {job_id} not found'
            }), 404
        
        # Extract details
        job_details = extract_job_details(row_data)
        job_details['status'] = get_job_status(row_data)
        
        return jsonify({
            'success': True,
            'job': job_details
        })
        
    except Exception as e:
        logger.error(f"Error in /api/job/{job_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/update_status', methods=['POST'])
def update_status():
    """Manually update job status checkboxes.
    
    Request body:
        {
            "job_id": "9E8B7BBF",
            "acknowledged": true/false,
            "completed": true/false
        }
        
    Response:
        {
            "success": true,
            "job": {...updated job details...}
        }
    """
    try:
        data = request.get_json()
        job_id = data.get('job_id', '').strip()
        
        if not job_id:
            return jsonify({
                'success': False,
                'error': 'Job ID is required'
            }), 400
        
        # Get sheets service
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({
                'success': False,
                'error': 'Google Sheets service unavailable'
            }), 500
        
        # Find job by ID
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        
        if row_index is None:
            return jsonify({
                'success': False,
                'error': f'Job ID {job_id} not found'
            }), 404
        
        # Get sheet ID
        sheet_id = get_sheet_id(sheets_service, SPREADSHEET_ID, SHEET_NAME)
        if sheet_id is None:
            return jsonify({
                'success': False,
                'error': 'Could not find sheet'
            }), 500
        
        # Prepare batch update requests
        requests = []
        
        # Update acknowledged checkbox if provided
        if 'acknowledged' in data:
            ack_value = data['acknowledged']
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': row_index,
                        'endRowIndex': row_index + 1,
                        'startColumnIndex': COLUMN_MAP['acknowledged'],
                        'endColumnIndex': COLUMN_MAP['acknowledged'] + 1
                    },
                    'cell': {
                        'userEnteredValue': {
                            'boolValue': ack_value
                        }
                    },
                    'fields': 'userEnteredValue'
                }
            })
        
        # Update completed checkbox if provided
        if 'completed' in data:
            comp_value = data['completed']
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': row_index,
                        'endRowIndex': row_index + 1,
                        'startColumnIndex': COLUMN_MAP['completed'],
                        'endColumnIndex': COLUMN_MAP['completed'] + 1
                    },
                    'cell': {
                        'userEnteredValue': {
                            'boolValue': comp_value
                        }
                    },
                    'fields': 'userEnteredValue'
                }
            })
        
        # Execute batch update
        if requests:
            body = {'requests': requests}
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
            logger.info(f"Updated status for job {job_id} at row {row_index + 1}")
        
        # Fetch updated job details
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        job_details = extract_job_details(row_data)
        job_details['status'] = get_job_status(row_data)
        
        return jsonify({
            'success': True,
            'job': job_details
        })
        
    except Exception as e:
        logger.error(f"Error in /api/update_status: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/update_notes', methods=['POST'])
def update_notes():
    """Update staff notes (Column B).
    
    Request body:
        {
            "job_id": "9E8B7BBF",
            "notes": "Staff notes text"
        }
        
    Response:
        {
            "success": true,
            "job": {...updated job details...}
        }
    """
    try:
        data = request.get_json()
        job_id = data.get('job_id', '').strip()
        notes = data.get('notes', '')
        
        if not job_id:
            return jsonify({
                'success': False,
                'error': 'Job ID is required'
            }), 400
        
        # Get sheets service
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({
                'success': False,
                'error': 'Google Sheets service unavailable'
            }), 500
        
        # Find job by ID
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        
        if row_index is None:
            return jsonify({
                'success': False,
                'error': f'Job ID {job_id} not found'
            }), 404
        
        # Update staff notes (Column B)
        col_letter = chr(ord('A') + STAFF_NOTES_COLUMN)
        range_name = f"{SHEET_NAME}!{col_letter}{row_index + 1}"
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body={'values': [[notes]]}
        ).execute()
        
        logger.info(f"Updated staff notes for job {job_id} at row {row_index + 1}")
        
        # Fetch updated job details
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        job_details = extract_job_details(row_data)
        job_details['status'] = get_job_status(row_data)
        
        return jsonify({
            'success': True,
            'job': job_details
        })
        
    except Exception as e:
        logger.error(f"Error in /api/update_notes: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'barcode-job-tracking'
    })


@app.route('/api/search-job-ids', methods=['GET'])
def search_job_ids():
    """Search for job IDs matching a query prefix.
    
    Query parameter: q (search query)
    Returns: List of matching job IDs (max 10)
    """
    try:
        query = request.args.get('q', '').strip().upper()
        
        if not query:
            return jsonify({'success': True, 'job_ids': []})
        
        if len(query) < 2:
            return jsonify({'success': True, 'job_ids': []})
        
        # Get Google Sheets service
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({'success': False, 'error': 'Google Sheets connection failed'}), 500
        
        # Fetch all rows from the sheet
        range_name = f"{SHEET_NAME}!A:Z"
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        rows = result.get('values', [])
        
        # Extract unique job IDs that match the query prefix
        matching_job_ids = set()
        for row in rows:
            if len(row) > JOB_ID_COLUMN:
                job_id = str(row[JOB_ID_COLUMN]).strip().upper()
                # Match job IDs that start with the query
                if job_id and job_id.startswith(query):
                    matching_job_ids.add(job_id)
        
        # Sort and limit to 10 results
        sorted_ids = sorted(list(matching_job_ids))[:10]
        
        return jsonify({
            'success': True,
            'job_ids': sorted_ids
        })
        
    except Exception as e:
        logger.error(f"Error searching job IDs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/version', methods=['GET'])
def version_info():
    """Version endpoint showing deployed version and git commit."""
    version_data = {
        'version': os.getenv('APP_VERSION', '1.0.0'),
        'git_commit': os.getenv('GIT_COMMIT', 'unknown'),
        'git_branch': os.getenv('GIT_BRANCH', 'unknown'),
        'build_time': os.getenv('BUILD_TIME', 'unknown'),
        'environment': os.getenv('FLASK_ENV', 'production'),
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(version_data), 200


if __name__ == '__main__':
    # Check deployment mode from environment
    deployment_mode = os.getenv('DEPLOYMENT_MODE', 'local')
    
    if deployment_mode == 'cloud':
        # Cloud deployment (use gunicorn in production)
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
    else:
        # Local network deployment
        logger.info("Starting barcode tracking web app in LOCAL mode")
        logger.info("Access from local network at: http://<your-ip>:5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
