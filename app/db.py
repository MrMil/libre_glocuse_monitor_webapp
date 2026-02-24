from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "sugar.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            timestamp TEXT PRIMARY KEY,
            value     REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized at %s", DB_PATH)


def upsert_readings(rows: list[tuple[str, float]]) -> int:
    """Insert readings, ignoring duplicates. Returns number of new rows inserted."""
    if not rows:
        return 0
    conn = get_connection()
    cur = conn.executemany(
        "INSERT OR IGNORE INTO readings (timestamp, value) VALUES (?, ?)",
        rows,
    )
    inserted = cur.rowcount
    conn.commit()
    conn.close()
    return inserted


def get_all_readings() -> list[tuple[str, float]]:
    """Return all readings ordered newest-first."""
    conn = get_connection()
    rows: list[tuple[str, float]] = conn.execute(
        "SELECT timestamp, value FROM readings ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return rows
