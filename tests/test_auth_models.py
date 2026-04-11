from sqlalchemy.dialects import postgresql

from app.core.db import Base

import app.models.audit_log  # noqa: F401
import app.models.permission  # noqa: F401
import app.models.refresh_token  # noqa: F401
import app.models.role  # noqa: F401
import app.models.user  # noqa: F401

EXPECTED_TABLES = {
    "audit_logs",
    "permissions",
    "refresh_tokens",
    "role_permissions",
    "roles",
    "user_roles",
    "users",
}


def compile_server_default(column) -> str:
    arg = column.server_default.arg
    if hasattr(arg, "compile"):
        return str(arg.compile(dialect=postgresql.dialect())).lower()
    return str(arg).lower()


def index_by_name(table) -> dict[str, object]:
    return {index.name: index for index in table.indexes}


def test_auth_models_register_expected_tables() -> None:
    assert EXPECTED_TABLES.issubset(set(Base.metadata.tables))


def test_user_and_refresh_token_defaults_compile_for_postgresql() -> None:
    users = Base.metadata.tables["users"]
    refresh_tokens = Base.metadata.tables["refresh_tokens"]

    assert {"id", "username", "email", "password_hash", "is_active", "is_superuser"}.issubset(
        set(users.columns.keys())
    )
    assert compile_server_default(users.c.is_active) == "true"
    assert compile_server_default(users.c.is_superuser) == "false"
    assert compile_server_default(refresh_tokens.c.is_revoked) == "false"
    assert users.c.updated_at.nullable is False


def test_auth_tables_define_unique_indexes() -> None:
    users = Base.metadata.tables["users"]
    roles = Base.metadata.tables["roles"]
    permissions = Base.metadata.tables["permissions"]
    refresh_tokens = Base.metadata.tables["refresh_tokens"]

    user_indexes = index_by_name(users)
    role_indexes = index_by_name(roles)
    permission_indexes = index_by_name(permissions)
    refresh_token_indexes = index_by_name(refresh_tokens)

    assert user_indexes["ix_users_username"].unique is True
    assert user_indexes["ix_users_email"].unique is True
    assert role_indexes["ix_roles_name"].unique is True
    assert permission_indexes["ix_permissions_code"].unique is True
    assert refresh_token_indexes["ix_refresh_tokens_token_id"].unique is True
    assert refresh_token_indexes["ix_refresh_tokens_user_id"].unique is False


def test_auth_relationship_tables_define_composite_primary_keys_and_cascading_foreign_keys() -> None:
    user_roles = Base.metadata.tables["user_roles"]
    role_permissions = Base.metadata.tables["role_permissions"]

    assert [column.name for column in user_roles.primary_key.columns] == ["user_id", "role_id"]
    assert [column.name for column in role_permissions.primary_key.columns] == ["role_id", "permission_id"]

    assert {
        (fk.parent.name, fk.column.table.name, fk.column.name, fk.ondelete) for fk in user_roles.foreign_keys
    } == {
        ("user_id", "users", "id", "CASCADE"),
        ("role_id", "roles", "id", "CASCADE"),
    }
    assert {
        (fk.parent.name, fk.column.table.name, fk.column.name, fk.ondelete) for fk in role_permissions.foreign_keys
    } == {
        ("role_id", "roles", "id", "CASCADE"),
        ("permission_id", "permissions", "id", "CASCADE"),
    }


def test_auth_foreign_keys_match_delete_policies() -> None:
    refresh_tokens = Base.metadata.tables["refresh_tokens"]
    audit_logs = Base.metadata.tables["audit_logs"]

    assert {
        (fk.parent.name, fk.column.table.name, fk.column.name, fk.ondelete) for fk in refresh_tokens.foreign_keys
    } == {
        ("user_id", "users", "id", "CASCADE"),
    }
    assert {
        (fk.parent.name, fk.column.table.name, fk.column.name, fk.ondelete) for fk in audit_logs.foreign_keys
    } == {
        ("actor_user_id", "users", "id", "SET NULL"),
    }
