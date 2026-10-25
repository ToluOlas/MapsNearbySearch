"""Small SQLite-backed cache for slow third-party lookups."""

import json
import sqlite3
import time
from contextlib import contextmanager


class Cache:
    def __init__(self, path):
        self.path = path
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at REAL NOT NULL)"
            )

    @contextmanager
    def _connect(self):
        # A fresh connection per call keeps this safe across Flask's request threads
        conn = sqlite3.connect(self.path)
        try:
            with conn:  # commits on success, rolls back on error
                yield conn
        finally:
            conn.close()

    def get(self, key, max_age_seconds):
        """Return the cached value for key, or None if missing or older than max_age_seconds."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM cache WHERE key = ? AND created_at >= ?",
                (key, time.time() - max_age_seconds),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def find(self, prefix, max_age_seconds):
        """Return all fresh cached values whose key starts with prefix."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT value FROM cache WHERE substr(key, 1, ?) = ? AND created_at >= ?",
                (len(prefix), prefix, time.time() - max_age_seconds),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def put(self, key, value):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time()),
            )

    def prune(self, max_age_seconds):
        """Delete entries older than max_age_seconds."""
        with self._connect() as conn:
            conn.execute("DELETE FROM cache WHERE created_at < ?", (time.time() - max_age_seconds,))
