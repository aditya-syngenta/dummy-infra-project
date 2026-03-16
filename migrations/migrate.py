"""
Database migration management.
BUG: No migration version tracking
BUG: Migrations not idempotent
BUG: No down-migration support
"""

import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

# BUG: Hardcoded connection parameters
DB_PATH = os.environ.get("DB_PATH", "/tmp/app.db")


def run_migrations():
    """Run all pending migrations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Migration 1: Users table
    # BUG: No check if table already exists - will error on re-run
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)

    # Migration 2: Orders table
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            items TEXT,
            total REAL,
            status TEXT DEFAULT 'pending'
        )
    """)

    # BUG: Commit happens at end - if any migration fails, all roll back
    # but there's no way to resume from where it failed
    conn.commit()

    # Migration 3: Add column
    # BUG: ALTER TABLE doesn't check if column exists - fails on re-run
    cursor.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
    cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")

    conn.commit()
    conn.close()
    logger.info("Migrations complete")


def rollback_migration(version):
    """Roll back to a specific migration version."""
    # BUG: Not implemented - just logs a message
    logger.warning(f"Rollback to version {version} is not implemented!")
    pass


if __name__ == "__main__":
    run_migrations()
