"""Durable, task-local crawl checkpoints. Never stores model credentials."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import closing, contextmanager
from pathlib import Path


@contextmanager
def task_lock(path):
    if path is None:
        yield
        return
    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if lock_path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError("该任务正在另一个进程运行，请等待完成后再恢复") from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class TaskState:
    def __init__(self, path, metadata=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS entries "
                       "(kind TEXT, source TEXT, key TEXT, payload TEXT, PRIMARY KEY(kind, source, key))")
        if metadata is not None:
            previous = self.get("meta", "", "task")
            if previous and previous != metadata:
                raise ValueError("任务日期、站点或采集规则已改变，请新建任务；恢复任务只允许更改模型连接配置")
            self.put("meta", "", "task", metadata)

    def put(self, kind, source, key, payload):
        with self.lock, closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            db.execute("INSERT OR REPLACE INTO entries VALUES (?, ?, ?, ?)",
                       (kind, source, key, json.dumps(payload, ensure_ascii=False)))

    def get(self, kind, source, key):
        with self.lock, closing(sqlite3.connect(self.path, timeout=30)) as db:
            row = db.execute("SELECT payload FROM entries WHERE kind=? AND source=? AND key=?",
                             (kind, source, key)).fetchone()
        return json.loads(row[0]) if row else None

    def rows(self, kind, source=None):
        query = "SELECT source, key, payload FROM entries WHERE kind=?"
        args = [kind]
        if source is not None:
            query += " AND source=?"
            args.append(source)
        with self.lock, closing(sqlite3.connect(self.path, timeout=30)) as db:
            rows = db.execute(query + " ORDER BY rowid", args).fetchall()
        return [(name, key, json.loads(payload)) for name, key, payload in rows]

    def records(self, source=None):
        return [p["record"] for _, _, p in self.rows("candidate", source) if p.get("record")]

    def summary(self):
        meta = self.get("meta", "", "task") or {}
        names = [s["name"] for s in meta.get("sources", [])]
        names += [n for n, _, _ in self.rows("source") if n not in names]
        sources = []
        totals = dict(included=0, excluded=0, out_of_range=0, llm_failed=0, detail_failed=0, pending=0, skipped_attachment=0)
        labels = {"complete": "完成", "partial": "部分失败", "failed": "采集失败", "pending": "未完成"}
        for name in names:
            pages = [dict(url=k, **p) for _, k, p in self.rows("page", name)]
            candidates = [p for _, _, p in self.rows("candidate", name)]
            counts = {k: sum(p.get("status") == k for p in candidates) for k in totals}
            for key in totals:
                totals[key] += counts[key]
            failed = sum(p.get("status") in {"failed", "empty", "pending"} for p in pages)
            completed = sum(p.get("status") == "complete" for p in pages)
            source = self.get("source", name, "state") or {}
            if not source.get("finished"):
                status = "pending"
            elif failed or counts["llm_failed"] or counts["detail_failed"] or counts["pending"] or source.get("error"):
                status = "failed" if pages and not completed and failed == len(pages) else "partial"
            else:
                status = "complete"
            sources.append(dict(name=name, status=status, label=labels[status], pages=len(pages),
                                failed_pages=failed, counts=counts,
                                issues=[dict(url=p.get("item", {}).get("url", ""), title=p.get("item", {}).get("title", ""),
                                             status=p.get("status"), reason=p.get("reason", ""),
                                             column=p.get("column", ""), failure_kind=p.get("failure_kind", ""),
                                             http_status=p.get("http_status")) for p in candidates
                                        if p.get("status") in {"llm_failed", "detail_failed", "pending"}],
                                details=[{k: p.get(k, "") for k in ("url", "column", "status", "reason", "stop", "failure_kind", "http_status")} for p in pages]))
        return dict(sources=sources, counts=totals, start_date=meta.get("start_date", ""), end_date=meta.get("end_date", ""),
                    complete=sum(s["status"] == "complete" for s in sources),
                    partial=sum(s["status"] == "partial" for s in sources),
                    failed=sum(s["status"] == "failed" for s in sources),
                    pending=sum(s["status"] == "pending" for s in sources), total=len(sources))
