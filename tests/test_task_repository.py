
from task_manager.auth import hash_password
from task_manager.models import Task, User
from task_manager.repository import TaskRepository
from task_manager.user_repository import UserRepository


def test_filter_tasks_by_due_date_range(tmp_path):
    db_path = tmp_path / "test_tasks.db"

    task_repository = TaskRepository(db_path)
    user_repository = UserRepository(db_path)

    user = user_repository.create(
        User(
            username="deadline_user",
            email="deadline@example.com",
            password_hash=hash_password("StrongPass123!"),
        )
    )

    tasks = [
        Task(
            title="Tugas sebelum rentang",
            description="",
            completed=False,
            priority="Medium",
            due_date="2026-11-03",
        ),
        Task(
            title="Tugas dalam rentang",
            description="",
            completed=False,
            priority="Medium",
            due_date="2026-11-06",
        ),
        Task(
            title="Tugas setelah rentang",
            description="",
            completed=False,
            priority="Medium",
            due_date="2026-11-12",
        ),
        Task(
            title="Tugas tanpa deadline",
            description="",
            completed=False,
            priority="Medium",
            due_date=None,
        ),
    ]

    for task in tasks:
        task_repository.create_for_user(task, user.id)

    result = task_repository.get_all_for_user(
        user_id=user.id,
        due_from="2026-11-04",
        due_to="2026-11-10",
    )

    assert len(result) == 1
    assert result[0].title == "Tugas dalam rentang"
