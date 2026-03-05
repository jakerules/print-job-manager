"""
Job repository for database operations.
"""
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from database.db_config import get_connection


class JobRepository:
    """Repository for job database operations."""

    def create(self, data: dict) -> Optional[dict]:
        """Create a new job. Returns the job as a dict."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO jobs (job_id, email, room, quantity, paper_size,
                    two_sided, color, stapled, deadline, notes, file_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['job_id'], data['email'], data['room'],
                data.get('quantity', 1), data.get('paper_size', 'Letter'),
                data.get('two_sided', False), data.get('color', False),
                data.get('stapled', False), data.get('deadline', ''),
                data.get('notes', ''), data.get('file_url', ''),
            ))
            conn.commit()
            return self.get_by_id(data['job_id'])
        except Exception as e:
            conn.rollback()
            print(f"Error creating job: {e}")
            return None
        finally:
            conn.close()

    def get_by_id(self, job_id: str) -> Optional[dict]:
        """Get a job by its 8-char hex ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def get_all(
        self,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        email_filter: Optional[str] = None,
    ) -> Tuple[List[dict], int]:
        """Return (jobs, total) with optional filtering & pagination."""
        conn = get_connection()
        cursor = conn.cursor()

        conditions: list[str] = []
        params: list = []

        if status_filter == 'pending':
            conditions.append('acknowledged = 0 AND completed = 0')
        elif status_filter == 'acknowledged':
            conditions.append('acknowledged = 1 AND completed = 0')
        elif status_filter == 'completed':
            conditions.append('completed = 1')

        if search:
            conditions.append('(job_id LIKE ? OR email LIKE ? OR room LIKE ?)')
            like = f'%{search}%'
            params.extend([like, like, like])

        if email_filter:
            conditions.append('LOWER(email) = LOWER(?)')
            params.append(email_filter)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ''

        # Total count
        cursor.execute(f'SELECT COUNT(*) FROM jobs{where}', params)
        total = cursor.fetchone()[0]

        # Paginated results
        cursor.execute(
            f'SELECT * FROM jobs{where} ORDER BY created_at DESC LIMIT ? OFFSET ?',
            params + [limit, offset],
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(r) for r in rows], total

    def update_status(self, job_id: str, acknowledged: Optional[bool] = None,
                      completed: Optional[bool] = None) -> Optional[dict]:
        """Update acknowledged / completed flags. Returns updated job."""
        conn = get_connection()
        cursor = conn.cursor()
        sets: list[str] = []
        params: list = []

        if acknowledged is not None:
            sets.append('acknowledged = ?')
            params.append(acknowledged)
        if completed is not None:
            sets.append('completed = ?')
            params.append(completed)

        if not sets:
            conn.close()
            return self.get_by_id(job_id)

        sets.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(job_id)

        try:
            cursor.execute(
                f"UPDATE jobs SET {', '.join(sets)} WHERE job_id = ?", params
            )
            conn.commit()
            return self.get_by_id(job_id)
        except Exception as e:
            conn.rollback()
            print(f"Error updating job status: {e}")
            return None
        finally:
            conn.close()

    def update_notes(self, job_id: str, notes: str) -> bool:
        """Update staff notes for a job."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE jobs SET staff_notes = ?, updated_at = ? WHERE job_id = ?",
                (notes, datetime.now(timezone.utc).isoformat(), job_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating notes: {e}")
            return False
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Return job counts by status."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM jobs')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM jobs WHERE acknowledged = 0 AND completed = 0')
        pending = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM jobs WHERE acknowledged = 1 AND completed = 0')
        acknowledged = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM jobs WHERE completed = 1')
        completed = cursor.fetchone()[0]
        conn.close()
        return {
            'total': total,
            'pending': pending,
            'acknowledged': acknowledged,
            'completed': completed,
        }

    def delete(self, job_id: str) -> bool:
        """Delete a job by ID."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM jobs WHERE job_id = ?', (job_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting job: {e}")
            return False
        finally:
            conn.close()

    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_dict(row) -> dict:
        """Convert a sqlite3.Row to the API-compatible dict."""
        return {
            'job_id': row['job_id'],
            'email': row['email'],
            'room': row['room'],
            'quantity': str(row['quantity']),
            'paper_size': row['paper_size'],
            'two_sided': 'Yes' if row['two_sided'] else 'No',
            'color': 'Yes' if row['color'] else 'No',
            'stapled': 'Yes' if row['stapled'] else 'No',
            'date_submitted': row['created_at'] or '',
            'job_deadline': row['deadline'] or '',
            'staff_notes': row['staff_notes'] or '',
            'user_notes': row['notes'] or '',
            'file_url': row['file_url'] or '',
            'status': {
                'acknowledged': bool(row['acknowledged']),
                'completed': bool(row['completed']),
            },
        }
