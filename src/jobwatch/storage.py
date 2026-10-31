"""SQLite memory of jobs already seen, so each job is announced only once."""
import sqlite3
import time
from pathlib import Path
from typing import Iterable, List

from .models import Job


class SeenStore:
    def __init__(self, path: str = "data/seen.db"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS seen (uid TEXT PRIMARY KEY, company TEXT, title TEXT, url TEXT, first_seen REAL)")
        self.db.commit()

    def new_only(self, jobs: Iterable[Job]) -> List[Job]:
        return [j for j in jobs if self.db.execute("SELECT 1 FROM seen WHERE uid=?", (j.uid,)).fetchone() is None]

    def mark_seen(self, jobs: Iterable[Job]) -> None:
        now = time.time()
        self.db.executemany(
            "INSERT OR IGNORE INTO seen (uid, company, title, url, first_seen) VALUES (?,?,?,?,?)",
            [(j.uid, j.company, j.title, j.url, now) for j in jobs])
        self.db.commit()
