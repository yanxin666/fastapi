from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.security import decode_token, hash_password, verify_password
from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
ALEMBIC_DIR = REPO_ROOT / "alembic"


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


@pytest.fixture()
def auth_engine():
    settings = get_settings()
    command.upgrade(make_config(settings.database_url), "head")
    engine = create_engine(settings.database_url)

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE audit_logs, refresh_tokens, user_roles, role_permissions, permissions, roles, users "
                    "RESTART IDENTITY CASCADE"
                )
            )
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def seed_admin_user(engine) -> dict[str, object]:
    with engine.begin() as connection:
        role_id = connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description) RETURNING id"),
            {"name": "superadmin", "description": "system administrator"},
        ).scalar_one()
        permission_ids = []
        for code in ["user:view", "user:create"]:
            permission_ids.append(
                connection.execute(
                    text("INSERT INTO permissions (code, description) VALUES (:code, :description) RETURNING id"),
                    {"code": code, "description": code},
                ).scalar_one()
            )
        user_id = connection.execute(
            text(
                "INSERT INTO users (username, email, password_hash) "
                "VALUES (:username, :email, :password_hash) RETURNING id"
            ),
            {
                "username": "admin",
                "email": "admin@example.com",
                "password_hash": hash_password("secret123"),
            },
        ).scalar_one()
        connection.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
            {"user_id": user_id, "role_id": role_id},
        )
        for permission_id in permission_ids:
            connection.execute(
                text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
                {"role_id": role_id, "permission_id": permission_id},
            )

    return {"user_id": user_id, "username": "admin"}


def seed_user(engine, *, username: str, permissions: list[str]) -> dict[str, object]:
    with engine.begin() as connection:
        role_id = connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description) RETURNING id"),
            {"name": f"{username}-role", "description": f"{username} role"},
        ).scalar_one()
        user_id = connection.execute(
            text(
                "INSERT INTO users (username, email, password_hash) "
                "VALUES (:username, :email, :password_hash) RETURNING id"
            ),
            {
                "username": username,
                "email": f"{username}@example.com",
                "password_hash": hash_password("secret123"),
            },
        ).scalar_one()
        connection.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
            {"user_id": user_id, "role_id": role_id},
        )
        for code in permissions:
            permission_id = connection.execute(
                text("INSERT INTO permissions (code, description) VALUES (:code, :description) RETURNING id"),
                {"code": code, "description": code},
            ).scalar_one()
            connection.execute(
                text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
                {"role_id": role_id, "permission_id": permission_id},
            )

    return {"user_id": user_id, "username": username}


def test_login_returns_tokens_and_persists_refresh_token(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)

    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"] == {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_active": True,
        "is_superuser": False,
        "roles": ["superadmin"],
        "permissions": ["user:create", "user:view"],
    }

    with auth_engine.connect() as connection:
        refresh_tokens = connection.execute(
            text("SELECT user_id, is_revoked FROM refresh_tokens ORDER BY id")
        ).all()

    assert refresh_tokens == [(1, False)]


def test_login_rejects_invalid_password(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)

    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"message": "Invalid username or password", "error": True}


def test_refresh_rotates_refresh_token_and_returns_new_access_token(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"] != refresh_token
    payload = decode_token(body["access_token"], expected_token_type="access")
    assert payload.subject == "1"

    with auth_engine.connect() as connection:
        refresh_tokens = connection.execute(
            text("SELECT token_id, is_revoked FROM refresh_tokens ORDER BY id")
        ).all()

    assert len(refresh_tokens) == 2
    assert refresh_tokens[0][1] is True
    assert refresh_tokens[1][1] is False


def test_me_returns_current_user_profile(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_active": True,
        "is_superuser": False,
        "roles": ["superadmin"],
        "permissions": ["user:create", "user:view"],
    }


def test_role_detail_returns_role_profile(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:view"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )
        connection.execute(
            text("INSERT INTO permissions (code, description) VALUES (:code, :description)"),
            {"code": "user:view", "description": "view users"},
        )
        connection.execute(
            text("INSERT INTO permissions (code, description) VALUES (:code, :description)"),
            {"code": "user:create", "description": "create users"},
        )
        connection.execute(
            text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
            {"role_id": 2, "permission_id": 2},
        )
        connection.execute(
            text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
            {"role_id": 2, "permission_id": 3},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/roles/2",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "name": "auditor",
        "description": "audit role",
        "permissions": ["user:create", "user:view"],
    }



def test_role_detail_returns_not_found(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:view"])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/roles/99",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"message": "Role not found", "error": True}



def test_permissions_list_requires_permission_and_returns_permissions(
    client: TestClient, auth_engine
) -> None:
    seed_user(auth_engine, username="auditor", permissions=["permission:view"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO permissions (code, description) VALUES (:code, :description)"),
            {"code": "role:view", "description": "view roles"},
        )
        connection.execute(
            text("INSERT INTO permissions (code, description) VALUES (:code, :description)"),
            {"code": "user:update", "description": "update users"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "auditor", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/permissions",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": 1, "code": "permission:view", "description": "permission:view"},
            {"id": 2, "code": "role:view", "description": "view roles"},
            {"id": 3, "code": "user:update", "description": "update users"},
        ]
    }



def test_permissions_list_forbids_missing_permission(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="operator", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "operator", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/permissions",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"message": "Permission denied", "error": True}



def test_roles_list_requires_permission_and_returns_roles(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:view"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "editor", "description": "editor role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": 1, "name": "manager-role", "description": "manager role"},
            {"id": 2, "name": "auditor", "description": "audit role"},
            {"id": 3, "name": "editor", "description": "editor role"},
        ]
    }



def test_roles_list_forbids_missing_permission(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="operator", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "operator", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"message": "Permission denied", "error": True}



def test_create_role_persists_record_via_post(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:create"])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "auditor", "description": "audit role"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 2,
        "name": "auditor",
        "description": "audit role",
    }

    with auth_engine.connect() as connection:
        created_role = connection.execute(
            text("SELECT name, description FROM roles WHERE id = 2")
        ).one()

    assert created_role == ("auditor", "audit role")



def test_create_role_forbids_missing_permission(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="operator", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "operator", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "auditor", "description": "audit role"},
    )

    assert response.status_code == 403
    assert response.json() == {"message": "Permission denied", "error": True}



def test_create_role_rejects_duplicate_name(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:create"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "auditor", "description": "duplicate role"},
    )

    assert response.status_code == 409
    assert response.json() == {"message": "Role name already exists", "error": True}



def test_update_role_persists_changes_via_post(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:update"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/2/update",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "auditor-updated", "description": "updated audit role"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "name": "auditor-updated",
        "description": "updated audit role",
    }

    with auth_engine.connect() as connection:
        updated_role = connection.execute(
            text("SELECT name, description FROM roles WHERE id = 2")
        ).one()

    assert updated_role == ("auditor-updated", "updated audit role")



def test_update_role_forbids_missing_permission(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="operator", permissions=[])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "operator", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/2/update",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "auditor-updated", "description": "updated audit role"},
    )

    assert response.status_code == 403
    assert response.json() == {"message": "Permission denied", "error": True}



def test_update_role_rejects_duplicate_name_via_post(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:update"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "editor", "description": "editor role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/2/update",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "editor", "description": "duplicate role"},
    )

    assert response.status_code == 409
    assert response.json() == {"message": "Role name already exists", "error": True}



def test_update_role_returns_not_found(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:update"])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/99/update",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "auditor-updated", "description": "updated audit role"},
    )

    assert response.status_code == 404
    assert response.json() == {"message": "Role not found", "error": True}



def test_assign_role_permissions_replaces_permissions_via_post(
    client: TestClient, auth_engine
) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:update"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )
        connection.execute(
            text("INSERT INTO permissions (code, description) VALUES (:code, :description)"),
            {"code": "user:view", "description": "view users"},
        )
        connection.execute(
            text("INSERT INTO permissions (code, description) VALUES (:code, :description)"),
            {"code": "user:create", "description": "create users"},
        )
        connection.execute(
            text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
            {"role_id": 2, "permission_id": 2},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/2/permissions",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"permission_ids": [3]},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}

    with auth_engine.connect() as connection:
        permission_ids = connection.execute(
            text(
                "SELECT permission_id FROM role_permissions WHERE role_id = 2 ORDER BY permission_id"
            )
        ).scalars().all()

    assert permission_ids == [3]



def test_assign_role_permissions_forbids_missing_permission(
    client: TestClient, auth_engine
) -> None:
    seed_user(auth_engine, username="operator", permissions=[])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )
        connection.execute(
            text("INSERT INTO permissions (code, description) VALUES (:code, :description)"),
            {"code": "user:view", "description": "view users"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "operator", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/2/permissions",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"permission_ids": [2]},
    )

    assert response.status_code == 403
    assert response.json() == {"message": "Permission denied", "error": True}





def test_delete_role_removes_role_via_post(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:delete"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/2/delete",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}

    with auth_engine.connect() as connection:
        deleted_role = connection.execute(text("SELECT id FROM roles WHERE id = 2")).scalar_one_or_none()

    assert deleted_role is None



def test_delete_role_returns_not_found(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:delete"])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/99/delete",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"message": "Role not found", "error": True}



def test_delete_role_rejects_role_assigned_to_users(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="manager", permissions=["role:delete"])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )
        connection.execute(
            text(
                "INSERT INTO users (username, email, password_hash) "
                "VALUES (:username, :email, :password_hash) RETURNING id"
            ),
            {
                "username": "editor",
                "email": "editor@example.com",
                "password_hash": hash_password("secret123"),
            },
        )
        connection.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
            {"user_id": 2, "role_id": 2},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "manager", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/roles/2/delete",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "message": "Role is assigned to users and cannot be deleted",
        "error": True,
    }



def test_users_list_requires_permission_and_returns_users(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_active": True,
                "is_superuser": False,
            }
        ]
    }


def test_users_list_forbids_missing_permission(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="operator", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "operator", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"message": "Permission denied", "error": True}



def test_user_detail_returns_user_profile(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/users/1",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_active": True,
        "is_superuser": False,
        "roles": ["superadmin"],
    }



def test_create_user_persists_record(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": "editor",
            "email": "editor@example.com",
            "password": "secret123",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 2,
        "username": "editor",
        "email": "editor@example.com",
        "is_active": True,
        "is_superuser": False,
    }

    with auth_engine.connect() as connection:
        created_user = connection.execute(
            text("SELECT username, email, password_hash FROM users WHERE id = 2")
        ).one()

    assert created_user[0] == "editor"
    assert created_user[1] == "editor@example.com"
    assert created_user[2] != "secret123"



def test_create_user_rejects_duplicate_username(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": "admin",
            "email": "another-admin@example.com",
            "password": "secret123",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"message": "Username already exists", "error": True}



def test_create_user_rejects_duplicate_email(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": "another-admin",
            "email": "admin@example.com",
            "password": "secret123",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"message": "Email already exists", "error": True}



def test_update_user_persists_changes_via_post(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    seed_user(auth_engine, username="editor", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/2/update",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": "editor-updated",
            "email": "editor-updated@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "username": "editor-updated",
        "email": "editor-updated@example.com",
        "is_active": True,
        "is_superuser": False,
    }

    with auth_engine.connect() as connection:
        updated_user = connection.execute(
            text("SELECT username, email FROM users WHERE id = 2")
        ).one()

    assert updated_user == ("editor-updated", "editor-updated@example.com")



def test_update_user_rejects_duplicate_username_via_post(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    seed_user(auth_engine, username="editor", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/2/update",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": "admin",
            "email": "editor-updated@example.com",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"message": "Username already exists", "error": True}



def test_update_user_rejects_duplicate_email_via_post(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    seed_user(auth_engine, username="editor", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/2/update",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": "editor-updated",
            "email": "admin@example.com",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"message": "Email already exists", "error": True}



def test_assign_user_roles_replaces_roles_via_post(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    seed_user(auth_engine, username="editor", permissions=[])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "reviewer", "description": "review role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/2/roles",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"role_ids": [3]},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}

    with auth_engine.connect() as connection:
        role_ids = connection.execute(
            text("SELECT role_id FROM user_roles WHERE user_id = 2 ORDER BY role_id")
        ).scalars().all()

    assert role_ids == [3]



def test_assign_user_roles_forbids_missing_permission(client: TestClient, auth_engine) -> None:
    seed_user(auth_engine, username="operator", permissions=[])
    seed_user(auth_engine, username="editor", permissions=[])
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "operator", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/2/roles",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"role_ids": [3]},
    )

    assert response.status_code == 403
    assert response.json() == {"message": "Permission denied", "error": True}



def test_assign_user_roles_returns_not_found_for_missing_user(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    with auth_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": "auditor", "description": "audit role"},
        )

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/99/roles",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"role_ids": [2]},
    )

    assert response.status_code == 404
    assert response.json() == {"message": "User not found", "error": True}



def test_user_routes_use_get_or_post_only(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.put(
        "/api/v1/admin/users/1/update",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"username": "admin", "email": "admin@example.com"},
    )

    assert response.status_code == 405



def test_toggle_user_active_status_via_post(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    seed_user(auth_engine, username="editor", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/2/toggle-active",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "username": "editor",
        "email": "editor@example.com",
        "is_active": False,
        "is_superuser": False,
    }

    with auth_engine.connect() as connection:
        is_active = connection.execute(text("SELECT is_active FROM users WHERE id = 2")).scalar_one()

    assert is_active is False



def test_toggle_user_active_status_switches_back_on_second_post(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    seed_user(auth_engine, username="editor", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    first_response = client.post(
        "/api/v1/admin/users/2/toggle-active",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    second_response = client.post(
        "/api/v1/admin/users/2/toggle-active",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json() == {
        "id": 2,
        "username": "editor",
        "email": "editor@example.com",
        "is_active": True,
        "is_superuser": False,
    }



def test_reset_user_password_via_post(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    seed_user(auth_engine, username="editor", permissions=[])
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/2/reset-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"password": "new-secret456"},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}

    with auth_engine.connect() as connection:
        password_hash = connection.execute(
            text("SELECT password_hash FROM users WHERE id = 2")
        ).scalar_one()

    assert password_hash != "secret123"
    assert verify_password("new-secret456", password_hash) is True



def test_reset_user_password_replaces_previous_hash(client: TestClient, auth_engine) -> None:
    seed_admin_user(auth_engine)
    seed_user(auth_engine, username="editor", permissions=[])
    with auth_engine.connect() as connection:
        original_hash = connection.execute(
            text("SELECT password_hash FROM users WHERE id = 2")
        ).scalar_one()

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/admin/users/2/reset-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"password": "new-secret456"},
    )

    assert response.status_code == 200

    with auth_engine.connect() as connection:
        updated_hash = connection.execute(
            text("SELECT password_hash FROM users WHERE id = 2")
        ).scalar_one()

    assert updated_hash != original_hash


