from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class CircuitBreaker:
    failure_threshold: int
    reset_timeout_s: int
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _failures: int = 0
    _opened_at: float | None = None

    async def allow_request(self) -> bool:
        async with self._lock:
            if self._opened_at is None:
                return True
            # If the breaker is open, only allow after reset_timeout.
            if (time.time() - self._opened_at) >= self.reset_timeout_s:
                # Half-open: allow and reset failures.
                self._opened_at = None
                self._failures = 0
                return True
            return False

    async def record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._opened_at = None

    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_at = time.time()

