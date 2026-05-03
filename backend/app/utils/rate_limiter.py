from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class InMemoryRateLimiter:
    max_requests: int
    window_seconds: int
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _hits: Dict[str, Deque[float]] = field(default_factory=dict)

    async def check(self, key: str) -> bool:
        now = time.time()
        async with self._lock:
            q = self._hits.setdefault(key, deque())
            # Drop old hits
            while q and (now - q[0]) > self.window_seconds:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True

