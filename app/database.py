"""SQLite database helpers for RedmondHR."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import DB_PATH, ensure_data_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date_of_birth TEXT,
    phone TEXT,
    address TEXT,
    drivers_license_number TEXT,
    drivers_license_expiry TEXT,
    health_card_number TEXT,
    health_card_expiry TEXT,
    company_start_date TEXT,
    date_of_hire TEXT,
    wage TEXT,
    notes TEXT,
    role TEXT,
    specialty TEXT DEFAULT 'none',
    millwright_level TEXT,
    training_stage TEXT,
    training_due_date TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
    notes TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dismissed_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL UNIQUE,
    employee_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    event_date TEXT NOT NULL,
    dismissed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS wage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    effective_date TEXT NOT NULL,
    event_type TEXT NOT NULL,
    amount TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(name);
CREATE INDEX IF NOT EXISTS idx_documents_employee ON documents(employee_id);
CREATE INDEX IF NOT EXISTS idx_dismissed_key ON dismissed_reminders(event_key);
CREATE INDEX IF NOT EXISTS idx_wage_history_employee ON wage_history(employee_id);
"""

# Columns added after the original schema — applied via migrate_schema().
# training_stage / training_due_date are left in place if present but unused.
_EMPLOYEE_COLUMN_MIGRATIONS = [
    ("phone", "TEXT"),
    ("role", "TEXT"),
    ("specialty", "TEXT DEFAULT 'none'"),
    ("millwright_level", "TEXT"),
]


_schema_ready = False


def get_connection() -> sqlite3.Connection:
    global _schema_ready
    ensure_data_dirs()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if not _schema_ready:
        conn.executescript(SCHEMA)
        migrate_schema(conn)
        conn.commit()
        _schema_ready = True
    return conn


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Add missing columns on existing DBs (ALTER TABLE ADD COLUMN IF NOT EXISTS style)."""
    existing = _existing_columns(conn, "employees")
    for col, col_type in _EMPLOYEE_COLUMN_MIGRATIONS:
        if col not in existing:
            conn.execute(f"ALTER TABLE employees ADD COLUMN {col} {col_type}")
    # Ensure specialty default for any NULL rows from older partial migrations
    conn.execute(
        "UPDATE employees SET specialty = 'none' WHERE specialty IS NULL OR specialty = ''"
    )


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    ensure_data_dirs()
    with db_session() as conn:
        conn.executescript(SCHEMA)
        migrate_schema(conn)


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]
