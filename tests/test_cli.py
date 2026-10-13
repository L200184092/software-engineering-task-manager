
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
    assert "Terima kasih" in output
