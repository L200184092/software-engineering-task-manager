from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection, init_db
from .models import Subtask


class SubtaskRepository:
    """Menyediakan CRUD subtask dengan pemeriksaan kepemilikan task."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        init_db(db_path)

    @staticmethod
    def _subtask(row) -> Subtask:
        return Subtask(
            id=row["id"],
            task_id=row["task_id"],
            user_id=row["user_id"],
            title=row["title"],
            completed=bool(row["completed"]),
        )

    def create_for_task(
        self,
        task_id: int,
        user_id: int,
        title: str,
    ) -> Subtask | None:
        with get_connection(self.db_path) as connection:
            owner = connection.execute(
                "SELECT 1 FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id),
            ).fetchone()

            if owner is None:
                return None

            cursor = connection.execute(
                """
                INSERT INTO subtasks (task_id, user_id, title)
                VALUES (?, ?, ?)
                """,
                (task_id, user_id, title),
            )

            row = connection.execute(
                """
                SELECT id, task_id, user_id, title, completed
                FROM subtasks
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

        return self._subtask(row)

    def list_for_task(
        self,
        task_id: int,
        user_id: int,
    ) -> list[Subtask] | None:
        with get_connection(self.db_path) as connection:
            owner = connection.execute(
                "SELECT 1 FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id),
            ).fetchone()

            if owner is None:
                return None

            rows = connection.execute(
                """
                SELECT s.id, s.task_id, s.user_id, s.title, s.completed
                FROM subtasks s
                JOIN tasks t ON t.id = s.task_id
                WHERE s.task_id = ?
                  AND s.user_id = ?
                  AND t.user_id = ?
                ORDER BY s.id
                """,
                (task_id, user_id, user_id),
            ).fetchall()

        return [self._subtask(row) for row in rows]

    def get_summary(
        self,
        task_id: int,
        user_id: int,
    ) -> dict[str, int | float]:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(
                        SUM(
                            CASE WHEN s.completed = 1
                            THEN 1 ELSE 0 END
                        ),
                        0
                    ) AS completed
                FROM subtasks s
                JOIN tasks t ON t.id = s.task_id
                WHERE s.task_id = ?
                  AND s.user_id = ?
                  AND t.user_id = ?
                """,
                (task_id, user_id, user_id),
            ).fetchone()

        total = row["total"]
        completed = row["completed"]

        return {
            "subtask_total": total,
            "subtask_completed": completed,
            "subtask_progress": (round(completed / total * 100, 2) if total else 0.0),
        }

    def update_for_user(
        self,
        subtask_id: int,
        task_id: int,
        user_id: int,
        *,
        title: str,
    ) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE subtasks
                SET title = ?
                WHERE id = ?
                  AND task_id = ?
                  AND user_id = ?
                  AND EXISTS (
                      SELECT 1
                      FROM tasks t
                      WHERE t.id = subtasks.task_id
                        AND t.user_id = ?
                  )
                """,
                (title, subtask_id, task_id, user_id, user_id),
            )

        return cursor.rowcount > 0

    def complete_for_user(
        self,
        subtask_id: int,
        task_id: int,
        user_id: int,
    ) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE subtasks
                SET completed = 1
                WHERE id = ?
                  AND task_id = ?
                  AND user_id = ?
                  AND EXISTS (
                      SELECT 1
                      FROM tasks t
                      WHERE t.id = subtasks.task_id
                        AND t.user_id = ?
                  )
                """,
                (subtask_id, task_id, user_id, user_id),
            )

        return cursor.rowcount > 0

    def delete_for_user(
        self,
        subtask_id: int,
        task_id: int,
        user_id: int,
    ) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                DELETE FROM subtasks
                WHERE id = ?
                  AND task_id = ?
                  AND user_id = ?
                  AND EXISTS (
                      SELECT 1
                      FROM tasks t
                      WHERE t.id = subtasks.task_id
                        AND t.user_id = ?
                  )
                """,
                (subtask_id, task_id, user_id, user_id),
            )

        return cursor.rowcount > 0
