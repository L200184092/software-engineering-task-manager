import pytest

from src.task_manager.csv_handler import export_tasks, read_tasks
from src.task_manager.models import Task


def test_export_and_read_tasks_round_trip(tmp_path):
    csv_path = tmp_path / "tasks.csv"

    original_tasks = [
        Task(
            title="Belajar Python",
            description="Belajar CSV, termasuk koma,",
            completed=False,
            priority="High",
            due_date="2026-11-01",
        ),
        Task(
            title="Selesai laporan",
            description="Laporan sudah selesai",
            completed=True,
            priority="Medium",
            due_date=None,
        ),
    ]

    exported_count = export_tasks(original_tasks, csv_path)
    imported_tasks = read_tasks(csv_path)

    assert exported_count == 2
    assert len(imported_tasks) == 2

    for original, imported in zip(original_tasks, imported_tasks):
        assert imported.title == original.title
        assert imported.description == original.description
        assert imported.completed == original.completed
        assert imported.priority == original.priority
        assert imported.due_date == original.due_date


def test_export_empty_tasks(tmp_path):
    csv_path = tmp_path / "empty.csv"

    exported_count = export_tasks([], csv_path)

    assert exported_count == 0
    assert read_tasks(csv_path) == []


def test_read_tasks_rejects_empty_title(tmp_path):
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text(
        "title,description,completed,priority,due_date\n,Deskripsi,false,Medium,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Judul tugas"):
        read_tasks(csv_path)


def test_read_tasks_rejects_invalid_status(tmp_path):
    csv_path = tmp_path / "invalid_status.csv"
    csv_path.write_text(
        "title,description,completed,priority,due_date\nTugas,Deskripsi,yes,Medium,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Status"):
        read_tasks(csv_path)


def test_read_tasks_rejects_invalid_priority(tmp_path):
    csv_path = tmp_path / "invalid_priority.csv"
    csv_path.write_text(
        "title,description,completed,priority,due_date\n"
        "Tugas,Deskripsi,false,Urgent,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Prioritas"):
        read_tasks(csv_path)


def test_read_tasks_rejects_invalid_header(tmp_path):
    csv_path = tmp_path / "invalid_header.csv"
    csv_path.write_text(
        "title,description\nTugas,Deskripsi\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Header CSV"):
        read_tasks(csv_path)


def test_read_tasks_rejects_invalid_due_date(tmp_path):
    csv_path = tmp_path / "invalid_date.csv"
    csv_path.write_text(
        "title,description,completed,priority,due_date\n"
        "Tugas,Deskripsi,false,Medium,2026-02-30\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Tanggal tenggat"):
        read_tasks(csv_path)


def test_read_tasks_accepts_empty_due_date(tmp_path):
    csv_path = tmp_path / "empty_date.csv"
    csv_path.write_text(
        "title,description,completed,priority,due_date\n"
        "Tugas,Deskripsi,false,Medium,\n",
        encoding="utf-8",
    )

    tasks = read_tasks(csv_path)

    assert len(tasks) == 1
    assert tasks[0].due_date is None
