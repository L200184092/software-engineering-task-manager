from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection, init_db
from .models import Tag


class TagRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        init_db(db_path)

    @staticmethod
    def _tag(row) -> Tag:
        return Tag(id=row["id"], name=row["name"], user_id=row["user_id"])

    def create_for_user(self, name: str, user_id: int) -> Tag:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO tags(name, user_id) VALUES (?, ?)", (name, user_id)
            )
            row = conn.execute(
                "SELECT * FROM tags WHERE id=?", (cursor.lastrowid,)
            ).fetchone()
        return self._tag(row)

    def list_for_user(self, user_id: int) -> list[Tag]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM tags WHERE user_id=? ORDER BY name COLLATE NOCASE, id",
                (user_id,),
            ).fetchall()
        return [self._tag(row) for row in rows]

    def get_for_user(self, tag_id: int, user_id: int) -> Tag | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tags WHERE id=? AND user_id=?", (tag_id, user_id)
            ).fetchone()
        return self._tag(row) if row else None

    def update_for_user(self, tag_id: int, user_id: int, name: str) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE tags SET name=? WHERE id=? AND user_id=?",
                (name, tag_id, user_id),
            )
        return cursor.rowcount > 0

    def delete_for_user(self, tag_id: int, user_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM tags WHERE id=? AND user_id=?", (tag_id, user_id)
            )
        return cursor.rowcount > 0

    def list_for_task(self, task_id: int, user_id: int) -> list[Tag] | None:
        with get_connection(self.db_path) as conn:
            owner = conn.execute(
                "SELECT 1 FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
            if owner is None:
                return None
            rows = conn.execute(
                """SELECT t.* FROM tags t JOIN task_tags tt ON tt.tag_id=t.id
                   WHERE tt.task_id=? AND tt.user_id=? AND t.user_id=?
                   ORDER BY t.name COLLATE NOCASE, t.id""",
                (task_id, user_id, user_id),
            ).fetchall()
        return [self._tag(row) for row in rows]

    def set_for_task(self, task_id: int, user_id: int, tag_ids: list[int]) -> bool:
        unique_ids = list(dict.fromkeys(tag_ids))
        with get_connection(self.db_path) as conn:
            owner = conn.execute(
                "SELECT 1 FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
            if owner is None:
                return False
            if unique_ids:
                placeholders = ",".join("?" for _ in unique_ids)
                valid = conn.execute(
                    f"SELECT COUNT(*) FROM tags WHERE user_id=? AND id IN ({placeholders})",
                    [user_id, *unique_ids],
                ).fetchone()[0]
                if valid != len(unique_ids):
                    raise ValueError("Satu atau lebih tag tidak ditemukan.")
            conn.execute(
                "DELETE FROM task_tags WHERE task_id=? AND user_id=?",
                (task_id, user_id),
            )
            conn.executemany(
                "INSERT INTO task_tags(task_id, tag_id, user_id) VALUES (?, ?, ?)",
                [(task_id, tag_id, user_id) for tag_id in unique_ids],
            )
        return True

    def list_task_ids_for_tag(self, tag_id: int, user_id: int) -> list[int] | None:
        with get_connection(self.db_path) as conn:
            if (
                conn.execute(
                    "SELECT 1 FROM tags WHERE id=? AND user_id=?", (tag_id, user_id)
                ).fetchone()
                is None
            ):
                return None
            rows = conn.execute(
                "SELECT task_id FROM task_tags WHERE tag_id=? AND user_id=? ORDER BY task_id",
                (tag_id, user_id),
            ).fetchall()
        return [row["task_id"] for row in rows]
