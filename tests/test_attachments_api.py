from io import BytesIO

from fastapi.testclient import TestClient


def register_and_login(client: TestClient, username: str, email: str) -> dict[str, str]:
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


def create_task(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post("/tasks", headers=headers, json={"title": "Attachment task"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_upload_list_download_and_delete_attachment(client):
    headers = register_and_login(client, "file_owner", "fileowner@example.com")
    task_id = create_task(client, headers)
    payload = b"%PDF-1.7\\nSample PDF content"

    uploaded = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": ("report.pdf", BytesIO(payload), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    item = uploaded.json()
    assert item["filename"] == "report.pdf"
    assert item["content_type"] == "application/pdf"
    assert item["size"] == len(payload)

    listed = client.get(f"/tasks/{task_id}/attachments", headers=headers)
    assert listed.status_code == 200
    assert [attachment["id"] for attachment in listed.json()] == [item["id"]]

    downloaded = client.get(
        f"/tasks/{task_id}/attachments/{item['id']}/download", headers=headers
    )
    assert downloaded.status_code == 200
    assert downloaded.content == payload
    assert "report.pdf" in downloaded.headers["content-disposition"]

    deleted = client.delete(
        f"/tasks/{task_id}/attachments/{item['id']}", headers=headers
    )
    assert deleted.status_code == 204
    assert client.get(f"/tasks/{task_id}/attachments", headers=headers).json() == []
    assert (
        client.get(
            f"/tasks/{task_id}/attachments/{item['id']}/download", headers=headers
        ).status_code
        == 404
    )


def test_attachment_validation_rejects_unsupported_and_mismatched_files(client):
    headers = register_and_login(
        client, "file_validation", "filevalidation@example.com"
    )
    task_id = create_task(client, headers)

    unsupported = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": ("script.exe", b"MZ executable", "application/octet-stream")},
    )
    assert unsupported.status_code == 415

    mismatched = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": ("fake.pdf", b"not a PDF", "application/pdf")},
    )
    assert mismatched.status_code == 415

    oversized = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={
            "file": (
                "large.pdf",
                b"%PDF-" + (b"x" * (5 * 1024 * 1024)),
                "application/pdf",
            )
        },
    )
    assert oversized.status_code == 413


def test_attachment_access_is_isolated_between_users(client):
    owner = register_and_login(
        client, "file_private_owner", "fileprivateowner@example.com"
    )
    other = register_and_login(
        client, "file_private_other", "fileprivateother@example.com"
    )
    task_id = create_task(client, owner)
    uploaded = client.post(
        f"/tasks/{task_id}/attachments",
        headers=owner,
        files={"file": ("private.pdf", b"%PDF-1.4 private", "application/pdf")},
    )
    assert uploaded.status_code == 201
    attachment_id = uploaded.json()["id"]

    assert client.get(f"/tasks/{task_id}/attachments", headers=other).status_code == 404
    assert (
        client.get(
            f"/tasks/{task_id}/attachments/{attachment_id}/download", headers=other
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/tasks/{task_id}/attachments/{attachment_id}", headers=other
        ).status_code
        == 404
    )


def test_deleting_task_removes_attachment_file(client):
    headers = register_and_login(client, "file_cleanup", "filecleanup@example.com")
    task_id = create_task(client, headers)
    uploaded = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": ("cleanup.pdf", b"%PDF-1.4 cleanup", "application/pdf")},
    )
    assert uploaded.status_code == 201

    storage_dir = client.db_path.parent / "attachments"
    assert len(list(storage_dir.iterdir())) == 1
    deleted = client.delete(f"/tasks/{task_id}", headers=headers)
    assert deleted.status_code == 204
    assert list(storage_dir.iterdir()) == []
