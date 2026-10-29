from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection, init_db
from .models import Task


class TaskRepository:
    """Mengelola penyimpanan tugas SQLite, termasuk operasi yang dibatasi pemilik."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        init_db(db_path)

    @staticmethod
    def _task(row) -> Task:
        return Task(
            id=row["id"], title=row["title"], description=row["description"],
            completed=bool(row["completed"]), priority=row["priority"],
            due_date=row["due_date"],
        )

    # Metode lama dipertahankan untuk CLI dan fitur lokal.
    def create(self, task: Task) -> Task:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """INSERT INTO tasks (title, description, completed, priority, due_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (task.title, task.description, int(task.completed), task.priority, task.due_date),
            )
            task_id = cursor.lastrowid
        return Task(id=task_id, title=task.title, description=task.description,
                    completed=task.completed, priority=task.priority, due_date=task.due_date)

    def get_all(self) -> list[Task]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """SELECT id, title, description, completed, priority, due_date
                   FROM tasks ORDER BY id"""
            ).fetchall()
        return [self._task(row) for row in rows]

    def update(self, task: Task) -> bool:
        if task.id is None:
            return False
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """UPDATE tasks SET title=?, description=?, completed=?, priority=?, due_date=?
                   WHERE id=?""",
                (task.title, task.description, int(task.completed), task.priority, task.due_date, task.id),
            )
        return cursor.rowcount > 0

    def delete(self, task_id: int) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return cursor.rowcount > 0

    # Metode khusus API: semua query dibatasi user_id di database.
    def create_for_user(self, task: Task, user_id: int) -> Task:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """INSERT INTO tasks (title, description, completed, priority, due_date, user_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (task.title, task.description, int(task.completed), task.priority, task.due_date, user_id),
            )
            task_id = cursor.lastrowid
            row = connection.execute(
                """SELECT id, title, description, completed, priority, due_date
                   FROM tasks WHERE id=? AND user_id=?""", (task_id, user_id)
            ).fetchone()
        return self._task(row)

    def get_all_for_user(self, user_id: int) -> list[Task]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """SELECT id, title, description, completed, priority, due_date
                   FROM tasks WHERE user_id=? ORDER BY id""", (user_id,)
            ).fetchall()
        return [self._task(row) for row in rows]

    def get_for_user(self, task_id: int, user_id: int) -> Task | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """SELECT id, title, description, completed, priority, due_date
                   FROM tasks WHERE id=? AND user_id=?""", (task_id, user_id)
            ).fetchone()
        return self._task(row) if row else None

    def update_for_user(self, task_id: int, user_id: int, *, title: str,
                        description: str, priority: str, due_date: str | None) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """UPDATE tasks SET title=?, description=?, priority=?, due_date=?
                   WHERE id=? AND user_id=?""",
                (title, description, priority, due_date, task_id, user_id),
            )
        return cursor.rowcount > 0

    def complete_for_user(self, task_id: int, user_id: int) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "UPDATE tasks SET completed=1 WHERE id=? AND user_id=?", (task_id, user_id)
            )
        return cursor.rowcount > 0

    def delete_for_user(self, task_id: int, user_id: int) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            )
        return cursor.rowcount > 0
