import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture()
def alice_headers():
    return {"Authorization": "Bearer token-alice"}

