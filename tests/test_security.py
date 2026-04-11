import pytest

from app.core.config import get_settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_expose_default_auth_configuration() -> None:
    settings = get_settings()

    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_ttl_minutes == 30
    assert settings.refresh_token_ttl_days == 7


def test_hash_password_round_trip() -> None:
    password_hash = hash_password("yanxin-password")

    assert password_hash != "yanxin-password"
    assert verify_password("yanxin-password", password_hash) is True


def test_verify_password_rejects_invalid_password() -> None:
    password_hash = hash_password("yanxin-password")

    assert verify_password("wrong-password", password_hash) is False


def test_access_token_round_trip() -> None:
    token = create_access_token(subject="admin")

    payload = decode_token(token, expected_token_type="access")

    assert payload.subject == "admin"
    assert payload.token_type == "access"
    assert payload.token_id is None


def test_refresh_token_round_trip() -> None:
    token = create_refresh_token(subject="admin", token_id="refresh-001")

    payload = decode_token(token, expected_token_type="refresh")

    assert payload.subject == "admin"
    assert payload.token_type == "refresh"
    assert payload.token_id == "refresh-001"


def test_decode_token_rejects_unexpected_token_type() -> None:
    token = create_access_token(subject="admin")

    with pytest.raises(InvalidTokenError, match="Unexpected token type"):
        decode_token(token, expected_token_type="refresh")
