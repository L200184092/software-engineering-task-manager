from task_manager.auth import hash_password
from task_manager.database import init_db
from task_manager.models import Task, User
from task_manager.repository import TaskRepository
from task_manager.subtask_repository import SubtaskRepository
from task_manager.user_repository import UserRepository


def test_subtask_repository_crud_and_progress(tmp_path):
    db_path = tmp_path / "subtasks.db"
    init_db(db_path)

    user = UserRepository(db_path).create(
        User(
            "subtask_repo",
            "subtask_repo@example.com",
            hash_password("StrongPass123!"),
        )
    )

    task = TaskRepository(db_path).create_for_user(
        Task("Parent task"),
        user.id,
    )

    repository = SubtaskRepository(db_path)

    first = repository.create_for_task(
        task.id,
        user.id,
        "First",
    )
    second = repository.create_for_task(
        task.id,
        user.id,
        "Second",
    )

    assert first is not None
    assert second is not None

    assert repository.get_summary(task.id, user.id) == {
        "subtask_total": 2,
        "subtask_completed": 0,
        "subtask_progress": 0.0,
    }

    assert (
        repository.complete_for_user(
            first.id,
            task.id,
            user.id,
        )
        is True
    )

    assert repository.get_summary(task.id, user.id)["subtask_progress"] == 50.0

    assert (
        repository.update_for_user(
            second.id,
            task.id,
            user.id,
            title="Updated",
        )
        is True
    )

    assert (
        repository.delete_for_user(
            second.id,
            task.id,
            user.id,
        )
        is True
    )

    assert len(repository.list_for_task(task.id, user.id)) == 1


def test_subtask_repository_rejects_other_users(tmp_path):
    db_path = tmp_path / "subtasks_scope.db"
    init_db(db_path)

    users = UserRepository(db_path)

    first_user = users.create(
        User(
            "first",
            "first@example.com",
            hash_password("StrongPass123!"),
        )
    )

    second_user = users.create(
        User(
            "second",
            "second@example.com",
            hash_password("StrongPass123!"),
        )
    )

    task = TaskRepository(db_path).create_for_user(
        Task("Private task"),
        first_user.id,
    )

    repository = SubtaskRepository(db_path)

    assert (
        repository.create_for_task(
            task.id,
            second_user.id,
            "Forbidden",
        )
        is None
    )

    assert (
        repository.list_for_task(
            task.id,
            second_user.id,
        )
        is None
    )
