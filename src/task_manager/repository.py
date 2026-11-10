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
            id=row["id"],
            title=row["title"],
            description=row["description"],
            completed=bool(row["completed"]),
            priority=row["priority"],
            due_date=row["due_date"],
        )

    # Metode lama dipertahankan untuk CLI dan fitur lokal.
    def create(self, task: Task) -> Task:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """INSERT INTO tasks (title, description, completed, priority, due_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    task.title,
                    task.description,
                    int(task.completed),
                    task.priority,
                    task.due_date,
                ),
            )
            task_id = cursor.lastrowid
        return Task(
            id=task_id,
            title=task.title,
            description=task.description,
            completed=task.completed,
            priority=task.priority,
            due_date=task.due_date,
        )

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
                (
                    task.title,
                    task.description,
                    int(task.completed),
                    task.priority,
                    task.due_date,
                    task.id,
                ),
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
                (
                    task.title,
                    task.description,
                    int(task.completed),
                    task.priority,
                    task.due_date,
                    user_id,
                ),
            )
            task_id = cursor.lastrowid
            row = connection.execute(
                """SELECT id, title, description, completed, priority, due_date
                   FROM tasks WHERE id=? AND user_id=?""",
                (task_id, user_id),
            ).fetchone()
        return self._task(row)

    def get_all_for_user(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
        search: str | None = None,
        completed: bool | None = None,
        priority: str | None = None,
        sort_by: str = "id",
        sort_order: str = "asc",
        due_from: str | None = None,
        due_to: str | None = None,
    ) -> list[Task]:
        """Mengambil tugas milik pengguna dengan pencarian, filter,
        pagination, dan sorting.
        """
        sort_columns = {
            "id": "id",
            "created_at": "created_at",
            "title": "title",
            "priority": "priority",
            "due_date": "due_date",
        }

        if sort_by not in sort_columns:
            raise ValueError("Kolom pengurutan tidak valid.")

        if sort_order not in {"asc", "desc"}:
            raise ValueError("Arah pengurutan harus 'asc' atau 'desc'.")

        query = """
            SELECT id, title, description, completed, priority, due_date
            FROM tasks
            WHERE user_id = ?
        """
        params: list = [user_id]

        if search is not None:
            query += " AND title LIKE ?"
            params.append(f"%{search.strip()}%")

        if completed is not None:
            query += " AND completed = ?"
            params.append(int(completed))

        if priority is not None:
            query += " AND priority = ?"
            params.append(priority)

        if due_from is not None:
            query += " AND due_date >= ?"
            params.append(due_from)

        if due_to is not None:
            query += " AND due_date <= ?"
            params.append(due_to)

        if sort_by == "priority":
            query += """
                ORDER BY
                    CASE priority
                        WHEN 'High' THEN 3
                        WHEN 'Medium' THEN 2
                        WHEN 'Low' THEN 1
                        ELSE 0
                    END
            """
        elif sort_by == "due_date":
            query += """
                ORDER BY
                    CASE WHEN due_date IS NULL THEN 1 ELSE 0 END ASC,
                    due_date
            """
        else:
            query += f" ORDER BY {sort_columns[sort_by]}"

        query += f" {sort_order.upper()}, id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_connection(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()

        return [self._task(row) for row in rows]

    def get_for_user(self, task_id: int, user_id: int) -> Task | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """SELECT id, title, description, completed, priority, due_date
                   FROM tasks WHERE id=? AND user_id=?""",
                (task_id, user_id),
            ).fetchone()
        return self._task(row) if row else None

    def update_for_user(
        self,
        task_id: int,
        user_id: int,
        *,
        title: str,
        description: str,
        priority: str,
        due_date: str | None,
    ) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """UPDATE tasks SET title=?, description=?, priority=?, due_date=?
                   WHERE id=? AND user_id=?""",
                (title, description, priority, due_date, task_id, user_id),
            )
        return cursor.rowcount > 0

    def update_fields_for_user(
        self,
        task_id: int,
        user_id: int,
        fields: dict,
    ) -> bool:
        """Memperbarui field tertentu dari tugas milik pengguna."""
        allowed_fields = {"title", "description", "priority", "due_date"}
        if not fields or not fields.keys() <= allowed_fields:
            return False

        assignments = ", ".join(f"{field} = ?" for field in fields)
        values = list(fields.values()) + [task_id, user_id]

        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                f"""UPDATE tasks SET {assignments}
                    WHERE id = ? AND user_id = ?""",
                values,
            )

        return cursor.rowcount > 0

    def complete_for_user(self, task_id: int, user_id: int) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "UPDATE tasks SET completed=1 WHERE id=? AND user_id=?",
                (task_id, user_id),
            )
        return cursor.rowcount > 0

    def delete_for_user(self, task_id: int, user_id: int) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            )
        return cursor.rowcount > 0

    def get_all_for_user_statistics(self, user_id: int) -> list[Task]:
        """Mengambil seluruh tugas milik pengguna untuk perhitungan statistik."""
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT id, title, description, completed, priority, due_date
                FROM tasks
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()

        return [self._task(row) for row in rows]
