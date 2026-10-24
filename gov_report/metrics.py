"""Thread-safe stage counters for the desktop and the saved run summary."""

from __future__ import annotations

import threading
from collections import defaultdict


class RunMetrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.stages = defaultdict(lambda: {"count": 0, "seconds": 0.0, "errors": 0, "cache_hits": 0})

    def record(self, payload):
        if payload.get("event") != "stage_finished":
            return
        with self.lock:
            row = self.stages[payload["kind"]]
            row["count"] += 1
            row["seconds"] += max(0.0, float(payload.get("seconds", 0)))
            row["errors"] += int(bool(payload.get("error")))
            row["cache_hits"] += int(bool(payload.get("cache_hit")))

    def snapshot(self):
        with self.lock:
            return {kind: {**row, "seconds": round(row["seconds"], 3)} for kind, row in self.stages.items()}
