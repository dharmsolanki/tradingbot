import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional


class DatabaseManager:
    """
    Simple SQLite database manager.

    Thread-safe: the underlying sqlite3 connection is shared (via
    check_same_thread=False) between the async live loop and FastAPI's
    threadpool-executed endpoints. sqlite3 connections are not safe for
    truly concurrent access even with that flag, so all operations are
    serialized with a lock.
    """

    def __init__(self, db_path: str = "database/trading.db"):

        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )

        self.connection.row_factory = sqlite3.Row

        self._lock = threading.Lock()

    def execute(
        self,
        query: str,
        params: tuple = (),
    ) -> sqlite3.Cursor:

        with self._lock:
            cursor = self.connection.cursor()

            try:
                cursor.execute(query, params)
                self.connection.commit()
            except sqlite3.Error:
                self.connection.rollback()
                raise

            return cursor

    def executemany(
        self,
        query: str,
        params: list[tuple],
    ):

        with self._lock:
            cursor = self.connection.cursor()

            try:
                cursor.executemany(query, params)
                self.connection.commit()
            except sqlite3.Error:
                self.connection.rollback()
                raise

            return cursor

    def fetchone(
        self,
        query: str,
        params: tuple = (),
    ) -> Optional[dict]:

        with self._lock:
            cursor = self.connection.cursor()

            cursor.execute(query, params)

            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)

    def fetchall(
        self,
        query: str,
        params: tuple = (),
    ) -> list[dict]:

        with self._lock:
            cursor = self.connection.cursor()

            cursor.execute(query, params)

            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def close(self):

        if self.connection:

            self.connection.close()
