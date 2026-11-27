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
            if payload.get("date_budget_skipped"):
                row["date_budget_skipped"] = row.get("date_budget_skipped", 0) + 1
                return
            row["count"] += 1
            row["seconds"] += max(0.0, float(payload.get("seconds", 0)))
            row["errors"] += int(bool(payload.get("error")))
            row["cache_hits"] += int(bool(payload.get("cache_hit")))
            if payload.get("deferred"):
                row["deferred"] = row.get("deferred", 0) + 1
            if payload.get("date_review"):
                row["date_reviews"] = row.get("date_reviews",0)+1
                row["date_verified"] = row.get("date_verified",0)+int(bool(payload.get("date_verified")))

    def snapshot(self):
        with self.lock:
            return {kind: {**row, "seconds": round(row["seconds"], 3)} for kind, row in self.stages.items()}
