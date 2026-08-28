from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'todo',
    estimate_hours INTEGER,
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS idempotency_keys (
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    PRIMARY KEY (user_id, project_id, key)
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    task_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.executescript(SCHEMA)
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO users(id, name, token) VALUES (?, ?, ?)",
                [(1, "Alice", "token-alice"), (2, "Bob", "token-bob")],
            )
            connection.executemany(
                "INSERT INTO projects(id, owner_id, name) VALUES (?, ?, ?)",
                [(1, 1, "Alice project"), (2, 2, "Bob project")],
            )
            connection.executemany(
                """INSERT INTO tasks(
                    id, project_id, title, status, estimate_hours, created_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (1, 1, "Zero estimate", "todo", 0, "2026-08-28T00:30:00Z", 1),
                    (2, 1, "Alice second", "doing", 2, "2026-08-27T12:00:00Z", 3),
                    (3, 2, "Bob private", "todo", 5, "2026-08-28T01:00:00Z", 1),
                ],
            )


@contextmanager
def database(path: str):
    connection = connect(path)
    try:
        yield connection
    finally:
        connection.close()

