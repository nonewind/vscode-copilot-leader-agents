def test_auth_is_required(client):
    response = client.get("/api/projects/1/tasks")
    assert response.status_code == 401
    assert response.json["error"]["code"] == "unauthorized"


def test_list_has_expected_shape(client, alice_headers):
    response = client.get("/api/projects/1/tasks?page=1&page_size=1", headers=alice_headers)
    assert response.status_code == 200
    assert set(response.json) == {"items", "page", "page_size", "total"}
    assert response.json["total"] == 2


def test_create_and_update_happy_path(client, alice_headers):
    created = client.post(
        "/api/projects/1/tasks",
        headers={**alice_headers, "Idempotency-Key": "smoke-key"},
        json={"title": "Ship it", "estimate_hours": 2},
    )
    assert created.status_code in (200, 201)
    task = created.json
    updated = client.patch(
        f"/api/tasks/{task['id']}",
        headers=alice_headers,
        json={"status": "done", "version": task["version"]},
    )
    assert updated.status_code == 200
    assert updated.json["status"] == "done"
