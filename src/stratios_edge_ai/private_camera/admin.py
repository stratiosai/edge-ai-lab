"""Local-only administrator creation and password reset operations."""

from __future__ import annotations

import time

from .database import Database
from .security import hash_password


def set_admin(database: Database, username: str, password: str) -> None:
    password_hash = hash_password(password)
    now = int(time.time())
    with database.connect() as connection:
        row = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row is None:
            connection.execute(
                """
                INSERT INTO users(username, password_hash, is_admin, created_at)
                VALUES (?, ?, 1, ?)
                """,
                (username, password_hash, now),
            )
        else:
            connection.execute(
                "UPDATE users SET password_hash = ?, is_admin = 1 WHERE id = ?",
                (password_hash, row["id"]),
            )
            connection.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
