
import pytest
from fastapi.testclient import TestClient

from task_manager.api import app, get_task_service
from task_manager.repository import TaskRepository
from task_manager.services import TaskService
from task_manager.database import init_db



@pytest.fixture
def client(tmp_path):
    """Membuat API client dengan database sementara."""
    db_path = tmp_path / "test_tasks.db"

    # Buat tabel tasks di database khusus pengujian.
    init_db(db_path)

    service = TaskService(
        repository=TaskRepository(db_path=str(db_path))
    )

    app.dependency_overrides[get_task_service] = lambda: service

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Task Manager API is running"


def test_create_and_list_tasks(client):
    create_response = client.post(
        "/tasks",
        json={
            "title": "Belajar FastAPI",
            "description": "Membuat REST API",
            "priority": "High",
            "due_date": "2026-10-25",
        },
    )

    assert create_response.status_code == 201
    task = create_response.json()
    assert task["title"] == "Belajar FastAPI"
    assert task["priority"] == "High"
    assert task["completed"] is False

    list_response = client.get("/tasks")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == task["id"]


def test_get_nonexistent_task_returns_404(client):
    response = client.get("/tasks/9999")

    assert response.status_code == 404


def test_update_complete_and_delete_task(client):
    create_response = client.post(
        "/tasks",
        json={"title": "Tugas awal"},
    )
    task_id = create_response.json()["id"]

    update_response = client.put(
        f"/tasks/{task_id}",
        json={
            "title": "Tugas diperbarui",
            "description": "Sudah diedit",
            "priority": "High",
            "due_date": None,
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Tugas diperbarui"

    complete_response = client.patch(
        f"/tasks/{task_id}/complete"
    )

    assert complete_response.status_code == 200
    assert complete_response.json()["completed"] is True

    delete_response = client.delete(f"/tasks/{task_id}")

    assert delete_response.status_code == 204

    missing_response = client.get(f"/tasks/{task_id}")
    assert missing_response.status_code == 404


def test_create_task_rejects_invalid_priority(client):
    response = client.post(
        "/tasks",
        json={
            "title": "Tugas invalid",
            "priority": "Urgent",
        },
    )

    assert response.status_code == 422


def test_create_task_rejects_invalid_due_date(client):
    response = client.post(
        "/tasks",
        json={
            "title": "Tugas dengan tanggal invalid",
            "due_date": "25-10-2026",
        },
    )

    assert response.status_code == 422
