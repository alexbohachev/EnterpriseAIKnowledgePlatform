"""Per-process fixed-window limiter for the MVP; NOT cluster-wide enforcement."""
from __future__ import annotations
import threading
import time
from fastapi import HTTPException

class InProcessRateLimiter:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._records = {}
        self._lock = threading.Lock()

    def check(self, action: str, principal: str, max_requests: int, period: int = 60):
        now = self._clock()
        key = (action, principal)
        with self._lock:
            # Remove stale keys so anonymous identities do not grow storage forever.
            if len(self._records) > 10000:
                self._records = {k:v for k,v in self._records.items() if now-v[0] < period}
            start, count = self._records.get(key, (now, 0))
            if now-start >= period:
                start, count = now, 0
            if count >= max_requests:
                retry = max(1, int(period-(now-start)+1))
                raise HTTPException(429, "Request rate limit exceeded", headers={"Retry-After": str(retry)})
            self._records[key] = (start, count+1)
