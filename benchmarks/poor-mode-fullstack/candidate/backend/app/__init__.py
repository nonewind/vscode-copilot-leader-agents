from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify

from .db import init_database
from .routes import api


def create_app(db_path: str | None = None, audit_writer=None) -> Flask:
    app = Flask(__name__)
    resolved_path = db_path or str(Path(__file__).resolve().parent.parent / "taskboard.db")
    app.config.update(TESTING=False, DATABASE=resolved_path, AUDIT_WRITER=audit_writer)
    init_database(resolved_path)
    app.register_blueprint(api)

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error={"code": "not_found", "message": "Resource not found"}), 404

    return app

