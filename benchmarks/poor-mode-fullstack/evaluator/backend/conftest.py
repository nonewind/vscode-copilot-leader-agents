from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import create_app


def pytest_addoption(parser):
    parser.addoption("--score-output", action="store", default=None)


def pytest_configure(config):
    config._poor_mode_results = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" or (report.when == "setup" and report.failed):
        item.config._poor_mode_results.append(
            {
                "nodeid": item.nodeid,
                "status": "passed" if report.passed else "failed",
                "detail": str(report.longrepr) if report.failed else "",
            }
        )


def pytest_sessionfinish(session, exitstatus):
    output = session.config.getoption("--score-output")
    if output:
        Path(output).write_text(
            json.dumps(
                {"exitstatus": exitstatus, "tests": session.config._poor_mode_results},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


@pytest.fixture()
def app(tmp_path):
    instance = create_app(str(tmp_path / "hidden.db"))
    instance.config.update(TESTING=True)
    return instance


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def alice():
    return {"Authorization": "Bearer token-alice"}


@pytest.fixture()
def bob():
    return {"Authorization": "Bearer token-bob"}


def assert_error(response, status, code=None):
    assert response.status_code == status
    assert set(response.json) == {"error"}
    assert set(response.json["error"]) == {"code", "message"}
    assert isinstance(response.json["error"]["message"], str)
    if code is not None:
        assert response.json["error"]["code"] == code

