"""
Tiny in-process TTL cache.

No Redis/Celery exists in the deployment (docker-compose has only postgres,
service_a, service_b, nginx), so the lightest reasonable option for "don't
recompute an identical analysis" is an in-memory TTL+LRU map. It is process-local
(fine for the single-worker analysis service) and thread-safe, so re-submitting
the same dataset returns instantly instead of re-running the full engine.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    def __init__(self, maxsize: int = 32, ttl_seconds: int = 600):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            ts, value = item
            if time.time() - ts > self.ttl:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key not in self._store and len(self._store) >= self.maxsize:
                # Evict the oldest entry (LRU-by-insertion).
                oldest = min(self._store.items(), key=lambda kv: kv[1][0])[0]
                self._store.pop(oldest, None)
            self._store[key] = (time.time(), value)


# Shared cache for analysis responses, keyed by a hash of the input files +
# options. 10-minute TTL keeps memory bounded while covering quick re-views.
analysis_cache = TTLCache(maxsize=32, ttl_seconds=600)
