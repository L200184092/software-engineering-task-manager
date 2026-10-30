import sqlite3

import pytest

from task_manager.auth import hash_password
from task_manager.database import get_connection
from task_manager.models import User
from task_manager.user_repository import UserRepository


def test_create_and_find_user(tmp_path):
    db_path = tmp_path / "test_users.db"
    repository = UserRepository(db_path)

    user = User(
        username="ganno_test",
        email="ganno_test@example.com",
        password_hash=hash_password("ContohPassword123!"),
    )

    created = repository.create(user)

    assert created.id is not None
    assert repository.get_by_username("ganno_test").email == ("ganno_test@example.com")
    assert repository.get_by_email("ganno_test@example.com").username == ("ganno_test")


def test_find_missing_user_returns_none(tmp_path):
    repository = UserRepository(tmp_path / "test_users.db")

    assert repository.get_by_username("tidak_ada") is None
    assert repository.get_by_email("missing@example.com") is None


def test_duplicate_username_is_rejected(tmp_path):
    repository = UserRepository(tmp_path / "test_users.db")

    first_user = User(
        username="same_user",
        email="first@example.com",
        password_hash=hash_password("Password123!"),
    )
    second_user = User(
        username="same_user",
        email="second@example.com",
        password_hash=hash_password("Password456!"),
    )

    repository.create(first_user)

    with pytest.raises(sqlite3.IntegrityError):
        repository.create(second_user)


def test_foreign_key_rejects_nonexistent_user(tmp_path):
    db_path = tmp_path / "test_foreign_keys.db"

    # Membuat database beserta tabel melalui repository.
    UserRepository(db_path)

    # Tugas tidak boleh merujuk ke pengguna yang tidak ada.
    with get_connection(db_path) as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO tasks (title, user_id)
            VALUES (?, ?)
            """,
            ("Tugas dengan pengguna tidak valid", 999999),
        )
