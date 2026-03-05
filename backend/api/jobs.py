"""
Job management routes - handles job queue, status updates, and job operations.
Uses local SQLite database. Google Sheets is no longer required.
"""
from flask import Blueprint, request, jsonify
import secrets
import os

from api.auth_decorators import token_required, role_required
from api.job_repository import JobRepository

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')
job_repo = JobRepository()


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
    """
    try:
        status_filter = request.args.get('status')
        search_query = request.args.get('search')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        email_filter = None
        if current_user.role == 'submitter':
            email_filter = current_user.email

        jobs, total = job_repo.get_all(
            status_filter=status_filter,
            search=search_query,
            limit=limit,
            offset=offset,
            email_filter=email_filter,
        )

        return jsonify({
            'success': True,
            'jobs': jobs,
            'total': total,
            'limit': limit,
            'offset': offset,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch jobs: {str(e)}'}), 500


@jobs_bp.route('/<job_id>', methods=['GET'])
@token_required
def get_job(current_user, job_id):
    """Get job details by ID."""
    try:
        job = job_repo.get_by_id(job_id)
        if not job:
            return jsonify({'error': f'Job ID {job_id} not found'}), 404

        if current_user.role == 'submitter':
            if job.get('email', '').lower() != current_user.email.lower():
                return jsonify({'error': 'Unauthorized to view this job'}), 403

        return jsonify({'success': True, 'job': job}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch job: {str(e)}'}), 500


@jobs_bp.route('/<job_id>/status', methods=['PUT'])
@token_required
@role_required('staff')
def update_job_status(current_user, job_id):
    """
    Update job status.

    Request body:
        {"acknowledged": true/false, "completed": true/false}
    """
    try:
        data = request.get_json()

        job = job_repo.update_status(
            job_id,
            acknowledged=data.get('acknowledged'),
            completed=data.get('completed'),
        )
        if not job:
            return jsonify({'error': f'Job ID {job_id} not found'}), 404

        return jsonify({'success': True, 'job': job}), 200

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

        if not job_repo.update_notes(job_id, notes):
            return jsonify({'error': f'Job ID {job_id} not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Notes updated successfully',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to update notes: {str(e)}'}), 500


@jobs_bp.route('/stats', methods=['GET'])
@token_required
def get_job_stats(current_user):
    """Get job statistics."""
    try:
        stats = job_repo.get_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500


@jobs_bp.route('/submit', methods=['POST'])
@token_required
def submit_job(current_user):
    """
    Submit a new print job.

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
            "file_url": "https://..."
        }
    """
    try:
        data = request.get_json()

        required = ['email', 'room', 'quantity']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Generate unique Job ID
        job_id = generate_job_id()
        while job_repo.get_by_id(job_id):
            job_id = generate_job_id()

        job_data = {
            'job_id': job_id,
            'email': data.get('email', ''),
            'room': data.get('room', ''),
            'quantity': int(data.get('quantity', 1)),
            'paper_size': data.get('paper_size', 'Letter'),
            'two_sided': bool(data.get('two_sided')),
            'color': bool(data.get('color')),
            'stapled': bool(data.get('stapled')),
            'deadline': data.get('deadline', ''),
            'notes': data.get('notes', ''),
            'file_url': data.get('file_url', ''),
        }

        job = job_repo.create(job_data)
        if not job:
            return jsonify({'error': 'Failed to create job'}), 500

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Job {job_id} submitted successfully',
        }), 201

    except Exception as e:
        return jsonify({'error': f'Failed to submit job: {str(e)}'}), 500


@jobs_bp.route('/upload-file', methods=['POST'])
@token_required
def upload_file(current_user):
    """
    Upload a file for a print job.
    Returns a local file reference.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(file.filename)[1]
        safe_name = f"{secrets.token_hex(8)}{ext}"
        filepath = os.path.join(upload_dir, safe_name)
        file.save(filepath)

        return jsonify({
            'success': True,
            'file_url': f'/uploads/{safe_name}',
            'original_name': file.filename,
            'size': os.path.getsize(filepath),
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500
