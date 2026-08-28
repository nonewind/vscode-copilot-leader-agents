from __future__ import annotations

from functools import wraps

from flask import current_app, g, jsonify, request

from .db import database


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
        if not token:
            return jsonify(error={"code": "unauthorized", "message": "Authentication required"}), 401
        with database(current_app.config["DATABASE"]) as connection:
            user = connection.execute(
                "SELECT id, name FROM users WHERE token = ?", (token,)
            ).fetchone()
        if user is None:
            return jsonify(error={"code": "unauthorized", "message": "Invalid token"}), 401
        g.user = dict(user)
        return view(*args, **kwargs)

    return wrapped

