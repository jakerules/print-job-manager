"""
Database configuration and initialization for user management.
"""
import os
import sqlite3
from pathlib import Path

# Database path — honour DB_DIR env var so Docker can mount data separately
DB_DIR = Path(os.environ.get('DB_DIR', str(Path(__file__).parent)))
DB_PATH = DB_DIR / 'users.db'


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with all required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Notification preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            browser_notifications BOOLEAN DEFAULT TRUE,
            sound_alerts BOOLEAN DEFAULT TRUE,
            email_notifications BOOLEAN DEFAULT FALSE,
            dnd_enabled BOOLEAN DEFAULT FALSE,
            dnd_start VARCHAR(5) DEFAULT '22:00',
            dnd_end VARCHAR(5) DEFAULT '07:00',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Audit log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id VARCHAR(100),
            details TEXT,
            ip_address VARCHAR(45),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Jobs table — local job storage (replaces Google Sheets dependency)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id VARCHAR(8) UNIQUE NOT NULL,
            email VARCHAR(120) NOT NULL,
            room VARCHAR(50) NOT NULL,
            quantity INTEGER DEFAULT 1,
            paper_size VARCHAR(20) DEFAULT 'Letter',
            two_sided BOOLEAN DEFAULT FALSE,
            color BOOLEAN DEFAULT FALSE,
            stapled BOOLEAN DEFAULT FALSE,
            deadline VARCHAR(50),
            notes TEXT,
            staff_notes TEXT,
            file_url TEXT,
            acknowledged BOOLEAN DEFAULT FALSE,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Settings table — key-value app configuration (replaces config.ini)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL,
            category VARCHAR(50) DEFAULT 'general',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()

    # Migration: add DND columns if missing
    try:
        cursor.execute("SELECT dnd_enabled FROM notification_preferences LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE notification_preferences ADD COLUMN dnd_enabled BOOLEAN DEFAULT FALSE")
        cursor.execute("ALTER TABLE notification_preferences ADD COLUMN dnd_start VARCHAR(5) DEFAULT '22:00'")
        cursor.execute("ALTER TABLE notification_preferences ADD COLUMN dnd_end VARCHAR(5) DEFAULT '07:00'")
        conn.commit()

    # Seed default settings if the table is empty
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ('spreadsheet_id', '', 'google'),
            ('sheet_name', 'Sheet1', 'google'),
            ('adobe_reader_path', '', 'printing'),
            ('cover_sheet_printer', '', 'printing'),
            ('pdf_printer', '', 'printing'),
            ('receipt_printer', '', 'printing'),
            ('bypass_receipt_printer', 'false', 'printing'),
            ('bypass_pdf_printer', 'false', 'printing'),
            ('poll_interval', '10', 'script'),
            ('cleanup_after_processing', 'true', 'script'),
            ('cleanup_delay_minutes', '10', 'script'),
            ('enable_footer', 'true', 'footer'),
            ('footer_font_size', '6', 'footer'),
            ('footer_font_family', 'Times-Roman', 'footer'),
            ('websocket_notifications', 'true', 'notifications'),
            ('browser_push_notifications', 'true', 'notifications'),
            ('email_notifications', 'false', 'notifications'),
            ('sound_alerts', 'true', 'notifications'),
        ]
        cursor.executemany(
            "INSERT INTO settings (key, value, category) VALUES (?, ?, ?)",
            defaults,
        )
        conn.commit()

    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == '__main__':
    init_db()
