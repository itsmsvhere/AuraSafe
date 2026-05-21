"""
AuraSafe — logger.py
SQLite-backed persistent logging system. Thread-safe with connection-per-thread.
"""

import sqlite3
import threading
import time
import os
from datetime import datetime


class AuraLogger:
    """
    Thread-safe logger using SQLite.
    Each thread gets its own connection via threading.local().
    """

    EVENT_DETECTION   = "DETECTION"
    EVENT_BLOCK       = "BLOCK"
    EVENT_UNBLOCK     = "UNBLOCK"
    EVENT_LOCK        = "FOCUS_LOCK"
    EVENT_UNLOCK      = "FOCUS_UNLOCK"
    EVENT_APP_BLOCK   = "APP_BLOCKED"
    EVENT_SYSTEM      = "SYSTEM"

    def __init__(self, config: dict):
        log_cfg = config.get("logging", {})
        self.db_path   = log_cfg.get("db_path", "aurasafe_logs.db")
        self.max_entries = log_cfg.get("max_entries", 10000)
        self._local    = threading.local()
        self._init_lock = threading.Lock()
        self._ensure_table()

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _conn(self) -> sqlite3.Connection:
        """Get or create a per-thread SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _ensure_table(self):
        with self._init_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    event_type  TEXT    NOT NULL,
                    content     TEXT,
                    action      TEXT,
                    source      TEXT,
                    extra       TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON events(event_type)")
            conn.commit()
            conn.close()

    def _prune(self):
        """Keep table under max_entries limit."""
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if count > self.max_entries:
            excess = count - self.max_entries
            conn.execute(
                "DELETE FROM events WHERE id IN (SELECT id FROM events ORDER BY id ASC LIMIT ?)",
                (excess,)
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def log(self, event_type: str, content: str = "", action: str = "",
            source: str = "system", extra: str = ""):
        """Insert a log entry. Non-blocking, swallows errors gracefully."""
        try:
            ts = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
            conn = self._conn()
            conn.execute(
                "INSERT INTO events (timestamp, event_type, content, action, source, extra) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, event_type, content, action, source, extra)
            )
            conn.commit()
            self._prune()
        except Exception as e:
            # Logger must never crash the app
            print(f"[AuraLogger] Warning: could not write log — {e}")

    def get_recent(self, limit: int = 50, event_type: str = None) -> list[dict]:
        """Fetch recent log entries as list of dicts."""
        try:
            conn = self._conn()
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM events WHERE event_type=? ORDER BY id DESC LIMIT ?",
                    (event_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[AuraLogger] Warning: could not read logs — {e}")
            return []

    def get_stats(self) -> dict:
        """Return aggregate counts per event type."""
        try:
            conn = self._conn()
            rows = conn.execute(
                "SELECT event_type, COUNT(*) as cnt FROM events GROUP BY event_type"
            ).fetchall()
            return {r["event_type"]: r["cnt"] for r in rows}
        except Exception:
            return {}

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
