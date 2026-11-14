from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection, init_db
from .models import TaskAttachment


class AttachmentRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    @property
    def storage_dir(self) -> Path:
        return self.db_path.parent / "attachments"

    @staticmethod
    def _attachment(row) -> TaskAttachment:
        return TaskAttachment(
            id=row["id"],
            task_id=row["task_id"],
            user_id=row["user_id"],
            original_filename=row["original_filename"],
            storage_filename=row["storage_filename"],
            content_type=row["content_type"],
            file_size=row["file_size"],
            created_at=row["created_at"],
        )

    def create(
        self,
        *,
        task_id: int,
        user_id: int,
        original_filename: str,
        storage_filename: str,
        content_type: str,
        file_size: int,
    ) -> TaskAttachment:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO task_attachments (
                    task_id, user_id, original_filename, storage_filename,
                    content_type, file_size
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    user_id,
                    original_filename,
                    storage_filename,
                    content_type,
                    file_size,
                ),
            )
            row = conn.execute(
                "SELECT * FROM task_attachments WHERE id=?", (cursor.lastrowid,)
            ).fetchone()
        return self._attachment(row)

    def list_for_task(self, task_id: int, user_id: int) -> list[TaskAttachment] | None:
        with get_connection(self.db_path) as conn:
            owner = conn.execute(
                "SELECT 1 FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
            if owner is None:
                return None
            rows = conn.execute(
                """
                SELECT * FROM task_attachments
                WHERE task_id=? AND user_id=?
                ORDER BY id
                """,
                (task_id, user_id),
            ).fetchall()
        return [self._attachment(row) for row in rows]

    def get_for_task(
        self, attachment_id: int, task_id: int, user_id: int
    ) -> TaskAttachment | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT * FROM task_attachments
                WHERE id=? AND task_id=? AND user_id=?
                """,
                (attachment_id, task_id, user_id),
            ).fetchone()
        return self._attachment(row) if row else None

    def delete_for_task(
        self, attachment_id: int, task_id: int, user_id: int
    ) -> TaskAttachment | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT * FROM task_attachments
                WHERE id=? AND task_id=? AND user_id=?
                """,
                (attachment_id, task_id, user_id),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                """
                DELETE FROM task_attachments
                WHERE id=? AND task_id=? AND user_id=?
                """,
                (attachment_id, task_id, user_id),
            )
        return self._attachment(row)

    def list_storage_names_for_task(self, task_id: int, user_id: int) -> list[str]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT storage_filename FROM task_attachments
                WHERE task_id=? AND user_id=?
                """,
                (task_id, user_id),
            ).fetchall()
        return [row["storage_filename"] for row in rows]
