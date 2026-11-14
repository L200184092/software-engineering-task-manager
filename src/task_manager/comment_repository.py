from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection, init_db
from .models import TaskComment


class CommentRepository:
    """CRUD komentar task dengan pembatasan kepemilikan pengguna."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        init_db(db_path)

    @staticmethod
    def _comment(row) -> TaskComment:
        return TaskComment(
            row["task_id"],
            row["user_id"],
            row["content"],
            row["id"],
            row["created_at"],
            row["updated_at"],
        )

    def create(self, task_id: int, user_id: int, content: str) -> TaskComment | None:
        with get_connection(self.db_path) as conn:
            owner = conn.execute(
                "SELECT 1 FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
            if owner is None:
                return None
            cur = conn.execute(
                "INSERT INTO task_comments(task_id,user_id,content) VALUES(?,?,?)",
                (task_id, user_id, content),
            )
            row = conn.execute(
                "SELECT * FROM task_comments WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        return self._comment(row)

    def list_for_task(self, task_id: int, user_id: int) -> list[TaskComment] | None:
        with get_connection(self.db_path) as conn:
            owner = conn.execute(
                "SELECT 1 FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
            if owner is None:
                return None
            rows = conn.execute(
                "SELECT * FROM task_comments WHERE task_id=? AND user_id=? ORDER BY id",
                (task_id, user_id),
            ).fetchall()
        return [self._comment(row) for row in rows]

    def update(self, comment_id: int, task_id: int, user_id: int, content: str) -> bool:
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE task_comments SET content=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND task_id=? AND user_id=? AND EXISTS (SELECT 1 FROM tasks WHERE id=? AND user_id=?)",
                (content, comment_id, task_id, user_id, task_id, user_id),
            )
        return cur.rowcount > 0

    def delete(self, comment_id: int, task_id: int, user_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM task_comments WHERE id=? AND task_id=? AND user_id=? AND EXISTS (SELECT 1 FROM tasks WHERE id=? AND user_id=?)",
                (comment_id, task_id, user_id, task_id, user_id),
            )
        return cur.rowcount > 0
