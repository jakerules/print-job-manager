"""
Bidirectional sync service between local SQLite jobs DB and Google Sheets.

- pull_from_sheets(): reads all Sheet rows, upserts into local jobs table
- push_to_sheets(): finds local-only jobs, appends/updates Sheet rows
- sync(): runs pull then push
- Background thread runs sync() periodically (controlled by poll_interval setting)
"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from database.db_config import get_connection
from api.settings_repository import SettingsRepository
from api import sheets_client

logger = logging.getLogger(__name__)

# Sync state (module-level, thread-safe via _lock)
_lock = threading.Lock()
_last_sync_time: Optional[str] = None
_last_sync_error: Optional[str] = None
_last_sync_jobs_pulled: int = 0
_last_sync_jobs_pushed: int = 0
_sync_enabled: bool = False
_sync_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def get_status() -> dict:
    """Return current sync status."""
    with _lock:
        return {
            'enabled': _sync_enabled,
            'last_sync_time': _last_sync_time,
            'last_sync_error': _last_sync_error,
            'last_sync_jobs_pulled': _last_sync_jobs_pulled,
            'last_sync_jobs_pushed': _last_sync_jobs_pushed,
            'sheets_configured': bool(SettingsRepository().get('spreadsheet_id')),
        }


def _update_status(error: Optional[str] = None, pulled: int = 0, pushed: int = 0):
    global _last_sync_time, _last_sync_error, _last_sync_jobs_pulled, _last_sync_jobs_pushed
    with _lock:
        _last_sync_time = datetime.now(timezone.utc).isoformat()
        _last_sync_error = error
        _last_sync_jobs_pulled = pulled
        _last_sync_jobs_pushed = pushed


def _normalize_date(date_str: str) -> str:
    """Normalize a date string to ISO format for consistent storage."""
    if not date_str:
        return ''
    if 'T' in date_str:
        return date_str
    for fmt in ('%m/%d/%Y %H:%M:%S', '%m/%d/%Y %I:%M:%S %p',
                '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S',
                '%m/%d/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str, fmt).isoformat()
        except ValueError:
            continue
    return date_str


# ── Pull: Sheets → Local DB ─────────────────────────────────────────

def pull_from_sheets() -> int:
    """Read all rows from Google Sheet and upsert into local jobs table.

    Returns the number of jobs upserted, or -1 on error.
    """
    rows = sheets_client.read_all_rows()
    if rows is None:
        raise RuntimeError("Failed to read from Google Sheet (check credentials & spreadsheet_id)")

    if len(rows) <= 1:
        return 0  # header only or empty

    conn = get_connection()
    cursor = conn.cursor()
    upserted = 0

    try:
        for row in rows[1:]:  # skip header
            job = sheets_client.row_to_job_dict(row)
            job_id = job.get('job_id', '').strip()
            if not job_id:
                continue  # rows without a job_id can't be synced

            # Check if job already exists locally
            cursor.execute('SELECT id, updated_at FROM jobs WHERE job_id = ?', (job_id,))
            existing = cursor.fetchone()

            if existing:
                # Update status & notes from Sheet (Sheet is source of truth for pull)
                cursor.execute('''
                    UPDATE jobs SET
                        acknowledged = ?,
                        completed = ?,
                        completed_at = COALESCE(?, completed_at),
                        staff_notes = ?,
                        updated_at = ?
                    WHERE job_id = ?
                ''', (
                    job['acknowledged'],
                    job['completed'],
                    job.get('completed_at') or None,
                    job['staff_notes'],
                    datetime.now(timezone.utc).isoformat(),
                    job_id,
                ))
            else:
                # Insert new job from Sheet
                def _parse_bool(val):
                    return 1 if str(val).strip().upper() in ('YES', 'TRUE', '1') else 0

                cursor.execute('''
                    INSERT INTO jobs (job_id, email, room, quantity, paper_size,
                        two_sided, stapled, hole_punch, file_url, deadline, notes, staff_notes,
                        acknowledged, completed, completed_at, created_at, updated_at,
                        sheets_row_pushed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    job_id,
                    job['email'],
                    job['room'],
                    job.get('quantity', 1),
                    job.get('paper_size', 'Letter'),
                    _parse_bool(job.get('two_sided', '')),
                    _parse_bool(job.get('staples', '')),
                    _parse_bool(job.get('hole_punch', '')),
                    job.get('drive_link', ''),
                    job.get('job_deadline', ''),
                    job.get('user_notes', ''),
                    job.get('staff_notes', ''),
                    job['acknowledged'],
                    job['completed'],
                    job.get('completed_at') or None,
                    _normalize_date(job.get('date_submitted', '')) or datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                ))
            upserted += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return upserted


# ── Push: Local DB → Sheets ─────────────────────────────────────────

def push_to_sheets() -> int:
    """Push local job changes to the Google Sheet.

    - For jobs that exist in the Sheet AND have sheets_status_dirty=1:
      update only columns M (acknowledged) and N (completed), then reset the flag.
    - For jobs that are local-only (not in Sheet): append a full row.

    Returns the number of jobs pushed/updated, or -1 on error.
    """
    rows = sheets_client.read_all_rows()
    if rows is None:
        raise RuntimeError("Failed to read from Google Sheet")

    # Build set of job_ids already in Sheet
    sheet_job_ids: dict[str, int] = {}  # job_id -> row_index (0-based)
    for idx, row in enumerate(rows):
        if len(row) > sheets_client.JOB_ID_COL:
            jid = row[sheets_client.JOB_ID_COL].strip()
            if jid:
                sheet_job_ids[jid] = idx

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM jobs')
        local_jobs = cursor.fetchall()

        pushed = 0
        cell_updates = []  # collect all updates for a single batch call
        dirty_job_ids = []  # track which jobs to reset
        new_rows = []       # collect rows to append in a single API call
        new_job_ids = []    # track which jobs were appended

        for job_row in local_jobs:
            job = dict(job_row)
            job_id = job['job_id']

            if job_id in sheet_job_ids:
                # Only push M/N if the status was changed via the web UI
                if job.get('sheets_status_dirty'):
                    row_idx = sheet_job_ids[job_id]
                    cell_updates.append((row_idx, sheets_client.ACKNOWLEDGED_COL,
                                         'TRUE' if job.get('acknowledged') else 'FALSE'))
                    cell_updates.append((row_idx, sheets_client.COMPLETED_COL,
                                         'TRUE' if job.get('completed') else 'FALSE'))
                    dirty_job_ids.append(job_id)
                    pushed += 1
            elif not job.get('sheets_row_pushed'):
                # Job is local-only and not yet pushed — collect for batch append
                sheet_row = sheets_client.job_dict_to_row({
                    'date_submitted': job.get('created_at', ''),
                    'staff_notes': job.get('staff_notes', ''),
                    'email': job.get('email', ''),
                    'file_url': job.get('file_url', ''),
                    'paper_size': job.get('paper_size', 'Letter'),
                    'two_sided': 'Yes' if job.get('two_sided') else 'No',
                    'hole_punch': 'Yes' if job.get('hole_punch') else 'No',
                    'stapled': 'Yes' if job.get('stapled') else 'No',
                    'quantity': job.get('quantity', 1),
                    'room': job.get('room', ''),
                    'deadline': job.get('deadline', ''),
                    'user_notes': job.get('notes', ''),
                    'acknowledged': bool(job.get('acknowledged')),
                    'completed': bool(job.get('completed')),
                    'job_id': job_id,
                })
                new_rows.append(sheet_row)
                new_job_ids.append(job_id)

        # Send all cell updates in a single batch API call
        if cell_updates:
            if not sheets_client.batch_update_cells(cell_updates):
                logger.warning("Batch update of existing Sheet rows failed")

        # Append all new rows in a single API call
        if new_rows:
            if sheets_client.append_rows(new_rows):
                pushed += len(new_rows)
                # Mark these jobs so we don't re-append them next cycle
                placeholders = ','.join('?' * len(new_job_ids))
                cursor.execute(
                    f"UPDATE jobs SET sheets_row_pushed = 1 WHERE job_id IN ({placeholders})",
                    new_job_ids,
                )
            else:
                logger.warning(f"Failed to append {len(new_rows)} new rows to Sheet")

        # Reset dirty flag for pushed jobs
        if dirty_job_ids:
            placeholders = ','.join('?' * len(dirty_job_ids))
            cursor.execute(
                f"UPDATE jobs SET sheets_status_dirty = 0 WHERE job_id IN ({placeholders})",
                dirty_job_ids,
            )

        conn.commit()
    finally:
        conn.close()

    return pushed


# ── Full sync ────────────────────────────────────────────────────────

def sync() -> dict:
    """Run a full bidirectional sync (pull then push).

    Returns a status dict.
    """
    errors = []
    pulled = 0
    pushed = 0

    try:
        pulled = pull_from_sheets()
    except Exception as e:
        logger.error(f"Pull failed: {e}")
        errors.append(f"Pull: {e}")

    try:
        pushed = push_to_sheets()
    except Exception as e:
        logger.error(f"Push failed: {e}")
        errors.append(f"Push: {e}")

    error_str = '; '.join(errors) if errors else None
    _update_status(error=error_str, pulled=pulled, pushed=pushed)

    return {
        'success': not errors,
        'pulled': pulled,
        'pushed': pushed,
        'error': error_str,
    }


# ── Background sync thread ──────────────────────────────────────────

def _background_loop():
    """Background thread that periodically calls sync()."""
    logger.info("Background sync thread started")
    while not _stop_event.is_set():
        try:
            interval = int(SettingsRepository().get('poll_interval') or '60')
            interval = max(interval, 10)  # minimum 10s
        except (ValueError, TypeError):
            interval = 60

        _stop_event.wait(interval)
        if _stop_event.is_set():
            break

        if not _sync_enabled:
            continue

        try:
            result = sync()
            logger.info(f"Background sync: pulled={result['pulled']}, pushed={result['pushed']}")
        except Exception as e:
            logger.error(f"Background sync error: {e}")

    logger.info("Background sync thread stopped")


def start_background_sync():
    """Enable and start the background sync thread."""
    global _sync_enabled, _sync_thread
    with _lock:
        _sync_enabled = True
        if _sync_thread is None or not _sync_thread.is_alive():
            _stop_event.clear()
            _sync_thread = threading.Thread(target=_background_loop, daemon=True, name='sheets-sync')
            _sync_thread.start()


def stop_background_sync():
    """Disable background sync (thread stays alive but idle)."""
    global _sync_enabled
    with _lock:
        _sync_enabled = False


def toggle_sync(enabled: bool):
    """Enable or disable background sync."""
    if enabled:
        start_background_sync()
    else:
        stop_background_sync()
