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

        if "tasks" not in tables:
            raise ValueError(
                "File backup tidak memiliki tabel tasks."
            )

        columns = {
            row[1]
            for row in backup_connection.execute(
                "PRAGMA table_info(tasks)"
            ).fetchall()
        }

        required_columns = {
            "id",
            "title",
            "description",
            "completed",
            "created_at",
            "priority",
            "due_date",
        }

        if not required_columns.issubset(columns):
            raise ValueError(
                "Skema tabel tasks pada backup tidak sesuai."
            )

    # Pulihkan melalui SQLite Backup API tanpa mengganti file aktif.
    destination.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(source)) as source_connection:
        with closing(get_connection(destination)) as destination_connection:
            source_connection.backup(destination_connection)
