from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
ALEMBIC_DIR = REPO_ROOT / "alembic"
LEGACY_TIMESTAMP = datetime(2000, 1, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def prepare_engine():
    settings = get_settings()
    command.upgrade(make_config(settings.database_url), "head")
    return create_engine(settings.database_url)


def reset_auth_tables(connection) -> None:
    connection.execute(
        text(
            "TRUNCATE TABLE audit_logs, refresh_tokens, user_roles, role_permissions, permissions, roles, users "
            "RESTART IDENTITY CASCADE"
        )
    )


def test_postgresql_auth_tables_accept_real_data() -> None:
    engine = prepare_engine()

    try:
        with engine.begin() as connection:
            reset_auth_tables(connection)

            role_id = connection.execute(
                text("INSERT INTO roles (name, description) VALUES (:name, :description) RETURNING id"),
                {"name": "superadmin", "description": "system administrator"},
            ).scalar_one()
            permission_id = connection.execute(
                text("INSERT INTO permissions (code, description) VALUES (:code, :description) RETURNING id"),
                {"code": "user:view", "description": "view users"},
            ).scalar_one()
            user_id = connection.execute(
                text(
                    "INSERT INTO users (username, email, password_hash) "
                    "VALUES (:username, :email, :password_hash) RETURNING id"
                ),
                {
                    "username": "admin",
                    "email": "admin@example.com",
                    "password_hash": "hashed-password",
                },
            ).scalar_one()

            connection.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
                {"user_id": user_id, "role_id": role_id},
            )
            connection.execute(
                text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :permission_id)"
                ),
                {"role_id": role_id, "permission_id": permission_id},
            )
            connection.execute(
                text(
                    "INSERT INTO refresh_tokens (token_id, user_id, expires_at) "
                    "VALUES (:token_id, :user_id, NOW() + INTERVAL '7 days')"
                ),
                {"token_id": "refresh-token-001", "user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO audit_logs (action, actor_user_id, resource_type, resource_id, detail) "
                    "VALUES (:action, :actor_user_id, :resource_type, :resource_id, :detail)"
                ),
                {
                    "action": "auth.login",
                    "actor_user_id": user_id,
                    "resource_type": "user",
                    "resource_id": str(user_id),
                    "detail": '{"result":"success"}',
                },
            )

            flags = connection.execute(
                text("SELECT is_active, is_superuser FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            ).one()
            permissions = connection.execute(
                text(
                    "SELECT p.code "
                    "FROM permissions p "
                    "JOIN role_permissions rp ON rp.permission_id = p.id "
                    "JOIN user_roles ur ON ur.role_id = rp.role_id "
                    "WHERE ur.user_id = :user_id"
                ),
                {"user_id": user_id},
            ).scalars().all()
            refresh_token_count = connection.execute(text("SELECT COUNT(*) FROM refresh_tokens")).scalar_one()
            audit_log_count = connection.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar_one()

        assert tuple(flags) == (True, False)
        assert permissions == ["user:view"]
        assert refresh_token_count == 1
        assert audit_log_count == 1
    finally:
        engine.dispose()


def test_postgresql_direct_update_bumps_updated_at() -> None:
    engine = prepare_engine()

    try:
        with engine.begin() as connection:
            reset_auth_tables(connection)
            user_id = connection.execute(
                text(
                    "INSERT INTO users (username, email, password_hash, created_at, updated_at) "
                    "VALUES (:username, :email, :password_hash, :created_at, :updated_at) RETURNING id"
                ),
                {
                    "username": "admin",
                    "email": "admin@example.com",
                    "password_hash": "hashed-password",
                    "created_at": LEGACY_TIMESTAMP,
                    "updated_at": LEGACY_TIMESTAMP,
                },
            ).scalar_one()
            connection.execute(
                text("UPDATE users SET email = :email WHERE id = :user_id"),
                {"email": "admin+updated@example.com", "user_id": user_id},
            )
            updated_at = connection.execute(
                text("SELECT updated_at FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            ).scalar_one()

        assert updated_at > LEGACY_TIMESTAMP
    finally:
        engine.dispose()
