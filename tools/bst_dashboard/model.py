"""Thread-safe state model for the BuildStream dashboard."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class State:
    """Mutable build state with an immutable snapshot boundary."""

    def __init__(
        self,
        *,
        build_running: Callable[[], bool] | None = None,
        sysinfo: Callable[[], dict] | None = None,
    ):
        self._build_running = build_running or (lambda: False)
        self._sysinfo = sysinfo or (lambda: {})
        self._lock = threading.Lock()
        self.active: dict = {}
        self.completed: list = []
        self.failures: list = []
        self._summary_elements: set = set()
        self.pulled: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.cached_count: int = 0
        self.total_elements: int = 0
        self.recent_lines: list = []
        self.build_start_ts: float = 0.0
        self.build_end_ts: float = 0.0
        self.catching_up: bool = True
        self.version = 0

    def snapshot(self) -> dict:
        """Return a consistent view for API consumers."""
        with self._lock:
            live = bool(self.active) or self.catching_up
            if live:
                elapsed = (
                    int(time.time() - self.build_start_ts)
                    if self.build_start_ts
                    else 0
                )
            elif self.build_end_ts and self.build_start_ts:
                elapsed = int(self.build_end_ts - self.build_start_ts)
            else:
                elapsed = 0
            done = self.success_count + self.cached_count + self.pulled + self.failure_count
            return {
                "active": list(self.active.values()),
                "completed": self.completed[-60:],
                "failures": self.failures,
                "pulled": self.pulled,
                "success": self.success_count,
                "failure": self.failure_count,
                "cached": self.cached_count,
                "done": done,
                "total": self.total_elements,
                "recent": self.recent_lines[-80:],
                "elapsed": elapsed,
                "live": live,
                "catching_up": self.catching_up,
                "build_running": self._build_running(),
                "version": self.version,
                "sysinfo": dict(self._sysinfo()),
            }

    def update(self, fn) -> None:
        with self._lock:
            fn(self)
            self.version += 1
