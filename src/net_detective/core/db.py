import sqlite3
from contextlib import contextmanager

from net_detective.core.config import settings


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                interval_sec INTEGER NOT NULL,
                timeout_sec INTEGER NOT NULL,
                enabled INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS probe_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                status_code INTEGER,
                response_time_ms REAL,
                dns_time_ms REAL,
                error TEXT,
                ts TEXT NOT NULL,
                FOREIGN KEY(target_id) REFERENCES targets(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                ts TEXT NOT NULL,
                FOREIGN KEY(target_id) REFERENCES targets(id)
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection():
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
