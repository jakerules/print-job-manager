"""
Settings repository for database operations.
"""
from datetime import datetime, timezone
from typing import Optional, Dict

from database.db_config import get_connection


class SettingsRepository:
    """Repository for application settings stored in the database."""

    def get(self, key: str) -> Optional[str]:
        """Get a single setting value by key."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row['value'] if row else None

    def get_by_category(self, category: str) -> Dict[str, str]:
        """Get all settings in a category as {key: value}."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT key, value FROM settings WHERE category = ? ORDER BY key',
            (category,),
        )
        rows = cursor.fetchall()
        conn.close()
        return {r['key']: r['value'] for r in rows}

    def get_all(self) -> Dict[str, Dict[str, str]]:
        """Get all settings grouped by category."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value, category FROM settings ORDER BY category, key')
        rows = cursor.fetchall()
        conn.close()

        result: Dict[str, Dict[str, str]] = {}
        for r in rows:
            cat = r['category']
            if cat not in result:
                result[cat] = {}
            result[cat][r['key']] = r['value']
        return result

    def set(self, key: str, value: str, category: str = 'general') -> bool:
        """Insert or update a single setting."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT INTO settings (key, value, category, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       value = excluded.value,
                       category = excluded.category,
                       updated_at = excluded.updated_at''',
                (key, value, category, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error setting {key}: {e}")
            return False
        finally:
            conn.close()

    def set_many(self, settings: dict, category: Optional[str] = None) -> bool:
        """Bulk upsert settings. If category is None, existing category is preserved."""
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        try:
            for key, value in settings.items():
                if category:
                    cursor.execute(
                        '''INSERT INTO settings (key, value, category, updated_at)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(key) DO UPDATE SET
                               value = excluded.value,
                               category = excluded.category,
                               updated_at = excluded.updated_at''',
                        (key, str(value), category, now),
                    )
                else:
                    cursor.execute(
                        '''UPDATE settings SET value = ?, updated_at = ? WHERE key = ?''',
                        (str(value), now, key),
                    )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error bulk-setting: {e}")
            return False
        finally:
            conn.close()
