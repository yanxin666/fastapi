from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.core.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
ALEMBIC_DIR = REPO_ROOT / "alembic"
HEAD_REVISION = "0007_add_customer_claim_status"
EXPECTED_TABLES = {
    "alembic_version",
    "audit_logs",
    "permissions",
    "refresh_tokens",
    "role_permissions",
    "roles",
    "user_roles",
    "users",
}
LEGACY_TIMESTAMP = "2000-01-01 00:00:00"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make_config(database_url: str | None = None) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    if database_url is not None:
        config.set_main_option("sqlalchemy.url", database_url)
    return config


def read_version(database_url: str) -> str:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        engine.dispose()


def upgrade_sqlite_database(tmp_path: Path, filename: str):
    sqlite_path = tmp_path / filename
    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"
    command.upgrade(make_config(sqlite_url), "head")
    return sqlite_url, create_engine(sqlite_url)


def get_index(indexes: list[dict[str, object]], name: str) -> dict[str, object]:
    return next(index for index in indexes if index["name"] == name)


def test_alembic_has_single_head_revision() -> None:
    assert ALEMBIC_INI.exists()
    assert ALEMBIC_DIR.exists()

    script = ScriptDirectory.from_config(make_config())
    heads = script.get_heads()

    assert len(heads) == 1
    assert set(heads) == {HEAD_REVISION}


def test_alembic_upgrade_creates_auth_tables(tmp_path: Path) -> None:
    _, engine = upgrade_sqlite_database(tmp_path, "auth-schema.db")

    try:
        assert EXPECTED_TABLES.issubset(set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()


def test_alembic_upgrade_enforces_auth_constraints_and_defaults(tmp_path: Path) -> None:
    _, engine = upgrade_sqlite_database(tmp_path, "auth-constraints.db")

    try:
        inspector = inspect(engine)
        assert (
            bool(
                get_index(inspector.get_indexes("users"), "ix_users_username")["unique"]
            )
            is True
        )
        assert (
            bool(get_index(inspector.get_indexes("users"), "ix_users_email")["unique"])
            is True
        )
        assert (
            bool(get_index(inspector.get_indexes("roles"), "ix_roles_name")["unique"])
            is True
        )
        assert (
            bool(
                get_index(inspector.get_indexes("permissions"), "ix_permissions_code")[
                    "unique"
                ]
            )
            is True
        )
        assert (
            bool(
                get_index(
                    inspector.get_indexes("refresh_tokens"),
                    "ix_refresh_tokens_token_id",
                )["unique"]
            )
            is True
        )
        assert (
            bool(
                get_index(
                    inspector.get_indexes("refresh_tokens"), "ix_refresh_tokens_user_id"
                )["unique"]
            )
            is False
        )

        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys = ON"))
            connection.execute(
                text(
                    "INSERT INTO users (username, email, password_hash) VALUES (:username, :email, :password_hash)"
                ),
                {
                    "username": "admin",
                    "email": "admin@example.com",
                    "password_hash": "hashed-password",
                },
            )
            defaults = connection.execute(
                text(
                    "SELECT is_active, is_superuser FROM users WHERE username = :username"
                ),
                {"username": "admin"},
            ).one()

        assert tuple(defaults) == (1, 0)

        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys = ON"))
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO refresh_tokens (token_id, user_id, expires_at) "
                        "VALUES (:token_id, :user_id, CURRENT_TIMESTAMP)"
                    ),
                    {"token_id": "missing-user-token", "user_id": 999},
                )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    (
        "insert_sql",
        "insert_params",
        "update_sql",
        "update_params",
        "select_sql",
        "select_params",
    ),
    [
        (
            "INSERT INTO users (username, email, password_hash, is_active, is_superuser, created_at, updated_at) "
            "VALUES (:username, :email, :password_hash, 1, 0, :timestamp, :timestamp)",
            {
                "username": "admin",
                "email": "admin@example.com",
                "password_hash": "hashed-password",
                "timestamp": LEGACY_TIMESTAMP,
            },
            "UPDATE users SET email = :email WHERE username = :username",
            {"username": "admin", "email": "admin+updated@example.com"},
            "SELECT updated_at FROM users WHERE username = :username",
            {"username": "admin"},
        ),
        (
            "INSERT INTO roles (name, description, created_at, updated_at) "
            "VALUES (:name, :description, :timestamp, :timestamp)",
            {
                "name": "superadmin",
                "description": "initial",
                "timestamp": LEGACY_TIMESTAMP,
            },
            "UPDATE roles SET description = :description WHERE name = :name",
            {"name": "superadmin", "description": "updated"},
            "SELECT updated_at FROM roles WHERE name = :name",
            {"name": "superadmin"},
        ),
    ],
)
def test_alembic_upgrade_refreshes_updated_at_on_direct_updates(
    tmp_path: Path,
    insert_sql: str,
    insert_params: dict[str, object],
    update_sql: str,
    update_params: dict[str, object],
    select_sql: str,
    select_params: dict[str, object],
) -> None:
    _, engine = upgrade_sqlite_database(tmp_path, "updated-at.db")

    try:
        with engine.begin() as connection:
            connection.execute(text(insert_sql), insert_params)
            connection.execute(text(update_sql), update_params)
            updated_at = connection.execute(
                text(select_sql), select_params
            ).scalar_one()

        assert str(updated_at) != LEGACY_TIMESTAMP
    finally:
        engine.dispose()


def test_alembic_uses_application_database_url_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sqlite_path = tmp_path / "settings-default.db"
    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"
    monkeypatch.setenv("APP_DATABASE_URL", sqlite_url)

    command.upgrade(make_config(), "head")

    assert sqlite_path.exists()
    assert read_version(sqlite_url) == HEAD_REVISION


def test_alembic_prefers_configured_database_url_over_application_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    default_path = tmp_path / "settings-default.db"
    override_path = tmp_path / "config-override.db"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{default_path.as_posix()}")
    override_url = f"sqlite:///{override_path.as_posix()}"

    command.upgrade(make_config(override_url), "head")

    assert not default_path.exists()
    assert override_path.exists()
    assert read_version(override_url) == HEAD_REVISION
