from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from task_manager.api import app, get_task_service, get_user_repository, limiter
from task_manager.database import init_db
from task_manager.repository import TaskRepository
from task_manager.services import TaskService
from task_manager.user_repository import UserRepository


@pytest.fixture
def client(tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_tasks.db"
    init_db(db_path)

    service = TaskService(
        repository=TaskRepository(db_path=db_path)
    )
    users = UserRepository(db_path=db_path)

    app.dependency_overrides[get_task_service] = lambda: service
    app.dependency_overrides[get_user_repository] = lambda: users

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def register_and_login(client, username, email):
    response = client.post("/auth/register", json={
        "username": username, "email": email, "password": "StrongPass123!"
    })
    assert response.status_code == 201, response.text
    login = client.post("/auth/login", json={
        "username": username, "password": "StrongPass123!"
    })
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Task Manager API is running"


def test_register_and_login(client):
    register = client.post("/auth/register", json={
        "username": "ganno", "email": "ganno@example.com", "password": "StrongPass123!"
    })
    assert register.status_code == 201
    assert "password_hash" not in register.json()
    login = client.post("/auth/login", json={
        "username": "ganno", "password": "StrongPass123!"
    })
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["access_token"]


def test_duplicate_registration_returns_409(client):
    payload = {"username": "ganno", "email": "ganno@example.com", "password": "StrongPass123!"}
    assert client.post("/auth/register", json=payload).status_code == 201
    payload["email"] = "another@example.com"
    assert client.post("/auth/register", json=payload).status_code == 409


def test_login_rejects_wrong_password(client):
    client.post("/auth/register", json={
        "username": "ganno", "email": "ganno@example.com", "password": "StrongPass123!"
    })
    response = client.post("/auth/login", json={"username": "ganno", "password": "WrongPass123!"})
    assert response.status_code == 401

def test_login_rate_limit(client):
    payload = {
        "username": "unknown_user",
        "password": "WrongPass123!",
    }

    # Lima permintaan pertama harus diproses.
    for _ in range(5):
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401, response.text

    # Permintaan keenam harus dibatasi.
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 429, response.text

def test_tasks_require_authentication(client):
    for method, url in [
        ("get", "/tasks"),
        ("post", "/tasks"),
        ("get", "/tasks/1"),
        ("put", "/tasks/1"),
        ("patch", "/tasks/1/complete"),
        ("delete", "/tasks/1"),
    ]:
        if method in {"post", "put"}:
            response = getattr(client, method)(url, json={})
        else:
            response = getattr(client, method)(url)
        assert response.status_code == 401, (method, url, response.text)

def test_tasks_reject_expired_token(client):
    from datetime import datetime, timedelta

    import jwt

    from task_manager.auth import JWT_ALGORITHM, get_secret_key

    expired_at = datetime.now(UTC) - timedelta(minutes=5)
    token = jwt.encode(
        {
            "sub": "1",
            "iat": expired_at - timedelta(minutes=30),
            "exp": expired_at,
        },
        get_secret_key(),
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_tasks_reject_invalid_signature(client):
    import jwt

    from task_manager.auth import JWT_ALGORITHM

    token = jwt.encode(
        {
            "sub": "1",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        "invalid-test-secret-key-at-least-32-bytes",
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_tasks_reject_token_missing_required_claim(client):
    from datetime import datetime

    import jwt

    from task_manager.auth import JWT_ALGORITHM, get_secret_key

    token = jwt.encode(
        {
            "sub": "1",
            "iat": datetime.now(UTC),
        },
        get_secret_key(),
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401

def test_tasks_reject_token_issued_in_future(client):
    import jwt

    from task_manager.auth import JWT_ALGORITHM, get_secret_key

    future_iat = datetime.now(UTC) + timedelta(hours=1)

    token = jwt.encode(
        {
            "sub": "1",
            "iat": future_iat,
            "exp": future_iat + timedelta(minutes=30),
        },
        get_secret_key(),
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401

def test_tasks_reject_nonexistent_user_token(client):
    from task_manager.auth import create_access_token

    token = create_access_token("999999999")

    response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401

def test_crud_tasks_with_authentication(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post("/tasks", headers=headers, json={
        "title": "Belajar FastAPI", "description": "REST API", "priority": "High",
        "due_date": "2026-10-25",
    })
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["title"] == "Belajar FastAPI"
    assert task["completed"] is False

    listed = client.get("/tasks", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [task["id"]]

    updated = client.put(f"/tasks/{task['id']}", headers=headers, json={
        "title": "Updated task", "description": "Edited", "priority": "Medium",
        "due_date": None,
    })
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated task"

    completed = client.patch(f"/tasks/{task['id']}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["completed"] is True

    deleted = client.delete(f"/tasks/{task['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/tasks/{task['id']}", headers=headers).status_code == 404


def test_user_cannot_access_another_users_task(client):
    headers_one = register_and_login(client, "user_one", "one@example.com")
    headers_two = register_and_login(client, "user_two", "two@example.com")
    created = client.post("/tasks", headers=headers_one, json={"title": "Private task"})
    task_id = created.json()["id"]

    assert client.get(f"/tasks/{task_id}", headers=headers_two).status_code == 404
    assert client.put(f"/tasks/{task_id}", headers=headers_two, json={
        "title": "Hijack", "description": "", "priority": "High", "due_date": None
    }).status_code == 404
    assert client.patch(f"/tasks/{task_id}/complete", headers=headers_two).status_code == 404
    assert client.delete(f"/tasks/{task_id}", headers=headers_two).status_code == 404
    assert client.get("/tasks", headers=headers_two).json() == []


def test_create_task_rejects_invalid_priority(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    response = client.post("/tasks", headers=headers, json={
        "title": "Invalid priority", "priority": "Urgent"
    })
    assert response.status_code == 422


def test_create_task_rejects_invalid_due_date(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    response = client.post("/tasks", headers=headers, json={
        "title": "Invalid date", "due_date": "25-10-2026"
    })
    assert response.status_code == 422
