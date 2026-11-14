from task_manager.activity_repository import ActivityRepository
from task_manager.auth import hash_password
from task_manager.comment_repository import CommentRepository
from task_manager.database import init_db
from task_manager.models import Task, User
from task_manager.repository import TaskRepository
from task_manager.user_repository import UserRepository


def setup_data(tmp_path):
    db_path = tmp_path / "comments_activity.db"
    init_db(db_path)
    users = UserRepository(db_path)
    owner = users.create(
        User("owner", "owner@example.com", hash_password("StrongPass123!"))
    )
    other = users.create(
        User("other", "other@example.com", hash_password("StrongPass123!"))
    )
    task = TaskRepository(db_path).create_for_user(Task("Sample task"), owner.id)
    return db_path, owner, other, task


def test_comment_crud_and_activity_log(tmp_path):
    db_path, owner, _, task = setup_data(tmp_path)
    comments = CommentRepository(db_path)
    comment = comments.create(task.id, owner.id, "Initial note")
    assert comment is not None
    assert comment.content == "Initial note"
    assert comments.update(comment.id, task.id, owner.id, "Edited note")
    assert comments.list_for_task(task.id, owner.id)[0].content == "Edited note"
    activity = ActivityRepository(db_path)
    assert (
        activity.record(task.id, owner.id, "comment_added", "Edited note") is not None
    )
    entries = activity.list_for_task(task.id, owner.id)
    assert len(entries) == 1
    assert entries[0].action == "comment_added"
    assert comments.delete(comment.id, task.id, owner.id)
    assert comments.list_for_task(task.id, owner.id) == []


def test_comments_and_activity_are_user_scoped(tmp_path):
    db_path, owner, other, task = setup_data(tmp_path)
    comments = CommentRepository(db_path)
    comment = comments.create(task.id, owner.id, "Private")
    assert comment is not None
    assert comments.list_for_task(task.id, other.id) is None
    assert not comments.update(comment.id, task.id, other.id, "Hacked")
    assert not comments.delete(comment.id, task.id, other.id)
    activity = ActivityRepository(db_path)
    activity.record(task.id, owner.id, "task_created", "Sample task")
    assert activity.list_for_task(task.id, other.id) is None
