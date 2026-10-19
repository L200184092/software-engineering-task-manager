
import sqlite3

import pytest

from src.task_manager.backup import backup_database, restore_database
from src.task_manager.database import init_db, get_connection


def add_task(db_path, title):
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO tasks (title, description, priority, due_date) "
            "VALUES (?, '', 'Medium', NULL)",
            (title,),
        )


def get_titles(db_path):
    with get_connection(db_path) as connection:
        return [
            row["title"]
            for row in connection.execute(
                "SELECT title FROM tasks ORDER BY id"
            ).fetchall()
        ]


def test_backup_database_preserves_tasks(tmp_path):
    db_path = tmp_path / "tasks.db"
    backup_path = tmp_path / "backup.db"

    init_db(db_path)
    add_task(db_path, "Tugas pertama")

    result = backup_database(backup_path, db_path)

    assert result == backup_path
    assert get_titles(backup_path) == ["Tugas pertama"]


def test_backup_database_rejects_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup_database(
            tmp_path / "backup.db",
            tmp_path / "missing.db",
        )


def test_backup_database_rejects_same_path(tmp_path):
    db_path = tmp_path / "tasks.db"
    init_db(db_path)

    with pytest.raises(ValueError):
        backup_database(db_path, db_path)


def test_restore_database_restores_tasks(tmp_path):
    db_path = tmp_path / "tasks.db"
    backup_path = tmp_path / "backup.db"

    init_db(db_path)
    add_task(db_path, "Tugas dari backup")
    backup_database(backup_path, db_path)

    add_task(db_path, "Tugas tambahan")
    assert len(get_titles(db_path)) == 2

    restore_database(backup_path, db_path)

    assert get_titles(db_path) == ["Tugas dari backup"]


def test_restore_database_rejects_missing_backup(tmp_path):
    db_path = tmp_path / "tasks.db"
    init_db(db_path)

    with pytest.raises(FileNotFoundError):
        restore_database(
            tmp_path / "missing.db",
            db_path,
        )


def test_restore_database_rejects_invalid_file(tmp_path):
    db_path = tmp_path / "tasks.db"
    invalid_backup = tmp_path / "invalid.db"

    init_db(db_path)
    add_task(db_path, "Tugas tetap ada")
    invalid_backup.write_text("bukan database SQLite", encoding="utf-8")

    with pytest.raises(sqlite3.DatabaseError):
        restore_database(invalid_backup, db_path)

    assert get_titles(db_path) == ["Tugas tetap ada"]


def test_restore_database_rejects_database_without_tasks_table(tmp_path):
    db_path = tmp_path / "tasks.db"
    backup_path = tmp_path / "wrong-schema.db"

    init_db(db_path)
    add_task(db_path, "Tugas tetap ada")

    with sqlite3.connect(backup_path) as connection:
        connection.execute("CREATE TABLE other_table (id INTEGER)")

    with pytest.raises(ValueError, match="tabel tasks"):
        restore_database(backup_path, db_path)

    assert get_titles(db_path) == ["Tugas tetap ada"]
