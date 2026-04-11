import pytest
from fastapi.testclient import TestClient

from app.core import db as db_module
from app.core.config import get_settings
from app.main import FRONTEND_INDEX_FILE, create_app

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:yanxin@localhost:5432/postgre"


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_app_exposes_default_settings_and_health_endpoint():
    app = create_app()

    assert app.state.settings.app_name == "FastAPI Service"
    assert app.state.settings.admin_api_prefix == "/api/v1/admin"
    assert app.state.settings.database_url == DEFAULT_DATABASE_URL
    assert app.state.settings.jwt_algorithm == "HS256"
    assert app.state.settings.access_token_ttl_minutes == 30
    assert app.state.settings.refresh_token_ttl_days == 7

    client = TestClient(app)
    response = client.get("/api/v1/admin/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "FastAPI Service",
        "environment": "development",
    }


def test_create_app_uses_environment_overrides_for_health_route(monkeypatch):
    monkeypatch.setenv("APP_APP_NAME", "Admin Service")
    monkeypatch.setenv("APP_APP_ENV", "test")
    monkeypatch.setenv("APP_API_V1_PREFIX", "/api/test")

    app = create_app()

    assert app.state.settings.admin_api_prefix == "/api/test/admin"

    client = TestClient(app)
    response = client.get("/api/test/admin/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Admin Service",
        "environment": "test",
    }


def test_root_path_serves_frontend_index_when_built():
    app = create_app()
    client = TestClient(app)

    response = client.get("/")

    assert FRONTEND_INDEX_FILE.exists()
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<div id=\"root\"></div>" in response.text


def test_spa_route_serves_frontend_index_when_built():
    app = create_app()
    client = TestClient(app)

    response = client.get("/users")

    assert FRONTEND_INDEX_FILE.exists()
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<div id=\"root\"></div>" in response.text


def test_unknown_api_route_still_returns_not_found():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"message": "Not Found", "error": True}


def test_database_engine_is_created_lazily():
    db_module.get_engine.cache_clear()
    db_module.get_session_factory.cache_clear()

    assert db_module.get_engine.cache_info().currsize == 0
    assert db_module.get_session_factory.cache_info().currsize == 0

    engine = db_module.get_engine()
    assert engine.url.render_as_string(hide_password=False) == get_settings().database_url
    assert db_module.get_engine.cache_info().currsize == 1

    session_factory = db_module.get_session_factory()
    assert db_module.get_session_factory.cache_info().currsize == 1

    session = session_factory()
    session.close()
