import sqlite3
from contextlib import closing
from pathlib import Path

from .database import DEFAULT_DB_PATH, get_connection


def backup_database(
    backup_path: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Path:
    """Membuat backup database SQLite ke file tujuan."""
    source = Path(db_path)
    destination = Path(backup_path)

    if not source.is_file():
        raise FileNotFoundError(
            f"Database sumber tidak ditemukan: {source}"
        )

    if source.resolve() == destination.resolve():
        raise ValueError(
            "Lokasi backup tidak boleh sama dengan database sumber."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    with closing(get_connection(source)) as source_connection:
        with closing(sqlite3.connect(destination)) as backup_connection:
            source_connection.backup(backup_connection)

    return destination



def restore_database(
    backup_path: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Memulihkan database dari backup SQLite yang valid."""
    source = Path(backup_path)
    destination = Path(db_path)

    if not source.is_file():
        raise FileNotFoundError(
            f"File backup tidak ditemukan: {source}"
        )

    if source.resolve() == destination.resolve():
        raise ValueError(
            "File backup tidak boleh sama dengan database tujuan."
        )

    # Validasi integritas dan skema backup sebelum restore.
    with closing(sqlite3.connect(source)) as backup_connection:
        result = backup_connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if result is None or result[0] != "ok":
            raise ValueError(
                "File backup bukan database SQLite yang valid."
            )

        tables = {
            row[0]
            for row in backup_connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        required_tables = {"tasks", "users"}

        if not required_tables.issubset(tables):
            raise ValueError(
                "File backup harus memiliki tabel tasks dan users."
            )

        required_task_columns = {
            "id",
            "title",
            "description",
            "completed",
            "created_at",
            "priority",
            "due_date",
            "user_id",
        }

        task_columns = {
            row[1]
            for row in backup_connection.execute(
                "PRAGMA table_info(tasks)"
            ).fetchall()
        }

        if not required_task_columns.issubset(task_columns):
            raise ValueError(
                "Skema tabel tasks pada backup tidak sesuai."
            )

        required_user_columns = {
            "id",
            "username",
            "email",
            "password_hash",
            "created_at",
        }

        user_columns = {
            row[1]
            for row in backup_connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if not required_user_columns.issubset(user_columns):
            raise ValueError(
                "Skema tabel users pada backup tidak sesuai."
            )

        foreign_keys = backup_connection.execute(
            "PRAGMA foreign_key_list(tasks)"
        ).fetchall()

        has_user_foreign_key = any(
            row[2] == "users"
            and row[3] == "user_id"
            and row[4] == "id"
            for row in foreign_keys
        )

        if not has_user_foreign_key:
            raise ValueError(
                "Relasi tasks.user_id ke users.id tidak ditemukan."
            )

    # Pulihkan melalui SQLite Backup API tanpa mengganti file aktif.
    destination.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(source)) as source_connection:
        with closing(get_connection(destination)) as destination_connection:
            source_connection.backup(destination_connection)
