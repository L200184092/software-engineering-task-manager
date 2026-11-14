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


def test_tag_crud_assignment_and_filtering(client):
    headers = register_and_login(client, "tag_user", "tag@example.com")
    first = client.post("/tasks", headers=headers, json={"title": "Task with tags"})
    second = client.post("/tasks", headers=headers, json={"title": "Task without tags"})
    assert first.status_code == second.status_code == 201

    work = client.post("/tags", headers=headers, json={"name": " Work "})
    urgent = client.post("/tags", headers=headers, json={"name": "Urgent"})
    assert work.status_code == urgent.status_code == 201
    assert work.json()["name"] == "Work"

    assigned = client.put(
        f"/tasks/{first.json()['id']}/tags",
        headers=headers,
        json={"tag_ids": [work.json()["id"], urgent.json()["id"]]},
    )
    assert assigned.status_code == 200
    assert {tag["name"] for tag in assigned.json()} == {"Work", "Urgent"}

    listed = client.get(f"/tasks/{first.json()['id']}/tags", headers=headers)
    assert {tag["name"] for tag in listed.json()} == {"Work", "Urgent"}

    filtered = client.get(f"/tasks?tag_id={work.json()['id']}", headers=headers)
    assert [task["id"] for task in filtered.json()] == [first.json()["id"]]

    removed = client.put(
        f"/tasks/{first.json()['id']}/tags",
        headers=headers,
        json={"tag_ids": []},
    )
    assert removed.status_code == 200
    assert removed.json() == []


def test_tags_reject_duplicates_and_support_update_delete(client):
    headers = register_and_login(client, "tag_crud", "tagcrud@example.com")
    created = client.post("/tags", headers=headers, json={"name": "Research"})
    assert created.status_code == 201
    assert (
        client.post("/tags", headers=headers, json={"name": "research"}).status_code
        == 409
    )
    updated = client.patch(
        f"/tags/{created.json()['id']}", headers=headers, json={"name": "Academic"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Academic"
    assert (
        client.delete(f"/tags/{created.json()['id']}", headers=headers).status_code
        == 204
    )


def test_tags_preserve_user_isolation(client):
    user_one = register_and_login(client, "tag_owner", "tagowner@example.com")
    user_two = register_and_login(client, "tag_other", "tagother@example.com")
    task = client.post("/tasks", headers=user_one, json={"title": "Private task"})
    tag = client.post("/tags", headers=user_one, json={"name": "Private"})
    task_id = task.json()["id"]
    tag_id = tag.json()["id"]

    assert client.get("/tags", headers=user_two).json() == []
    assert client.get(f"/tasks/{task_id}/tags", headers=user_two).status_code == 404
    assert (
        client.put(
            f"/tasks/{task_id}/tags", headers=user_two, json={"tag_ids": [tag_id]}
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/tasks/{task_id}/tags", headers=user_one, json={"tag_ids": [tag_id]}
        ).status_code
        == 200
    )

    other_task = client.post("/tasks", headers=user_two, json={"title": "Other task"})
    assert (
        client.put(
            f"/tasks/{other_task.json()['id']}/tags",
            headers=user_two,
            json={"tag_ids": [tag_id]},
        ).status_code
        == 404
    )
