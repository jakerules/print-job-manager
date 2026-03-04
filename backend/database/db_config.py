"""
Database configuration and initialization for user management.
"""
import os
import sqlite3
from pathlib import Path

# Database path
DB_DIR = Path(__file__).parent
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
    
    conn.commit()

    # Migration: add DND columns if missing
    try:
        cursor.execute("SELECT dnd_enabled FROM notification_preferences LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE notification_preferences ADD COLUMN dnd_enabled BOOLEAN DEFAULT FALSE")
        cursor.execute("ALTER TABLE notification_preferences ADD COLUMN dnd_start VARCHAR(5) DEFAULT '22:00'")
        cursor.execute("ALTER TABLE notification_preferences ADD COLUMN dnd_end VARCHAR(5) DEFAULT '07:00'")
        conn.commit()

    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == '__main__':
    init_db()
