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

    service = TaskService(repository=TaskRepository(db_path=db_path))
    users = UserRepository(db_path=db_path)

    app.dependency_overrides[get_task_service] = lambda: service
    app.dependency_overrides[get_user_repository] = lambda: users

    try:
        with TestClient(app) as test_client:
            test_client.db_path = db_path
            yield test_client
    finally:
        app.dependency_overrides.clear()


def register_and_login(client, username, email):
    response = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "StrongPass123!"},
    )
    assert response.status_code == 201, response.text
    login = client.post(
        "/auth/login", json={"username": username, "password": "StrongPass123!"}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Task Manager API is running"


def test_register_and_login(client):
    register = client.post(
        "/auth/register",
        json={
            "username": "ganno",
            "email": "ganno@example.com",
            "password": "StrongPass123!",
        },
    )
    assert register.status_code == 201
    assert "password_hash" not in register.json()
    login = client.post(
        "/auth/login", json={"username": "ganno", "password": "StrongPass123!"}
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["access_token"]


def test_duplicate_registration_returns_409(client):
    payload = {
        "username": "ganno",
        "email": "ganno@example.com",
        "password": "StrongPass123!",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    payload["email"] = "another@example.com"
    assert client.post("/auth/register", json=payload).status_code == 409


def test_login_rejects_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "username": "ganno",
            "email": "ganno@example.com",
            "password": "StrongPass123!",
        },
    )
    response = client.post(
        "/auth/login", json={"username": "ganno", "password": "WrongPass123!"}
    )
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
    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Belajar FastAPI",
            "description": "REST API",
            "priority": "High",
            "due_date": "2026-10-25",
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["title"] == "Belajar FastAPI"
    assert task["completed"] is False

    listed = client.get("/tasks", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [task["id"]]

    updated = client.put(
        f"/tasks/{task['id']}",
        headers=headers,
        json={
            "title": "Updated task",
            "description": "Edited",
            "priority": "Medium",
            "due_date": None,
        },
    )
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
    assert (
        client.put(
            f"/tasks/{task_id}",
            headers=headers_two,
            json={
                "title": "Hijack",
                "description": "",
                "priority": "High",
                "due_date": None,
            },
        ).status_code
        == 404
    )
    assert (
        client.patch(f"/tasks/{task_id}/complete", headers=headers_two).status_code
        == 404
    )
    assert client.delete(f"/tasks/{task_id}", headers=headers_two).status_code == 404
    assert client.get("/tasks", headers=headers_two).json() == []


def test_patch_task_updates_only_provided_fields(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Belajar FastAPI",
            "description": "REST API",
            "priority": "High",
            "due_date": "2026-11-15",
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()

    response = client.patch(
        f"/tasks/{task['id']}",
        headers=headers,
        json={"title": "Belajar PATCH"},
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["title"] == "Belajar PATCH"
    assert updated["description"] == "REST API"
    assert updated["priority"] == "High"
    assert updated["due_date"] == "2026-11-15"


def test_patch_task_can_clear_due_date(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Tugas bertenggat",
            "description": "Selesaikan tugas",
            "priority": "Medium",
            "due_date": "2026-11-15",
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()

    response = client.patch(
        f"/tasks/{task['id']}",
        headers=headers,
        json={"due_date": None},
    )

    assert response.status_code == 200, response.text
    assert response.json()["due_date"] is None


def test_patch_task_rejects_empty_payload(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Tugas pengujian"},
    )
    assert created.status_code == 201, created.text

    response = client.patch(
        f"/tasks/{created.json()['id']}",
        headers=headers,
        json={},
    )

    assert response.status_code == 422


def test_patch_task_rejects_invalid_priority(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Tugas pengujian"},
    )
    assert created.status_code == 201, created.text

    response = client.patch(
        f"/tasks/{created.json()['id']}",
        headers=headers,
        json={"priority": "Urgent"},
    )

    assert response.status_code == 422


def test_user_cannot_patch_another_users_task(client):
    headers_one = register_and_login(client, "user_one", "one@example.com")
    headers_two = register_and_login(client, "user_two", "two@example.com")

    created = client.post(
        "/tasks",
        headers=headers_one,
        json={"title": "Tugas pribadi"},
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        headers=headers_two,
        json={"title": "Mencoba mengambil alih"},
    )

    assert response.status_code == 404

    original = client.get(f"/tasks/{task_id}", headers=headers_one)
    assert original.status_code == 200
    assert original.json()["title"] == "Tugas pribadi"


def test_create_task_rejects_invalid_priority(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    response = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Invalid priority", "priority": "Urgent"},
    )
    assert response.status_code == 422


def test_create_task_rejects_invalid_due_date(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    response = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Invalid date", "due_date": "25-10-2026"},
    )
    assert response.status_code == 422


def test_patch_task_rejects_whitespace_only_title(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Tugas awal"},
    )
    assert created.status_code == 201, created.text

    task_id = created.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        headers=headers,
        json={"title": "   "},
    )

    assert response.status_code == 422

    original = client.get(f"/tasks/{task_id}", headers=headers)
    assert original.status_code == 200
    assert original.json()["title"] == "Tugas awal"


def test_patch_task_rejects_null_non_nullable_fields(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Tugas awal",
            "description": "Deskripsi awal",
            "priority": "Medium",
        },
    )
    assert created.status_code == 201, created.text

    task_id = created.json()["id"]

    for field in ("title", "description", "priority"):
        response = client.patch(
            f"/tasks/{task_id}",
            headers=headers,
            json={field: None},
        )

        assert response.status_code == 422, (
            f"Field {field!r} seharusnya menolak null: {response.text}"
        )


def test_patch_task_rejects_invalid_due_date(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Tugas awal",
            "due_date": "2026-11-15",
        },
    )
    assert created.status_code == 201, created.text

    task_id = created.json()["id"]

    for invalid_date in ("15-11-2026", "2026-02-30", "2026/11/15"):
        response = client.patch(
            f"/tasks/{task_id}",
            headers=headers,
            json={"due_date": invalid_date},
        )

        assert response.status_code == 422, (
            f"Tanggal {invalid_date!r} seharusnya ditolak: {response.text}"
        )

    original = client.get(f"/tasks/{task_id}", headers=headers)
    assert original.status_code == 200
    assert original.json()["due_date"] == "2026-11-15"


def test_patch_task_returns_404_for_nonexistent_task(client):
    headers = register_and_login(client, "user_one", "one@example.com")

    response = client.patch(
        "/tasks/999999",
        headers=headers,
        json={"title": "Tugas baru"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_patch_task_rejects_unknown_fields(client):
    headers = register_and_login(client, "user_one", "one@example.com")
    created = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Tugas awal"},
    )
    assert created.status_code == 201, created.text

    task_id = created.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        headers=headers,
        json={"titlle": "Judul salah eja"},
    )

    assert response.status_code == 422

    original = client.get(f"/tasks/{task_id}", headers=headers)
    assert original.status_code == 200
    assert original.json()["title"] == "Tugas awal"


def test_list_tasks_supports_pagination(client):
    headers = register_and_login(client, "pagination_user", "pagination@example.com")

    created_ids = []

    for number in range(5):
        response = client.post(
            "/tasks",
            headers=headers,
            json={"title": f"Tugas {number + 1}"},
        )
        assert response.status_code == 201, response.text
        created_ids.append(response.json()["id"])

    first_page = client.get("/tasks?limit=2&offset=0", headers=headers)
    second_page = client.get("/tasks?limit=2&offset=2", headers=headers)
    third_page = client.get("/tasks?limit=2&offset=4", headers=headers)

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert third_page.status_code == 200

    assert [task["id"] for task in first_page.json()] == created_ids[:2]
    assert [task["id"] for task in second_page.json()] == created_ids[2:4]
    assert [task["id"] for task in third_page.json()] == created_ids[4:]


def test_list_tasks_rejects_invalid_pagination_parameters(client):
    headers = register_and_login(client, "pagination_user", "pagination@example.com")

    invalid_params = [
        "limit=0",
        "limit=101",
        "offset=-1",
    ]

    for params in invalid_params:
        response = client.get(f"/tasks?{params}", headers=headers)
        assert response.status_code == 422, (
            f"Parameter {params!r} seharusnya ditolak: {response.text}"
        )


def test_list_tasks_pagination_preserves_user_isolation(client):
    user_one = register_and_login(client, "page_user_one", "page1@example.com")
    user_two = register_and_login(client, "page_user_two", "page2@example.com")

    for number in range(3):
        response = client.post(
            "/tasks",
            headers=user_one,
            json={"title": f"Tugas pengguna pertama {number + 1}"},
        )
        assert response.status_code == 201, response.text

    response = client.post(
        "/tasks",
        headers=user_two,
        json={"title": "Tugas pengguna kedua"},
    )
    assert response.status_code == 201, response.text

    result = client.get("/tasks?limit=10&offset=0", headers=user_two)

    assert result.status_code == 200
    assert len(result.json()) == 1
    assert result.json()[0]["title"] == "Tugas pengguna kedua"


def test_list_tasks_searches_by_title(client):
    headers = register_and_login(client, "search_user", "search@example.com")

    client.post("/tasks", headers=headers, json={"title": "Belajar FastAPI"})
    client.post("/tasks", headers=headers, json={"title": "Membaca Python"})

    response = client.get("/tasks?search=FastAPI", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Belajar FastAPI"


def test_list_tasks_filters_by_completion_status(client):
    headers = register_and_login(client, "status_user", "status@example.com")

    first = client.post(
        "/tasks", headers=headers, json={"title": "Tugas belum selesai"}
    )
    second = client.post("/tasks", headers=headers, json={"title": "Tugas selesai"})

    task_id = second.json()["id"]
    completed = client.patch(f"/tasks/{task_id}/complete", headers=headers)
    assert completed.status_code == 200

    pending_response = client.get("/tasks?completed=false", headers=headers)
    completed_response = client.get("/tasks?completed=true", headers=headers)

    assert [task["id"] for task in pending_response.json()] == [first.json()["id"]]
    assert [task["id"] for task in completed_response.json()] == [second.json()["id"]]


def test_list_tasks_filters_by_priority(client):
    headers = register_and_login(client, "priority_user", "priority@example.com")

    client.post(
        "/tasks",
        headers=headers,
        json={"title": "Tugas penting", "priority": "High"},
    )
    client.post(
        "/tasks",
        headers=headers,
        json={"title": "Tugas biasa", "priority": "Medium"},
    )

    response = client.get("/tasks?priority=High", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Tugas penting"
    assert response.json()[0]["priority"] == "High"


def test_list_tasks_combines_filters_and_pagination(client):
    headers = register_and_login(client, "combined_user", "combined@example.com")

    created_ids = []

    for number in range(3):
        response = client.post(
            "/tasks",
            headers=headers,
            json={
                "title": f"Belajar Python {number + 1}",
                "priority": "High",
            },
        )
        assert response.status_code == 201
        created_ids.append(response.json()["id"])

    client.post(
        "/tasks",
        headers=headers,
        json={"title": "Belajar Java", "priority": "Medium"},
    )

    response = client.get(
        "/tasks?search=Python&completed=false&priority=High&limit=1&offset=1",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == created_ids[1]


def test_list_tasks_rejects_invalid_search_and_priority(client):
    headers = register_and_login(client, "validation_user", "validation@example.com")

    invalid_params = [
        "search=%20%20%20",
        "priority=Urgent",
    ]

    for params in invalid_params:
        response = client.get(f"/tasks?{params}", headers=headers)
        assert response.status_code == 422, (
            f"Parameter {params!r} seharusnya ditolak: {response.text}"
        )


def test_list_tasks_filters_preserve_user_isolation(client):
    user_one = register_and_login(client, "filter_user_one", "filter1@example.com")
    user_two = register_and_login(client, "filter_user_two", "filter2@example.com")

    client.post(
        "/tasks",
        headers=user_one,
        json={"title": "Belajar Python pribadi", "priority": "High"},
    )

    client.post(
        "/tasks",
        headers=user_two,
        json={"title": "Belajar Python pengguna lain", "priority": "High"},
    )

    response = client.get(
        "/tasks?search=Python&priority=High",
        headers=user_two,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Belajar Python pengguna lain"


def test_list_tasks_sorts_by_title_ascending(client):
    headers = register_and_login(client, "sort_title_user", "sorttitle@example.com")

    for title in ["Zebra", "Apel", "Mangga"]:
        client.post("/tasks", headers=headers, json={"title": title})

    response = client.get("/tasks?sort_by=title&sort_order=asc", headers=headers)

    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == [
        "Apel",
        "Mangga",
        "Zebra",
    ]


def test_list_tasks_sorts_by_title_descending(client):
    headers = register_and_login(client, "sort_desc_user", "sortdesc@example.com")

    for title in ["Zebra", "Apel", "Mangga"]:
        client.post("/tasks", headers=headers, json={"title": title})

    response = client.get("/tasks?sort_by=title&sort_order=desc", headers=headers)

    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == [
        "Zebra",
        "Mangga",
        "Apel",
    ]


def test_list_tasks_sorts_by_priority(client):
    headers = register_and_login(
        client, "sort_priority_user", "sortpriority@example.com"
    )

    for title, priority in [
        ("Tugas rendah", "Low"),
        ("Tugas tinggi", "High"),
        ("Tugas sedang", "Medium"),
    ]:
        client.post(
            "/tasks",
            headers=headers,
            json={"title": title, "priority": priority},
        )

    response = client.get("/tasks?sort_by=priority&sort_order=desc", headers=headers)

    assert response.status_code == 200
    assert [task["priority"] for task in response.json()] == [
        "High",
        "Medium",
        "Low",
    ]


def test_list_tasks_sorts_by_id_descending(client):
    headers = register_and_login(client, "sort_id_user", "sortid@example.com")

    created_ids = []

    for number in range(3):
        response = client.post(
            "/tasks",
            headers=headers,
            json={"title": f"Tugas {number + 1}"},
        )
        created_ids.append(response.json()["id"])

    response = client.get("/tasks?sort_by=id&sort_order=desc", headers=headers)

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == list(reversed(created_ids))


def test_list_tasks_sorts_by_created_at(client):
    import sqlite3

    headers = register_and_login(client, "sort_date_user", "sortdate@example.com")

    task_ids = []

    for title in ["Tugas pertama", "Tugas kedua", "Tugas ketiga"]:
        response = client.post(
            "/tasks",
            headers=headers,
            json={"title": title},
        )
        assert response.status_code == 201
        task_ids.append(response.json()["id"])

    # Atur timestamp secara eksplisit agar hasil sorting deterministik.
    with sqlite3.connect(client.db_path) as connection:
        for task_id, timestamp in zip(
            task_ids,
            [
                "2026-01-01 00:00:01",
                "2026-01-01 00:00:02",
                "2026-01-01 00:00:03",
            ],
        ):
            connection.execute(
                "UPDATE tasks SET created_at = ? WHERE id = ?",
                (timestamp, task_id),
            )

    response = client.get(
        "/tasks?sort_by=created_at&sort_order=desc",
        headers=headers,
    )

    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == [
        "Tugas ketiga",
        "Tugas kedua",
        "Tugas pertama",
    ]


def test_list_tasks_combines_sorting_and_pagination(client):
    headers = register_and_login(client, "sort_page_user", "sortpage@example.com")

    for title in ["Zebra", "Apel", "Mangga", "Durian"]:
        client.post("/tasks", headers=headers, json={"title": title})

    response = client.get(
        "/tasks?sort_by=title&sort_order=asc&limit=2&offset=1",
        headers=headers,
    )

    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == ["Durian", "Mangga"]


def test_list_tasks_rejects_invalid_sorting_parameters(client):
    headers = register_and_login(client, "sort_invalid_user", "sortinvalid@example.com")

    invalid_params = [
        "sort_by=unknown",
        "sort_by=password",
        "sort_order=random",
    ]

    for params in invalid_params:
        response = client.get(f"/tasks?{params}", headers=headers)

        assert response.status_code == 422, (
            f"Parameter {params!r} seharusnya ditolak: {response.text}"
        )


def test_list_tasks_filters_by_due_date_range(client):
    headers = register_and_login(client, "deadline_api_user", "deadlineapi@example.com")

    tasks = [
        ("Sebelum rentang", "2026-11-03"),
        ("Dalam rentang", "2026-11-06"),
        ("Setelah rentang", "2026-11-12"),
        ("Tanpa deadline", None),
    ]

    for title, due_date in tasks:
        response = client.post(
            "/tasks",
            headers=headers,
            json={"title": title, "due_date": due_date},
        )
        assert response.status_code == 201, response.text

    response = client.get(
        "/tasks?due_from=2026-11-04&due_to=2026-11-10",
        headers=headers,
    )

    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == ["Dalam rentang"]


def test_list_tasks_rejects_invalid_due_date(client):
    headers = register_and_login(
        client, "invalid_deadline_user", "invaliddeadline@example.com"
    )

    for params in [
        "due_from=04-11-2026",
        "due_to=2026-02-30",
        "due_from=2026/11/04",
    ]:
        response = client.get(f"/tasks?{params}", headers=headers)
        assert response.status_code == 422


def test_list_tasks_rejects_reversed_due_date_range(client):
    headers = register_and_login(
        client, "reversed_deadline_user", "reverseddeadline@example.com"
    )

    response = client.get(
        "/tasks?due_from=2026-11-10&due_to=2026-11-04",
        headers=headers,
    )

    assert response.status_code == 422


def test_list_tasks_sorts_by_due_date_ascending(client):
    headers = register_and_login(client, "sort_due_asc_user", "sortdueasc@example.com")
    client.post(
        "/tasks",
        json={"title": "Tanpa deadline"},
        headers=headers,
    )
    client.post(
        "/tasks",
        json={"title": "Deadline jauh", "due_date": "2026-11-10"},
        headers=headers,
    )
    client.post(
        "/tasks",
        json={"title": "Deadline dekat", "due_date": "2026-11-05"},
        headers=headers,
    )

    response = client.get(
        "/tasks?sort_by=due_date&sort_order=asc",
        headers=headers,
    )

    assert response.status_code == 200
    titles = [task["title"] for task in response.json()]
    assert titles == [
        "Deadline dekat",
        "Deadline jauh",
        "Tanpa deadline",
    ]


def test_list_tasks_sorts_by_due_date_descending(client):
    headers = register_and_login(
        client, "sort_due_desc_user", "sortduedesc@example.com"
    )
    client.post(
        "/tasks",
        json={"title": "Tanpa deadline"},
        headers=headers,
    )
    client.post(
        "/tasks",
        json={"title": "Deadline dekat", "due_date": "2026-11-05"},
        headers=headers,
    )
    client.post(
        "/tasks",
        json={"title": "Deadline jauh", "due_date": "2026-11-10"},
        headers=headers,
    )

    response = client.get(
        "/tasks?sort_by=due_date&sort_order=desc",
        headers=headers,
    )

    assert response.status_code == 200
    titles = [task["title"] for task in response.json()]
    assert titles == [
        "Deadline jauh",
        "Deadline dekat",
        "Tanpa deadline",
    ]


def test_api_returns_correct_deadline_status(client):
    headers = register_and_login(
        client,
        "deadline_status_user",
        "deadlinestatus@example.com",
    )

    today = datetime.now().date()
    upcoming_date = (today + timedelta(days=3)).isoformat()
    future_date = (today + timedelta(days=10)).isoformat()

    # POST: Membuat tugas dengan deadline mendatang.
    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Menyelesaikan proyek",
            "due_date": upcoming_date,
        },
    )

    assert created.status_code == 201
    task = created.json()
    task_id = task["id"]
    assert task["deadline_status"] == "Upcoming"

    # GET list: Memastikan status tersedia pada daftar tugas.
    listed = client.get("/tasks", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["deadline_status"] == "Upcoming"

    # GET detail: Memastikan status tersedia pada detail tugas.
    detail = client.get(f"/tasks/{task_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["deadline_status"] == "Upcoming"

    # PUT: Mengubah deadline menjadi lebih dari 7 hari.
    updated = client.put(
        f"/tasks/{task_id}",
        headers=headers,
        json={
            "title": "Menyelesaikan proyek",
            "description": "",
            "priority": "Medium",
            "due_date": future_date,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["deadline_status"] == "Future"

    # PATCH: Menghapus deadline.
    patched = client.patch(
        f"/tasks/{task_id}",
        headers=headers,
        json={"due_date": None},
    )

    assert patched.status_code == 200
    assert patched.json()["deadline_status"] == "No Deadline"

    # PATCH complete: Status Completed harus menjadi prioritas.
    completed = client.patch(
        f"/tasks/{task_id}/complete",
        headers=headers,
    )

    assert completed.status_code == 200
    assert completed.json()["deadline_status"] == "Completed"


def test_task_statistics_returns_correct_distribution(client):
    headers = register_and_login(client, "statistics_user", "statistics@example.com")

    today = datetime.now().date()

    tasks = [
        ("Tugas overdue", "Low", (today - timedelta(days=1)).isoformat()),
        ("Tugas hari ini", "Medium", today.isoformat()),
        ("Tugas upcoming", "High", (today + timedelta(days=3)).isoformat()),
        ("Tugas future", "High", (today + timedelta(days=10)).isoformat()),
        ("Tanpa deadline", "Low", None),
        ("Tugas selesai", "Medium", (today - timedelta(days=2)).isoformat()),
    ]

    task_ids = []

    for title, priority, due_date in tasks:
        response = client.post(
            "/tasks",
            headers=headers,
            json={
                "title": title,
                "priority": priority,
                "due_date": due_date,
            },
        )
        assert response.status_code == 201, response.text
        task_ids.append(response.json()["id"])

    # Selesaikan satu tugas yang sebelumnya overdue.
    completed = client.patch(
        f"/tasks/{task_ids[5]}/complete",
        headers=headers,
    )
    assert completed.status_code == 200

    response = client.get("/tasks/statistics", headers=headers)

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total_tasks"] == 6
    assert data["completed_tasks"] == 1
    assert data["pending_tasks"] == 5
    assert data["completion_rate"] == 16.67

    assert data["priority_distribution"] == {
        "low": 2,
        "medium": 2,
        "high": 2,
    }

    assert data["deadline_distribution"] == {
        "overdue": 1,
        "due_today": 1,
        "upcoming": 1,
        "future": 1,
        "no_deadline": 1,
        "completed": 1,
    }


def test_task_statistics_counts_all_tasks_without_pagination(client):
    headers = register_and_login(
        client, "statistics_page_user", "statisticspage@example.com"
    )

    for number in range(25):
        response = client.post(
            "/tasks",
            headers=headers,
            json={"title": f"Tugas {number + 1}"},
        )
        assert response.status_code == 201, response.text

    response = client.get("/tasks/statistics", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["total_tasks"] == 25
    assert response.json()["pending_tasks"] == 25
    assert response.json()["completed_tasks"] == 0


def test_task_statistics_preserves_user_isolation(client):
    user_one = register_and_login(
        client, "statistics_user_one", "statistics1@example.com"
    )
    user_two = register_and_login(
        client, "statistics_user_two", "statistics2@example.com"
    )

    for number in range(3):
        response = client.post(
            "/tasks",
            headers=user_one,
            json={"title": f"Tugas pengguna pertama {number + 1}"},
        )
        assert response.status_code == 201, response.text

    response = client.post(
        "/tasks",
        headers=user_two,
        json={"title": "Tugas pengguna kedua"},
    )
    assert response.status_code == 201, response.text

    statistics_one = client.get("/tasks/statistics", headers=user_one)
    statistics_two = client.get("/tasks/statistics", headers=user_two)

    assert statistics_one.status_code == 200
    assert statistics_two.status_code == 200

    assert statistics_one.json()["total_tasks"] == 3
    assert statistics_two.json()["total_tasks"] == 1


def test_task_statistics_returns_zero_for_empty_user(client):
    headers = register_and_login(
        client, "empty_statistics_user", "empty_statistics@example.com"
    )

    response = client.get("/tasks/statistics", headers=headers)

    assert response.status_code == 200, response.text

    assert response.json() == {
        "total_tasks": 0,
        "completed_tasks": 0,
        "pending_tasks": 0,
        "completion_rate": 0.0,
        "priority_distribution": {
            "low": 0,
            "medium": 0,
            "high": 0,
        },
        "deadline_distribution": {
            "overdue": 0,
            "due_today": 0,
            "upcoming": 0,
            "future": 0,
            "no_deadline": 0,
            "completed": 0,
        },
    }


def test_task_statistics_requires_authentication(client):
    response = client.get("/tasks/statistics")

    assert response.status_code == 401


def test_task_dashboard_returns_correct_summary_and_deadline_overview(client):
    headers = register_and_login(client, "dashboard_user", "dashboard@example.com")

    today = datetime.now().date()

    tasks = [
        ("Tugas overdue", "Low", (today - timedelta(days=1)).isoformat()),
        ("Tugas hari ini", "Medium", today.isoformat()),
        ("Tugas upcoming", "High", (today + timedelta(days=3)).isoformat()),
        ("Tugas future", "High", (today + timedelta(days=10)).isoformat()),
        ("Tanpa deadline", "Low", None),
        ("Tugas selesai", "Medium", (today - timedelta(days=2)).isoformat()),
    ]

    task_ids = []

    for title, priority, due_date in tasks:
        response = client.post(
            "/tasks",
            headers=headers,
            json={
                "title": title,
                "priority": priority,
                "due_date": due_date,
            },
        )
        assert response.status_code == 201, response.text
        task_ids.append(response.json()["id"])

    completed = client.patch(
        f"/tasks/{task_ids[5]}/complete",
        headers=headers,
    )
    assert completed.status_code == 200

    response = client.get("/tasks/dashboard", headers=headers)

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["summary"] == {
        "total_tasks": 6,
        "completed_tasks": 1,
        "pending_tasks": 5,
        "completion_rate": 16.67,
    }

    assert data["deadline_overview"] == {
        "overdue": 1,
        "due_today": 1,
        "upcoming": 1,
        "future": 1,
        "no_deadline": 1,
        "completed": 1,
    }


def test_task_dashboard_limits_and_sorts_task_lists(client):
    headers = register_and_login(
        client, "dashboard_sort_user", "dashboardsort@example.com"
    )

    today = datetime.now().date()

    tasks = [
        ("High tanpa deadline", "High", None),
        ("High deadline 5", "High", (today + timedelta(days=5)).isoformat()),
        ("High deadline 2", "High", (today + timedelta(days=2)).isoformat()),
        ("High deadline 1", "High", (today + timedelta(days=1)).isoformat()),
        ("High deadline 4", "High", (today + timedelta(days=4)).isoformat()),
        ("High deadline 3", "High", (today + timedelta(days=3)).isoformat()),
        ("Medium deadline 1", "Medium", (today + timedelta(days=1)).isoformat()),
        ("Overdue High", "High", (today - timedelta(days=1)).isoformat()),
    ]

    for title, priority, due_date in tasks:
        response = client.post(
            "/tasks",
            headers=headers,
            json={
                "title": title,
                "priority": priority,
                "due_date": due_date,
            },
        )
        assert response.status_code == 201, response.text

    response = client.get("/tasks/dashboard", headers=headers)

    assert response.status_code == 200, response.text

    data = response.json()

    priority_tasks = data["priority_tasks"]
    upcoming_deadlines = data["upcoming_deadlines"]

    assert len(priority_tasks) == 5
    assert [task["title"] for task in priority_tasks] == [
        "Overdue High",
        "High deadline 1",
        "High deadline 2",
        "High deadline 3",
        "High deadline 4",
    ]

    assert len(upcoming_deadlines) == 5
    assert [task["title"] for task in upcoming_deadlines] == [
        "High deadline 1",
        "Medium deadline 1",
        "High deadline 2",
        "High deadline 3",
        "High deadline 4",
    ]


def test_task_dashboard_preserves_user_isolation(client):
    user_one = register_and_login(
        client, "dashboard_user_one", "dashboard1@example.com"
    )
    user_two = register_and_login(
        client, "dashboard_user_two", "dashboard2@example.com"
    )

    for number in range(3):
        response = client.post(
            "/tasks",
            headers=user_one,
            json={"title": f"Tugas pengguna pertama {number + 1}"},
        )
        assert response.status_code == 201, response.text

    response = client.post(
        "/tasks",
        headers=user_two,
        json={"title": "Tugas pengguna kedua"},
    )
    assert response.status_code == 201, response.text

    dashboard_one = client.get("/tasks/dashboard", headers=user_one)
    dashboard_two = client.get("/tasks/dashboard", headers=user_two)

    assert dashboard_one.status_code == 200
    assert dashboard_two.status_code == 200

    assert dashboard_one.json()["summary"]["total_tasks"] == 3
    assert dashboard_two.json()["summary"]["total_tasks"] == 1


def test_task_dashboard_requires_authentication(client):
    response = client.get("/tasks/dashboard")

    assert response.status_code == 401
