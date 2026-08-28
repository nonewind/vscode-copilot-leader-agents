from __future__ import annotations

import sqlite3

import pytest

from app import create_app

from conftest import assert_error


def test_auth_invalid_token_uses_error_contract(client):
    response = client.get(
        "/api/projects/1/tasks", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert_error(response, 401, "unauthorized")


def test_auth_forbids_listing_another_users_project(client, bob):
    assert_error(client.get("/api/projects/1/tasks", headers=bob), 403, "forbidden")


def test_auth_forbids_listing_ownership_is_data_driven(app, client, alice):
    connection = sqlite3.connect(app.config["DATABASE"])
    try:
        connection.execute("INSERT INTO users(id, name, token) VALUES (41, 'Carol', 'token-carol')")
        connection.execute("INSERT INTO projects(id, owner_id, name) VALUES (73, 41, 'Carol project')")
        connection.commit()
    finally:
        connection.close()
    own = client.get(
        "/api/projects/73/tasks", headers={"Authorization": "Bearer token-carol"}
    )
    assert own.status_code == 200
    assert_error(client.get("/api/projects/73/tasks", headers=alice), 403, "forbidden")


def test_auth_forbids_creating_in_another_users_project(client, bob):
    response = client.post(
        "/api/projects/1/tasks",
        headers={**bob, "Idempotency-Key": "cross-user"},
        json={"title": "Intrusion", "estimate_hours": 1},
    )
    assert_error(response, 403, "forbidden")


def test_auth_forbids_patching_another_users_task(client, alice):
    response = client.patch(
        "/api/tasks/3", headers=alice, json={"status": "done", "version": 1}
    )
    assert_error(response, 403, "forbidden")


def test_pagination_is_one_based_and_preserves_zero(client, alice):
    response = client.get("/api/projects/1/tasks?page=1&page_size=1", headers=alice)
    assert response.status_code == 200
    assert response.json["items"][0]["id"] == 1
    assert response.json["items"][0]["estimate_hours"] == 0
    assert response.json["page"] == 1


@pytest.mark.parametrize(
    "query",
    ["page=0", "page=-1", "page=nope", "page_size=0", "page_size=51", "page_size=1.5"],
)
def test_pagination_rejects_invalid_values(client, alice, query):
    assert_error(client.get(f"/api/projects/1/tasks?{query}", headers=alice), 422, "validation_error")


def test_pagination_out_of_range_is_empty_with_stable_total(client, alice):
    response = client.get("/api/projects/1/tasks?page=99&page_size=20", headers=alice)
    assert response.status_code == 200
    assert response.json["items"] == []
    assert response.json["total"] == 2


def test_pagination_sort_is_stable_when_timestamps_match(app, client, alice):
    connection = sqlite3.connect(app.config["DATABASE"])
    try:
        connection.executemany(
            """INSERT INTO tasks(project_id, title, status, estimate_hours, created_at, version)
               VALUES (1, ?, 'todo', 1, '2026-08-29T00:00:00Z', 1)""",
            [("same-time-a",), ("same-time-b",)],
        )
        ids = [
            row[0]
            for row in connection.execute(
                "SELECT id FROM tasks WHERE title LIKE 'same-time-%' ORDER BY id DESC"
            )
        ]
        connection.commit()
    finally:
        connection.close()
    response = client.get("/api/projects/1/tasks?page=1&page_size=2", headers=alice)
    assert [item["id"] for item in response.json["items"]] == ids


def test_search_is_case_insensitive_and_trim_safe(client, alice):
    response = client.get("/api/projects/1/tasks?q=ALICE&page=1", headers=alice)
    assert response.status_code == 200
    assert [item["id"] for item in response.json["items"]] == [2]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "   ", "estimate_hours": 1},
        {"title": "x" * 81, "estimate_hours": 1},
        {"title": "valid", "estimate_hours": -1},
        {"title": "valid", "estimate_hours": 101},
        {"title": "valid", "estimate_hours": 1.5},
        {"title": "valid", "estimate_hours": True},
        ["not", "an", "object"],
    ],
)
def test_validation_rejects_bad_create_payloads(client, alice, payload):
    response = client.post(
        "/api/projects/1/tasks",
        headers={**alice, "Idempotency-Key": "invalid-payload"},
        json=payload,
    )
    assert_error(response, 422, "validation_error")


def test_validation_rejects_bad_patch_fields(client, alice):
    cases = [
        {"version": 1},
        {"status": "blocked", "version": 1},
        {"title": "ok", "version": 1, "admin": True},
        {"title": "ok", "version": "1"},
        {"title": "ok", "version": True},
    ]
    for payload in cases:
        response = client.patch("/api/tasks/1", headers=alice, json=payload)
        assert_error(response, 422, "validation_error")


def test_create_requires_nonempty_idempotency_key(client, alice):
    for extra_headers in ({}, {"Idempotency-Key": "   "}):
        response = client.post(
            "/api/projects/1/tasks",
            headers={**alice, **extra_headers},
            json={"title": "Needs key", "estimate_hours": 0},
        )
        assert_error(response, 422, "validation_error")


def test_idempotency_replays_same_task_without_duplicate(client, alice):
    headers = {**alice, "Idempotency-Key": "same-request"}
    payload = {"title": "  One task  ", "estimate_hours": 0}
    first = client.post("/api/projects/1/tasks", headers=headers, json=payload)
    second = client.post("/api/projects/1/tasks", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json == second.json
    listing = client.get("/api/projects/1/tasks?q=One%20task", headers=alice)
    assert listing.json["total"] == 1
    assert listing.json["items"][0]["estimate_hours"] == 0


def test_idempotency_replays_semantically_equal_json_with_different_key_order(client, alice):
    headers = {**alice, "Idempotency-Key": "canonical-json", "Content-Type": "application/json"}
    first = client.post(
        "/api/projects/1/tasks",
        headers=headers,
        data='{"title":"Canonical","estimate_hours":2}',
    )
    second = client.post(
        "/api/projects/1/tasks",
        headers=headers,
        data='{"estimate_hours":2,"title":"Canonical"}',
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json == second.json


def test_idempotency_conflict_does_not_create(client, alice):
    headers = {**alice, "Idempotency-Key": "conflicting-request"}
    first = client.post(
        "/api/projects/1/tasks", headers=headers, json={"title": "First", "estimate_hours": 1}
    )
    conflict = client.post(
        "/api/projects/1/tasks", headers=headers, json={"title": "Second", "estimate_hours": 1}
    )
    assert first.status_code == 201
    assert_error(conflict, 409, "idempotency_conflict")
    listing = client.get("/api/projects/1/tasks?q=Second", headers=alice)
    assert listing.json["total"] == 0


def test_idempotency_key_is_scoped_by_user_and_project(client, alice, bob):
    key = "shared-key"
    alice_result = client.post(
        "/api/projects/1/tasks",
        headers={**alice, "Idempotency-Key": key},
        json={"title": "Alice scoped", "estimate_hours": 1},
    )
    bob_result = client.post(
        "/api/projects/2/tasks",
        headers={**bob, "Idempotency-Key": key},
        json={"title": "Bob scoped", "estimate_hours": 1},
    )
    assert alice_result.status_code == 201
    assert bob_result.status_code == 201
    assert alice_result.json["id"] != bob_result.json["id"]


def test_concurrency_stale_version_is_a_non_mutating_conflict(client, alice):
    before = client.get("/api/projects/1/tasks?q=Alice%20second", headers=alice).json["items"][0]
    response = client.patch(
        "/api/tasks/2", headers=alice, json={"status": "done", "version": before["version"] - 1}
    )
    assert_error(response, 409, "version_conflict")
    after = client.get("/api/projects/1/tasks?q=Alice%20second", headers=alice).json["items"][0]
    assert after == before


def test_concurrency_success_increments_exactly_once(client, alice):
    response = client.patch(
        "/api/tasks/2", headers=alice, json={"status": "done", "version": 3}
    )
    assert response.status_code == 200
    assert response.json["status"] == "done"
    assert response.json["version"] == 4


def test_transaction_rolls_back_task_and_key_when_audit_fails(tmp_path, alice):
    database_path = tmp_path / "audit-failure.db"

    def failing_writer(*_args):
        raise RuntimeError("audit storage unavailable")

    app = create_app(str(database_path), audit_writer=failing_writer)
    app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
    response = app.test_client().post(
        "/api/projects/1/tasks",
        headers={**alice, "Idempotency-Key": "rolled-back-key"},
        json={"title": "Must disappear", "estimate_hours": 4},
    )
    assert_error(response, 500)
    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE title = 'Must disappear'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM idempotency_keys WHERE key = 'rolled-back-key'"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_created_timestamp_is_utc_z(client, alice):
    response = client.post(
        "/api/projects/1/tasks",
        headers={**alice, "Idempotency-Key": "utc-time"},
        json={"title": "UTC timestamp", "estimate_hours": 1},
    )
    assert response.status_code == 201
    assert response.json["created_at"].endswith("Z")
    assert "+00:00" not in response.json["created_at"]
