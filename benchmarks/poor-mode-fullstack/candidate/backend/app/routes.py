from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request

from .auth import require_auth
from .db import database


api = Blueprint("api", __name__, url_prefix="/api")


def task_json(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "estimate_hours": row["estimate_hours"] or None,
        "created_at": row["created_at"],
        "version": row["version"],
    }


@api.get("/projects/<int:project_id>/tasks")
@require_auth
def list_tasks(project_id: int):
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    query = request.args.get("q", "")
    offset = page * page_size
    with database(current_app.config["DATABASE"]) as connection:
        project = connection.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if project is None:
            return jsonify(error={"code": "not_found", "message": "Project not found"}), 404
        like = f"%{query}%"
        total = connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND title LIKE ?", (project_id, like)
        ).fetchone()[0]
        rows = connection.execute(
            """SELECT * FROM tasks WHERE project_id = ? AND title LIKE ?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (project_id, like, page_size, offset),
        ).fetchall()
    return jsonify(items=[task_json(row) for row in rows], page=page, page_size=page_size, total=total)


@api.post("/projects/<int:project_id>/tasks")
@require_auth
def create_task(project_id: int):
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    estimate_hours = payload.get("estimate_hours") or None
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with database(current_app.config["DATABASE"]) as connection:
        cursor = connection.execute(
            """INSERT INTO tasks(project_id, title, status, estimate_hours, created_at, version)
               VALUES (?, ?, 'todo', ?, ?, 1)""",
            (project_id, title, estimate_hours, now),
        )
        connection.commit()
        task_id = cursor.lastrowid
        writer = current_app.config.get("AUDIT_WRITER")
        if writer:
            writer(connection, g.user["id"], "task.created", task_id, now)
        else:
            connection.execute(
                "INSERT INTO audit_log(user_id, action, task_id, created_at) VALUES (?, ?, ?, ?)",
                (g.user["id"], "task.created", task_id, now),
            )
            connection.commit()
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(task_json(row)), 200


@api.patch("/tasks/<int:task_id>")
@require_auth
def update_task(task_id: int):
    payload = request.get_json(silent=True) or {}
    with database(current_app.config["DATABASE"]) as connection:
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return jsonify(error={"code": "not_found", "message": "Task not found"}), 404
        title = payload.get("title") or row["title"]
        status = payload.get("status") or row["status"]
        connection.execute(
            "UPDATE tasks SET title = ?, status = ?, version = version + 1 WHERE id = ?",
            (title, status, task_id),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(task_json(updated))

