from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection, init_db
from .models import User


class UserRepository:
    """Mengelola penyimpanan pengguna di SQLite."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.db_path = db_path
        init_db(self.db_path)

    def create(self, user: User) -> User:
        """Menyimpan pengguna baru dan mengembalikan ID-nya."""
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (user.username, user.email, user.password_hash),
            )

            user_id = cursor.lastrowid

        return User(
            id=user_id,
            username=user.username,
            email=user.email,
            password_hash=user.password_hash,
        )

    def get_by_username(self, username: str) -> User | None:
        """Mencari pengguna berdasarkan username."""
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT id, username, email, password_hash
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

        if row is None:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
        )

    def get_by_email(self, email: str) -> User | None:
        """Mencari pengguna berdasarkan email."""
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT id, username, email, password_hash
                FROM users
                WHERE email = ?
                """,
                (email,),
            ).fetchone()

        if row is None:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
        )
