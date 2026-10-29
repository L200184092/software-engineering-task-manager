
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

    service.create_task("Tugas tanpa tenggat")

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


def test_search_tasks_by_title(tmp_path):
    service = create_test_service(tmp_path)
    service.create_task("Belajar Python", "Latihan coding")
    service.create_task("Belajar SQL", "Latihan database")

    results = service.search_tasks("python")

    assert len(results) == 1
    assert results[0].title == "Belajar Python"


def test_search_tasks_by_description(tmp_path):
    service = create_test_service(tmp_path)
    service.create_task("Tugas pertama", "Belajar machine learning")
    service.create_task("Tugas kedua", "Belajar database")

    results = service.search_tasks("MACHINE LEARNING")

    assert len(results) == 1
    assert results[0].title == "Tugas pertama"


def test_filter_tasks_by_priority(tmp_path):
    service = create_test_service(tmp_path)
    service.create_task("Tugas A", priority="High")
    service.create_task("Tugas B", priority="Low")
    service.create_task("Tugas C", priority="High")

    results = service.filter_tasks(priority="High")

    assert len(results) == 2
    assert all(task.priority == "High" for task in results)


def test_filter_tasks_by_status_and_priority(tmp_path):
    service = create_test_service(tmp_path)
    task_a = service.create_task("Tugas A", priority="High")
    service.create_task("Tugas B", priority="High")
    service.create_task("Tugas C", priority="Low")

    service.complete_task(task_a.id)

    results = service.filter_tasks(
        completed=False,
        priority="High",
    )

    assert len(results) == 1
    assert results[0].title == "Tugas B"
    assert results[0].completed is False


def test_sort_tasks_by_priority(tmp_path):
    service = create_test_service(tmp_path)
    service.create_task("Tugas Low", priority="Low")
    service.create_task("Tugas High", priority="High")
    service.create_task("Tugas Medium", priority="Medium")

    results = service.sort_tasks("priority")

    assert [task.priority for task in results] == [
        "High",
        "Medium",
        "Low",
    ]


def test_sort_tasks_by_due_date_puts_missing_dates_last(tmp_path):
    service = create_test_service(tmp_path)
    service.create_task("Tanpa tenggat")
    service.create_task("Tenggat kedua", due_date="2026-11-20")
    service.create_task("Tenggat pertama", due_date="2026-10-20")

    results = service.sort_tasks("due_date")

    assert [task.title for task in results] == [
        "Tenggat pertama",
        "Tenggat kedua",
        "Tanpa tenggat",
    ]



def test_get_task_statistics(tmp_path):
    service = create_test_service(tmp_path)

    task_high = service.create_task("Tugas High", priority="High")
    service.create_task("Tugas Medium", priority="Medium")
    service.create_task("Tugas Low", priority="Low")

    service.complete_task(task_high.id)

    stats = service.get_task_statistics()

    assert stats["total"] == 3
    assert stats["completed"] == 1
    assert stats["pending"] == 2
    assert stats["completion_rate"] == 33.33
    assert stats["priority_counts"] == {
        "High": 1,
        "Medium": 1,
        "Low": 1,
    }


def test_get_task_statistics_with_no_tasks(tmp_path):
    service = create_test_service(tmp_path)

    stats = service.get_task_statistics()

    assert stats["total"] == 0
    assert stats["completed"] == 0
    assert stats["pending"] == 0
    assert stats["completion_rate"] == 0.0
    assert stats["priority_counts"] == {
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }


def test_get_task_statistics_when_all_tasks_completed(tmp_path):
    service = create_test_service(tmp_path)

    task_one = service.create_task("Tugas 1")
    task_two = service.create_task("Tugas 2")

    service.complete_task(task_one.id)
    service.complete_task(task_two.id)

    stats = service.get_task_statistics()

    assert stats["total"] == 2
    assert stats["completed"] == 2
    assert stats["pending"] == 0
    assert stats["completion_rate"] == 100.0


def test_export_tasks_to_csv(tmp_path):
    service = create_test_service(tmp_path)
    service.create_task(
        "Belajar Python",
        "Mempelajari CSV",
        "High",
        "2026-11-01",
    )

    csv_path = tmp_path / "export.csv"
    count = service.export_tasks_to_csv(csv_path)

    assert count == 1
    assert csv_path.exists()


def test_import_tasks_from_csv(tmp_path):
    service = create_test_service(tmp_path)
    csv_path = tmp_path / "import.csv"

    csv_path.write_text(
        "title,description,completed,priority,due_date\n"
        "Belajar Python,Mempelajari CSV,false,High,2026-11-01\n"
        "Laporan,Sudah selesai,true,Medium,\n",
        encoding="utf-8",
    )

    count = service.import_tasks_from_csv(csv_path)
    tasks = service.list_tasks()

    assert count == 2
    assert len(tasks) == 2
    assert tasks[0].title == "Belajar Python"
    assert tasks[0].priority == "High"
    assert tasks[0].due_date == "2026-11-01"
    assert tasks[1].completed is True


def test_import_invalid_csv_does_not_save_tasks(tmp_path):
    service = create_test_service(tmp_path)
    csv_path = tmp_path / "invalid.csv"

    csv_path.write_text(
        "title,description,completed,priority,due_date\n"
        "Tugas valid,Deskripsi,false,High,\n"
        "Tugas tidak valid,Deskripsi,yes,Medium,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Status"):
        service.import_tasks_from_csv(csv_path)

    assert service.list_tasks() == []
