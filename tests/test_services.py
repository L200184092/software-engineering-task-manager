import pytest
from src.task_manager.database import init_db
from src.task_manager.repository import TaskRepository
from src.task_manager.services import TaskService


def create_test_service(tmp_path):
    """Membuat service dengan database khusus untuk pengujian."""
    db_path = tmp_path / "test_tasks.db"
    init_db(db_path)
    repository = TaskRepository(db_path)
    return TaskService(repository)


def test_create_task(tmp_path):
    service = create_test_service(tmp_path)

    task = service.create_task("Belajar pytest", "Mempelajari unit test")

    assert task.id is not None
    assert task.title == "Belajar pytest"
    assert task.description == "Mempelajari unit test"
    assert task.completed is False



def test_create_task_rejects_empty_title(tmp_path):
    service = create_test_service(tmp_path)

    with pytest.raises(
        ValueError,
        match="Judul tugas tidak boleh kosong.",
    ):
        service.create_task("   ")



def test_update_task(tmp_path):
    service = create_test_service(tmp_path)
    task = service.create_task("Tugas lama", "Deskripsi lama")

    result = service.update_task(task.id, "Tugas baru", "Deskripsi baru")

    assert result is True
    updated_task = service.list_tasks()[0]
    assert updated_task.title == "Tugas baru"
    assert updated_task.description == "Deskripsi baru"


def test_complete_task(tmp_path):
    service = create_test_service(tmp_path)
    task = service.create_task("Tugas selesai")

    result = service.complete_task(task.id)

    assert result is True
    assert service.list_tasks()[0].completed is True


def test_delete_task(tmp_path):
    service = create_test_service(tmp_path)
    task = service.create_task("Tugas yang akan dihapus")

    result = service.delete_task(task.id)

    assert result is True
    assert service.list_tasks() == []


def test_update_nonexistent_task_returns_false(tmp_path):
    service = create_test_service(tmp_path)

    assert service.update_task(999, "Tugas baru") is False


def test_complete_nonexistent_task_returns_false(tmp_path):
    service = create_test_service(tmp_path)

    assert service.complete_task(999) is False


def test_delete_nonexistent_task_returns_false(tmp_path):
    service = create_test_service(tmp_path)

    assert service.delete_task(999) is False
