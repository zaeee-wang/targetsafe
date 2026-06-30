from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class SQLiteCache:
    def __init__(self, path: str | Path = "work/targetsafe_cache.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def make_key(namespace: str, query: Any) -> str:
        raw = json.dumps({"namespace": namespace, "query": query}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, namespace: str, query: Any, ttl_seconds: int | None = 86400) -> Any | None:
        key = self.make_key(namespace, query)
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT payload, created_at FROM cache_entries WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if not row:
            return None
        payload, created_at = row
        if ttl_seconds is not None and time.time() - created_at > ttl_seconds:
            return None
        return json.loads(payload)

    def set(self, namespace: str, query: Any, payload: Any) -> None:
        key = self.make_key(namespace, query)
        encoded = json.dumps(payload, sort_keys=True, default=str)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_entries (cache_key, payload, created_at)
                VALUES (?, ?, ?)
                """,
                (key, encoded, time.time()),
            )
            conn.commit()

