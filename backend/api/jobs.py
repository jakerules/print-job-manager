"""
Job management routes - handles job queue, status updates, and job operations.
"""
from flask import Blueprint, request, jsonify
import sys
import os
import secrets
from datetime import datetime

# Import the existing Google Sheets integration
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web_app'))

from api.auth_decorators import token_required, role_required
from web_app.app import (
    get_sheets_service, find_job_by_id, get_job_status, 
    mark_job_status, extract_job_details, get_sheet_id,
    SPREADSHEET_ID, SHEET_NAME, COLUMN_MAP
)

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')


def generate_job_id():
    """Generate an 8-character hex Job ID."""
    return secrets.token_hex(4).upper()


@jobs_bp.route('', methods=['GET'])
@token_required
def list_jobs(current_user):
    """
    List jobs with filtering and pagination.
    
    Query params:
        status: Filter by status (pending, acknowledged, completed)
        search: Search by job ID, email, or room
        limit: Number of results (default: 50)
        offset: Offset for pagination (default: 0)
        
    Response:
        {
            "success": true,
            "jobs": [...],
            "total": int
        }
    """
    try:
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({'error': 'Google Sheets service unavailable'}), 500
        
        # Get all data
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:Z"
        ).execute()
        
        rows = result.get('values', [])
        
        # Filter based on query params
        status_filter = request.args.get('status')
        search_query = request.args.get('search', '').lower()
        
        jobs = []
        for idx, row in enumerate(rows):
            if idx == 0:  # Skip header
                continue
            
            if len(row) <= 14:  # Need at least job ID column
                continue
            
            job_details = extract_job_details(row)
            job_details['row_number'] = idx
            job_details['status'] = get_job_status(row)
            
            # Apply search filter
            if search_query:
                searchable = f"{job_details.get('job_id', '')} {job_details.get('email', '')} {job_details.get('room', '')}".lower()
                if search_query not in searchable:
                    continue
            
            # Apply status filter
            if status_filter:
                if status_filter == 'pending' and (job_details['status']['acknowledged'] or job_details['status']['completed']):
                    continue
                elif status_filter == 'acknowledged' and (not job_details['status']['acknowledged'] or job_details['status']['completed']):
                    continue
                elif status_filter == 'completed' and not job_details['status']['completed']:
                    continue
            
            # Check permissions - submitters can only see their own jobs
            if current_user.role == 'submitter':
                if job_details.get('email', '').lower() != current_user.email.lower():
                    continue
            
            jobs.append(job_details)
        
        # Pagination
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        total = len(jobs)
        jobs = jobs[offset:offset + limit]
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch jobs: {str(e)}'}), 500


@jobs_bp.route('/<job_id>', methods=['GET'])
@token_required
def get_job(current_user, job_id):
    """Get job details by ID."""
    try:
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({'error': 'Google Sheets service unavailable'}), 500
        
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        
        if row_index is None:
            return jsonify({'error': f'Job ID {job_id} not found'}), 404
        
        job_details = extract_job_details(row_data)
        job_details['status'] = get_job_status(row_data)
        job_details['row_number'] = row_index
        
        # Check permissions
        if current_user.role == 'submitter':
            if job_details.get('email', '').lower() != current_user.email.lower():
                return jsonify({'error': 'Unauthorized to view this job'}), 403
        
        return jsonify({
            'success': True,
            'job': job_details
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch job: {str(e)}'}), 500


@jobs_bp.route('/<job_id>/status', methods=['PUT'])
@token_required
@role_required('staff')
def update_job_status(current_user, job_id):
    """
    Update job status.
    
    Request body:
        {
            "acknowledged": true/false,
            "completed": true/false
        }
    """
    try:
        data = request.get_json()
        
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({'error': 'Google Sheets service unavailable'}), 500
        
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        
        if row_index is None:
            return jsonify({'error': f'Job ID {job_id} not found'}), 404
        
        sheet_id = get_sheet_id(sheets_service, SPREADSHEET_ID, SHEET_NAME)
        if sheet_id is None:
            return jsonify({'error': 'Could not find sheet'}), 500
        
        requests = []
        
        if 'acknowledged' in data:
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': row_index,
                        'endRowIndex': row_index + 1,
                        'startColumnIndex': COLUMN_MAP['acknowledged'],
                        'endColumnIndex': COLUMN_MAP['acknowledged'] + 1
                    },
                    'cell': {'userEnteredValue': {'boolValue': data['acknowledged']}},
                    'fields': 'userEnteredValue'
                }
            })
        
        if 'completed' in data:
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': row_index,
                        'endRowIndex': row_index + 1,
                        'startColumnIndex': COLUMN_MAP['completed'],
                        'endColumnIndex': COLUMN_MAP['completed'] + 1
                    },
                    'cell': {'userEnteredValue': {'boolValue': data['completed']}},
                    'fields': 'userEnteredValue'
                }
            })
        
        if requests:
            body = {'requests': requests}
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
        
        # Fetch updated job
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        job_details = extract_job_details(row_data)
        job_details['status'] = get_job_status(row_data)
        
        return jsonify({
            'success': True,
            'job': job_details
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to update status: {str(e)}'}), 500


@jobs_bp.route('/<job_id>/notes', methods=['PUT'])
@token_required
@role_required('staff')
def update_job_notes(current_user, job_id):
    """
    Update staff notes for a job.
    
    Request body:
        {"notes": "string"}
    """
    try:
        data = request.get_json()
        notes = data.get('notes', '')
        
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({'error': 'Google Sheets service unavailable'}), 500
        
        row_index, row_data = find_job_by_id(sheets_service, job_id)
        
        if row_index is None:
            return jsonify({'error': f'Job ID {job_id} not found'}), 404
        
        # Update staff notes (Column B, index 1)
        col_letter = 'B'
        range_name = f"{SHEET_NAME}!{col_letter}{row_index + 1}"
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body={'values': [[notes]]}
        ).execute()
        
        return jsonify({
            'success': True,
            'message': 'Notes updated successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to update notes: {str(e)}'}), 500


@jobs_bp.route('/stats', methods=['GET'])
@token_required
def get_job_stats(current_user):
    """
    Get job statistics.
    
    Response:
        {
            "total": int,
            "pending": int,
            "acknowledged": int,
            "completed": int
        }
    """
    try:
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({'error': 'Google Sheets service unavailable'}), 500
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:Z"
        ).execute()
        
        rows = result.get('values', [])
        
        stats = {
            'total': 0,
            'pending': 0,
            'acknowledged': 0,
            'completed': 0
        }
        
        for idx, row in enumerate(rows):
            if idx == 0:  # Skip header
                continue
            
            if len(row) <= 14:
                continue
            
            status = get_job_status(row)
            stats['total'] += 1
            
            if status['completed']:
                stats['completed'] += 1
            elif status['acknowledged']:
                stats['acknowledged'] += 1
            else:
                stats['pending'] += 1
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500


@jobs_bp.route('/submit', methods=['POST'])
@token_required
def submit_job(current_user):
    """
    Submit a new print job directly (bypasses Google Form).
    
    Request body:
        {
            "email": "user@example.com",
            "room": "301",
            "quantity": 25,
            "paper_size": "Letter",
            "two_sided": false,
            "color": false,
            "stapled": false,
            "deadline": "2024-01-15",
            "notes": "Special instructions",
            "file_url": "https://drive.google.com/..."
        }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['email', 'room', 'quantity']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        sheets_service = get_sheets_service()
        if not sheets_service:
            return jsonify({'error': 'Google Sheets service unavailable'}), 500
        
        # Generate unique Job ID
        job_id = generate_job_id()
        
        # Ensure uniqueness
        existing_row, _ = find_job_by_id(sheets_service, job_id)
        while existing_row is not None:
            job_id = generate_job_id()
            existing_row, _ = find_job_by_id(sheets_service, job_id)
        
        timestamp = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        
        # Build row matching Google Form column structure
        # Column order must match existing sheet format
        row = [
            timestamp,                                  # A: Timestamp
            '',                                         # B: Staff Notes
            data.get('email', ''),                      # C: Email
            data.get('room', ''),                       # D: Room
            str(data.get('quantity', 1)),                # E: Quantity
            data.get('paper_size', 'Letter'),            # F: Paper Size
            'Yes' if data.get('two_sided') else 'No',   # G: Two-Sided
            'Yes' if data.get('color') else 'No',       # H: Color
            'Yes' if data.get('stapled') else 'No',     # I: Stapled
            data.get('deadline', ''),                    # J: Deadline
            data.get('file_url', ''),                    # K: File URL
            data.get('notes', ''),                       # L: User Notes
            'FALSE',                                     # M: Acknowledged
            'FALSE',                                     # N: Completed
            job_id,                                      # O: Job ID
        ]
        
        # Append to Google Sheet
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:O",
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Job {job_id} submitted successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to submit job: {str(e)}'}), 500


@jobs_bp.route('/upload-file', methods=['POST'])
@token_required
def upload_file(current_user):
    """
    Upload a file for a print job.
    Returns a Google Drive URL or local file reference.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # For now, save locally. Google Drive upload can be added later
        # with proper OAuth2 credentials for Drive API
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate safe filename
        ext = os.path.splitext(file.filename)[1]
        safe_name = f"{secrets.token_hex(8)}{ext}"
        filepath = os.path.join(upload_dir, safe_name)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'file_url': f'/uploads/{safe_name}',
            'original_name': file.filename,
            'size': os.path.getsize(filepath)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500
