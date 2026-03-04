"""
Migration utilities and runner.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migrations():
    """Run all migration scripts in order."""
    migrations_dir = Path(__file__).parent
    migration_files = sorted([f for f in migrations_dir.glob('*.py') if f.stem.startswith('00')])
    
    print(f"Found {len(migration_files)} migration(s)")
    
    for migration_file in migration_files:
        print(f"\nRunning migration: {migration_file.name}")
        
        # Execute the migration script
        with open(migration_file) as f:
            code = f.read()
            exec(code)
    
    print("\n✓ All migrations completed")


if __name__ == '__main__':
    run_migrations()
