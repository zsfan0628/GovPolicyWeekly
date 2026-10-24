"""Successful article snapshots shared across date ranges; never caches network failures."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .parser import Article


class ArticleCache:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "articles.sqlite3"
        self.lock = threading.Lock()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("CREATE TABLE IF NOT EXISTS articles "
                               "(url TEXT PRIMARY KEY, fetched REAL NOT NULL, payload TEXT NOT NULL)")

    def get(self, key: str, *, now: float | None = None) -> Article | None:
        now = time.time() if now is None else now
        with self.lock, closing(sqlite3.connect(self.path)) as connection, connection:
            row = connection.execute("SELECT fetched, payload FROM articles WHERE url = ?", (key,)).fetchone()
        if not row or now - row[0] >= 7 * 86400 or now < row[0]:
            return None
        try:
            item = json.loads(row[1])
            published = datetime.fromisoformat(item["published"]) if item["published"] else None
            # Always re-fetch recent and undated documents, including corrections to recent articles.
            if published is None or now - published.timestamp() < 2 * 86400:
                return None
            return Article(item["title"], item["url"], published, item["text"], item["attachments"])
        except (KeyError, ValueError, TypeError):
            return None

    def put(self, key: str, article: Article, *, now: float | None = None) -> None:
        payload = json.dumps({"title": article.title, "url": article.url,
                              "published": article.publish_date.isoformat() if article.publish_date else None,
                              "text": article.text, "attachments": article.attachments}, ensure_ascii=False)
        with self.lock, closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("INSERT OR REPLACE INTO articles VALUES (?, ?, ?)",
                               (key, time.time() if now is None else now, payload))
