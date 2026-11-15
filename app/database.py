"""CivicPulse database helpers - plain SQLite, no ORM, easy to follow."""
import sqlite3
from contextlib import contextmanager

from app import config


@contextmanager
def get_db():
    """Open a SQLite connection that returns rows like dictionaries."""
    conn = sqlite3.connect(config.get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create the tables if they do not exist yet. Safe to run every start-up."""
    config.get_db_path().parent.mkdir(parents=True, exist_ok=True)
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                department TEXT NOT NULL,
                severity INTEGER NOT NULL DEFAULT 3,
                priority_score INTEGER NOT NULL DEFAULT 0,
                priority_tier TEXT NOT NULL DEFAULT 'Low',
                status TEXT NOT NULL DEFAULT 'Reported',
                citizen_name TEXT,
                citizen_phone TEXT,
                locality TEXT,
                lat REAL,
                lng REAL,
                photo_path TEXT,
                duplicate_of TEXT,
                duplicate_count INTEGER NOT NULL DEFAULT 0,
                assigned_to TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_code TEXT NOT NULL,
                status TEXT NOT NULL,
                note TEXT,
                changed_by TEXT,
                created_at TEXT NOT NULL
            );
            """
        )


def next_code(conn) -> str:
    """Next human-friendly complaint code, e.g. CP-0001, CP-0002..."""
    row = conn.execute("SELECT COALESCE(MAX(id), 0) AS m FROM reports").fetchone()
    return f"CP-{row['m'] + 1:04d}"


def row_to_dict(row) -> dict:
    return dict(row) if row is not None else None
