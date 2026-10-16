
from src.task_manager.cli import main
from src.task_manager.database import init_db
from src.task_manager.repository import TaskRepository
from src.task_manager.services import TaskService


def test_cli_add_and_list_task(monkeypatch, capsys, tmp_path):
    # Siapkan database sementara beserta tabelnya.
    db_path = tmp_path / "cli_test.db"
    init_db(db_path)

    repository = TaskRepository(db_path)
    service = TaskService(repository)

    # Simulasikan input pengguna.
    inputs = iter([
        "1",
        "Belajar pytest",
        "Latihan CLI",
        "High",
        "2026-10-20",
        "2",
        "0",
    ])

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": next(inputs),
    )
    monkeypatch.setattr(
        "src.task_manager.cli.TaskService",
        lambda: service,
    )

    main()

    output = capsys.readouterr().out

    assert "Tugas berhasil ditambahkan" in output
    assert "Belajar pytest" in output
    assert "Latihan CLI" in output
    assert "Prioritas: High" in output
    assert "Tenggat: 2026-10-20" in output
    assert "Terima kasih" in output

def test_cli_sort_tasks_by_priority(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "cli_sort_priority.db"
    init_db(db_path)

    repository = TaskRepository(db_path)
    service = TaskService(repository)

    service.create_task("Tugas Low", priority="Low")
    service.create_task("Tugas High", priority="High")
    service.create_task("Tugas Medium", priority="Medium")

    inputs = iter(["8", "1", "0"])

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": next(inputs),
    )
    monkeypatch.setattr(
        "src.task_manager.cli.TaskService",
        lambda: service,
    )

    main()

    output = capsys.readouterr().out

    assert "URUTKAN TUGAS" in output
    assert "Tugas High" in output
    assert "Tugas Medium" in output
    assert "Tugas Low" in output
    assert output.index("Tugas High") < output.index("Tugas Medium")
    assert output.index("Tugas Medium") < output.index("Tugas Low")


def test_cli_sort_tasks_by_due_date(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "cli_sort_due_date.db"
    init_db(db_path)

    repository = TaskRepository(db_path)
    service = TaskService(repository)

    service.create_task("Tanpa tenggat")
    service.create_task("Tenggat kedua", due_date="2026-11-20")
    service.create_task("Tenggat pertama", due_date="2026-10-20")

    inputs = iter(["8", "2", "0"])

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": next(inputs),
    )
    monkeypatch.setattr(
        "src.task_manager.cli.TaskService",
        lambda: service,
    )

    main()

    output = capsys.readouterr().out

    assert "Tenggat pertama" in output
    assert "Tenggat kedua" in output
    assert "Tanpa tenggat" in output
    assert output.index("Tenggat pertama") < output.index("Tenggat kedua")
    assert output.index("Tenggat kedua") < output.index("Tanpa tenggat")


def test_cli_display_task_statistics(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "cli_statistics.db"
    init_db(db_path)

    repository = TaskRepository(db_path)
    service = TaskService(repository)

    task_high = service.create_task("Tugas High", priority="High")
    service.create_task("Tugas Medium", priority="Medium")
    service.create_task("Tugas Low", priority="Low")

    service.complete_task(task_high.id)

    inputs = iter(["9", "0"])

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": next(inputs),
    )
    monkeypatch.setattr(
        "src.task_manager.cli.TaskService",
        lambda: service,
    )

    main()

    output = capsys.readouterr().out

    assert "STATISTIK TUGAS" in output
    assert "Total tugas       : 3" in output
    assert "Tugas selesai     : 1" in output
    assert "Belum selesai     : 2" in output
    assert "Tingkat selesai   : 33.33%" in output
    assert "High              : 1" in output
    assert "Medium            : 1" in output
    assert "Low               : 1" in output
    assert "Terima kasih" in output
