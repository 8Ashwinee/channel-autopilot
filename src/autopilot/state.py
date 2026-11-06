"""The ledger: a SQLite file recording every post attempt. It is what stops a post going out twice,
what the daily caps count, and what the daily report is built from."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item TEXT NOT NULL,
  action TEXT NOT NULL,
  status TEXT NOT NULL,            -- ok | failed
  url TEXT,
  remote_id TEXT,
  error TEXT,
  day TEXT NOT NULL,               -- the platform's own day (see schedule.day_key)
  ts REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_ok_per_action ON posts(item, action) WHERE status = 'ok';
CREATE INDEX IF NOT EXISTS posts_day ON posts(day, action);
"""


@dataclass
class Post:
    item: str
    action: str
    status: str
    url: str | None
    remote_id: str | None
    error: str | None
    day: str
    ts: float


class Ledger:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)

    def done(self, item: str, action: str) -> bool:
        return self.db.execute("SELECT 1 FROM posts WHERE item=? AND action=? AND status='ok'", (item, action)).fetchone() is not None

    def failures(self, item: str, action: str) -> int:
        return self.db.execute("SELECT COUNT(*) FROM posts WHERE item=? AND action=? AND status='failed'", (item, action)).fetchone()[0]

    def count(self, action: str, day: str) -> int:
        return self.db.execute("SELECT COUNT(*) FROM posts WHERE action=? AND day=? AND status='ok'", (action, day)).fetchone()[0]

    def record_ok(self, item, action, day, url=None, remote_id=None):
        self.db.execute("INSERT INTO posts(item,action,status,url,remote_id,day,ts) VALUES (?,?,'ok',?,?,?,?)",
                        (item, action, url, remote_id, day, time.time()))
        self.db.commit()

    def record_failed(self, item, action, day, error):
        self.db.execute("INSERT INTO posts(item,action,status,error,day,ts) VALUES (?,?,'failed',?,?,?)",
                        (item, action, str(error)[:1000], day, time.time()))
        self.db.commit()

    def rows(self, day: str | None = None, status: str | None = None) -> list[Post]:
        q, a = "SELECT item,action,status,url,remote_id,error,day,ts FROM posts WHERE 1=1", []
        if day:
            q += " AND day=?"; a.append(day)
        if status:
            q += " AND status=?"; a.append(status)
        return [Post(*r) for r in self.db.execute(q + " ORDER BY ts", a)]
