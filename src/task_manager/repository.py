
import sqlite3
from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection
from .models import Task


class TaskRepository:
    """Mengelola penyimpanan tugas di SQLite."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.db_path = db_path

    def create(self, task: Task) -> Task:
        """Menyimpan tugas baru dan mengembalikan tugas dengan ID."""
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (title, description, completed)
                VALUES (?, ?, ?)
                """,
                (task.title, task.description, int(task.completed)),
            )

            task_id = cursor.lastrowid

        return Task(
            id=task_id,
            title=task.title,
            description=task.description,
            completed=task.completed,
        )

    def get_all(self) -> list[Task]:
        """Mengambil semua tugas dari database."""
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT id, title, description, completed
                FROM tasks
                ORDER BY id
                """
            ).fetchall()

        return [
            Task(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                completed=bool(row["completed"]),
            )
            for row in rows
        ]
    
    def update(self, task: Task) -> bool:
        """Memperbarui tugas berdasarkan ID."""
        if task.id is None:
            return False

        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, completed = ?
                WHERE id = ?
                """,
                (
                    task.title,
                    task.description,
                    int(task.completed),
                    task.id,
                ),
            )

        return cursor.rowcount > 0

    def delete(self, task_id: int) -> bool:
        """Menghapus tugas berdasarkan ID."""
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,),
            )

        return cursor.rowcount > 0
