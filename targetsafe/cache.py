from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheProbe:
    payload: Any | None
    hit: bool
    stale: bool = False
    negative: bool = False
    age_seconds: float = 0.0


class SQLiteCache:
    def __init__(self, path: str | Path = "work/targetsafe_cache.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._runtime_stats = {
            "hits": 0,
            "misses": 0,
            "stale_hits": 0,
            "negative_hits": 0,
            "sets": 0,
            "negative_sets": 0,
        }
        self._init_db()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL DEFAULT '',
                    query TEXT NOT NULL DEFAULT '',
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_seconds INTEGER,
                    is_negative INTEGER NOT NULL DEFAULT 0,
                    last_accessed REAL,
                    hit_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._ensure_columns(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_namespace ON cache_entries(namespace)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created ON cache_entries(created_at)")
            conn.commit()

    @staticmethod
    def _ensure_columns(conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(cache_entries)").fetchall()}
        migrations = {
            "namespace": "ALTER TABLE cache_entries ADD COLUMN namespace TEXT NOT NULL DEFAULT ''",
            "query": "ALTER TABLE cache_entries ADD COLUMN query TEXT NOT NULL DEFAULT ''",
            "ttl_seconds": "ALTER TABLE cache_entries ADD COLUMN ttl_seconds INTEGER",
            "is_negative": "ALTER TABLE cache_entries ADD COLUMN is_negative INTEGER NOT NULL DEFAULT 0",
            "last_accessed": "ALTER TABLE cache_entries ADD COLUMN last_accessed REAL",
            "hit_count": "ALTER TABLE cache_entries ADD COLUMN hit_count INTEGER NOT NULL DEFAULT 0",
        }
        for column, statement in migrations.items():
            if column not in columns:
                conn.execute(statement)

    @staticmethod
    def make_key(namespace: str, query: Any) -> str:
        raw = json.dumps({"namespace": namespace, "query": query}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, namespace: str, query: Any, ttl_seconds: int | None = 86400) -> Any | None:
        probe = self.probe(namespace, query, ttl_seconds=ttl_seconds)
        if probe.hit and not probe.negative and not probe.stale:
            return probe.payload
        return None

    def get_stale(self, namespace: str, query: Any) -> Any | None:
        probe = self.probe(namespace, query, ttl_seconds=None, allow_stale=True)
        if probe.hit and not probe.negative:
            return probe.payload
        return None

    def get_negative(self, namespace: str, query: Any, ttl_seconds: int | None = 180) -> dict[str, Any] | None:
        probe = self.probe(namespace, query, ttl_seconds=ttl_seconds, allow_stale=False)
        if probe.hit and probe.negative:
            return probe.payload if isinstance(probe.payload, dict) else {"payload": probe.payload}
        return None

    def probe(
        self,
        namespace: str,
        query: Any,
        ttl_seconds: int | None = 86400,
        allow_stale: bool = False,
    ) -> CacheProbe:
        key = self.make_key(namespace, query)
        with closing(sqlite3.connect(self.path)) as conn:
            row = conn.execute(
                "SELECT payload, created_at, ttl_seconds, is_negative FROM cache_entries WHERE cache_key = ?",
                (key,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE cache_entries SET last_accessed = ?, hit_count = hit_count + 1 WHERE cache_key = ?",
                    (time.time(), key),
                )
                conn.commit()
        if not row:
            self._runtime_stats["misses"] += 1
            return CacheProbe(payload=None, hit=False)
        payload, created_at, stored_ttl, is_negative = row
        age = time.time() - float(created_at)
        effective_ttl = ttl_seconds if ttl_seconds is not None else stored_ttl
        stale = effective_ttl is not None and age > float(effective_ttl)
        negative = bool(is_negative)
        if stale and not allow_stale:
            self._runtime_stats["misses"] += 1
            return CacheProbe(payload=None, hit=False, stale=True, negative=negative, age_seconds=age)
        if stale:
            self._runtime_stats["stale_hits"] += 1
        elif negative:
            self._runtime_stats["negative_hits"] += 1
        else:
            self._runtime_stats["hits"] += 1
        return CacheProbe(payload=json.loads(payload), hit=True, stale=stale, negative=negative, age_seconds=age)

    def set(
        self,
        namespace: str,
        query: Any,
        payload: Any,
        ttl_seconds: int | None = None,
        negative: bool = False,
    ) -> None:
        key = self.make_key(namespace, query)
        query_text = json.dumps(query, sort_keys=True, default=str)
        encoded = json.dumps(payload, sort_keys=True, default=str)
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_entries
                (cache_key, namespace, query, payload, created_at, ttl_seconds, is_negative, last_accessed, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT hit_count FROM cache_entries WHERE cache_key = ?), 0))
                """,
                (key, namespace, query_text, encoded, time.time(), ttl_seconds, int(negative), time.time(), key),
            )
            conn.commit()
        self._runtime_stats["sets"] += 1
        if negative:
            self._runtime_stats["negative_sets"] += 1

    def stats(self) -> dict[str, Any]:
        now = time.time()
        with closing(sqlite3.connect(self.path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
            negative = conn.execute("SELECT COUNT(*) FROM cache_entries WHERE is_negative = 1").fetchone()[0]
            stale = conn.execute(
                """
                SELECT COUNT(*) FROM cache_entries
                WHERE ttl_seconds IS NOT NULL AND (? - created_at) > ttl_seconds
                """,
                (now,),
            ).fetchone()[0]
            namespace_rows = conn.execute(
                "SELECT namespace, COUNT(*), SUM(hit_count) FROM cache_entries GROUP BY namespace ORDER BY namespace"
            ).fetchall()
        return {
            "schema": "targetsafe.cache_stats.v1",
            "path": str(self.path),
            "entries": int(total),
            "negative_entries": int(negative),
            "stale_entries": int(stale),
            "runtime": dict(self._runtime_stats),
            "namespaces": {
                str(namespace or "unknown"): {"entries": int(count), "hit_count": int(hit_count or 0)}
                for namespace, count, hit_count in namespace_rows
            },
        }
