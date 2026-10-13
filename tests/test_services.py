
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


def test_create_task_strips_whitespace(tmp_path):
    service = create_test_service(tmp_path)

    task = service.create_task("  Belajar Python  ", "  Latihan coding  ")

    assert task.title == "Belajar Python"
    assert task.description == "Latihan coding"


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

    result = service.update_task(
        task.id,
        "Tugas baru",
        "Deskripsi baru",
    )

    assert result is True
    updated_task = service.list_tasks()[0]
    assert updated_task.title == "Tugas baru"
    assert updated_task.description == "Deskripsi baru"


def test_update_task_rejects_empty_title(tmp_path):
    service = create_test_service(tmp_path)
    task = service.create_task("Tugas lama")

    with pytest.raises(
        ValueError,
        match="Judul tugas tidak boleh kosong.",
    ):
        service.update_task(task.id, "   ")


def test_update_nonexistent_task_returns_false(tmp_path):
    service = create_test_service(tmp_path)

    assert service.update_task(999, "Tugas baru") is False


def test_complete_task(tmp_path):
    service = create_test_service(tmp_path)
    task = service.create_task("Tugas selesai")

    result = service.complete_task(task.id)

    assert result is True
    assert service.list_tasks()[0].completed is True


def test_complete_nonexistent_task_returns_false(tmp_path):
    service = create_test_service(tmp_path)

    assert service.complete_task(999) is False


def test_delete_task(tmp_path):
    service = create_test_service(tmp_path)
    task = service.create_task("Tugas yang akan dihapus")

    result = service.delete_task(task.id)

    assert result is True
    assert service.list_tasks() == []


def test_delete_nonexistent_task_returns_false(tmp_path):
    service = create_test_service(tmp_path)

    assert service.delete_task(999) is False


def test_create_task_with_priority_and_due_date(tmp_path):
    service = create_test_service(tmp_path)

    task = service.create_task("Selesaikan proyek", "Tahap pengujian")

    task.priority = "High"
    task.due_date = "2026-10-20"
    service.repository.update(task)

    saved_task = service.list_tasks()[0]

    assert saved_task.priority == "High"
    assert saved_task.due_date == "2026-10-20"


def test_update_task_priority_and_due_date(tmp_path):
    service = create_test_service(tmp_path)
    task = service.create_task("Tugas lama")

    task.priority = "Low"
    task.due_date = "2026-10-25"

    result = service.repository.update(task)

    assert result is True

    updated_task = service.list_tasks()[0]
    assert updated_task.priority == "Low"
    assert updated_task.due_date == "2026-10-25"


def test_task_default_priority_and_due_date(tmp_path):
    service = create_test_service(tmp_path)

    task = service.create_task("Tugas tanpa tenggat")

    saved_task = service.list_tasks()[0]

    assert saved_task.priority == "Medium"
    assert saved_task.due_date is None

def test_create_task_rejects_invalid_priority(tmp_path):
    service = create_test_service(tmp_path)

    with pytest.raises(ValueError, match="Prioritas harus Low, Medium, atau High"):
        service.create_task("Tugas baru", priority="Urgent")


def test_create_task_rejects_invalid_due_date(tmp_path):
    service = create_test_service(tmp_path)

    with pytest.raises(ValueError, match="Tanggal tenggat harus valid"):
        service.create_task("Tugas baru", due_date="2026-02-30")


def test_create_task_rejects_wrong_due_date_format(tmp_path):
    service = create_test_service(tmp_path)

    with pytest.raises(ValueError, match="Tanggal tenggat harus"):
        service.create_task("Tugas baru", due_date="20-10-2026")


def test_create_task_accepts_empty_due_date(tmp_path):
    service = create_test_service(tmp_path)

    task = service.create_task("Tugas tanpa tenggat", due_date="")

    assert task.due_date is None


def test_update_task_preserves_priority_and_due_date_when_omitted(
    tmp_path,
):
    task_service = create_test_service(tmp_path)
    task = task_service.create_task(
        "Belajar Python",
        "Mengerjakan latihan",
        "High",
        "2026-10-20",
    )

    result = task_service.update_task(
        task.id,
        "Belajar Python Lanjutan",
        "Mengerjakan proyek",
    )

    assert result is True

    updated_task = next(
        item
        for item in task_service.list_tasks()
        if item.id == task.id
    )

    assert updated_task.title == "Belajar Python Lanjutan"
    assert updated_task.priority == "High"
    assert updated_task.due_date == "2026-10-20"


def test_update_task_can_clear_due_date(tmp_path):
    task_service = create_test_service(tmp_path)
    task = task_service.create_task(
        "Belajar Python",
        priority="High",
        due_date="2026-10-20",
    )

    result = task_service.update_task(
        task.id,
        "Belajar Python",
        priority="High",
        due_date=None,
    )

    assert result is True

    updated_task = next(
        item
        for item in task_service.list_tasks()
        if item.id == task.id
    )

    assert updated_task.due_date is None
