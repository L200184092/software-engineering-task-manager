import sqlite3

import pytest

from src.task_manager.backup import backup_database, restore_database
from src.task_manager.database import get_connection, init_db


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


def test_backup_database_preserves_users_and_task_relationship(tmp_path):
    db_path = tmp_path / "source.db"
    backup_path = tmp_path / "backup.db"

    init_db(db_path)

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
            """,
            ("testuser", "test@example.com", "hashed-password"),
        )
        user_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO tasks (
                title, description, priority, due_date, user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Task milik pengguna", "Deskripsi", "High", None, user_id),
        )

    backup_database(backup_path, db_path)

    with get_connection(backup_path) as connection:
        user = connection.execute(
            "SELECT id, username, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        task = connection.execute(
            "SELECT title, user_id FROM tasks WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    assert user is not None
    assert user["username"] == "testuser"
    assert user["email"] == "test@example.com"
    assert task is not None
    assert task["title"] == "Task milik pengguna"
    assert task["user_id"] == user_id


def test_restore_database_preserves_users_and_task_relationship(tmp_path):
    db_path = tmp_path / "source.db"
    backup_path = tmp_path / "backup.db"
    restored_path = tmp_path / "restored.db"

    init_db(db_path)
    init_db(restored_path)

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
            """,
            ("restoreuser", "restore@example.com", "hashed-password"),
        )
        user_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO tasks (
                title, description, priority, due_date, user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Task untuk restore", "Deskripsi", "Medium", None, user_id),
        )

    with get_connection(restored_path) as connection:
        connection.execute(
            """
            INSERT INTO tasks (title, description, priority)
            VALUES (?, ?, ?)
            """,
            ("Task lama", "Akan digantikan oleh restore", "Low"),
        )

    backup_database(backup_path, db_path)
    restore_database(backup_path, restored_path)

    with get_connection(restored_path) as connection:
        user = connection.execute(
            "SELECT username, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        task = connection.execute(
            "SELECT title, user_id FROM tasks WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        old_task = connection.execute(
            "SELECT id FROM tasks WHERE title = ?",
            ("Task lama",),
        ).fetchone()

    assert user is not None
    assert user["username"] == "restoreuser"
    assert user["email"] == "restore@example.com"
    assert task is not None
    assert task["title"] == "Task untuk restore"
    assert task["user_id"] == user_id
    assert old_task is None


def test_restore_database_rejects_backup_without_users_table(tmp_path):
    db_path = tmp_path / "tasks.db"
    backup_path = tmp_path / "backup-without-users.db"

    init_db(db_path)
    add_task(db_path, "Data tujuan harus tetap ada")

    with sqlite3.connect(backup_path) as connection:
        connection.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                priority TEXT NOT NULL DEFAULT 'Medium',
                due_date TEXT,
                user_id INTEGER REFERENCES users(id)
            )
            """
        )

    with pytest.raises(ValueError, match="tabel tasks dan users"):
        restore_database(backup_path, db_path)

    assert get_titles(db_path) == ["Data tujuan harus tetap ada"]
