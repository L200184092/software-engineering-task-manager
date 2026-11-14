from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection, init_db
from .models import TaskActivity


class ActivityRepository:
    """Menyimpan dan membaca riwayat aktivitas task."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        init_db(db_path)

    def record(
        self, task_id: int, user_id: int, action: str, details: str = ""
    ) -> TaskActivity | None:
        with get_connection(self.db_path) as conn:
            owner = conn.execute(
                "SELECT 1 FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
            if owner is None:
                return None
            cur = conn.execute(
                "INSERT INTO task_activity_logs(task_id,user_id,action,details) VALUES(?,?,?,?)",
                (task_id, user_id, action, details),
            )
            row = conn.execute(
                "SELECT * FROM task_activity_logs WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        return TaskActivity(
            row["task_id"],
            row["user_id"],
            row["action"],
            row["details"],
            row["id"],
            row["created_at"],
        )

    def list_for_task(
        self, task_id: int, user_id: int, limit: int = 100
    ) -> list[TaskActivity] | None:
        with get_connection(self.db_path) as conn:
            owner = conn.execute(
                "SELECT 1 FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
            if owner is None:
                return None
            rows = conn.execute(
                "SELECT * FROM task_activity_logs WHERE task_id=? AND user_id=? ORDER BY id DESC LIMIT ?",
                (task_id, user_id, limit),
            ).fetchall()
        return [
            TaskActivity(
                r["task_id"],
                r["user_id"],
                r["action"],
                r["details"],
                r["id"],
                r["created_at"],
            )
            for r in rows
        ]
