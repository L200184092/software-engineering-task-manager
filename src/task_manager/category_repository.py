from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection, init_db
from .models import Category


class CategoryRepository:
    """Mengelola operasi database untuk kategori tugas."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def create_for_user(self, category: Category) -> Category:
        """Membuat kategori baru untuk pengguna tertentu."""
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO categories (name, user_id)
                VALUES (?, ?)
                """,
                (category.name, category.user_id),
            )
            category.id = cursor.lastrowid

        return category

    def get_all_for_user(self, user_id: int) -> list[Category]:
        """Mengambil seluruh kategori milik pengguna."""
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT id, name, user_id
                FROM categories
                WHERE user_id = ?
                ORDER BY name COLLATE NOCASE
                """,
                (user_id,),
            ).fetchall()

        return [
            Category(
                id=row["id"],
                name=row["name"],
                user_id=row["user_id"],
            )
            for row in rows
        ]

    def get_for_user(
        self,
        category_id: int,
        user_id: int,
    ) -> Category | None:
        """Mengambil kategori berdasarkan ID dan pemiliknya."""
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT id, name, user_id
                FROM categories
                WHERE id = ? AND user_id = ?
                """,
                (category_id, user_id),
            ).fetchone()

        if row is None:
            return None

        return Category(
            id=row["id"],
            name=row["name"],
            user_id=row["user_id"],
        )

    def update_for_user(
        self,
        category_id: int,
        user_id: int,
        name: str,
    ) -> bool:
        """Memperbarui nama kategori milik pengguna."""
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE categories
                SET name = ?
                WHERE id = ? AND user_id = ?
                """,
                (name, category_id, user_id),
            )

        return cursor.rowcount > 0

    def delete_for_user(
        self,
        category_id: int,
        user_id: int,
    ) -> bool:
        """Menghapus kategori milik pengguna."""
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                DELETE FROM categories
                WHERE id = ? AND user_id = ?
                """,
                (category_id, user_id),
            )

        return cursor.rowcount > 0
