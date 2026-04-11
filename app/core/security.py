from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets

import jwt

from app.core.config import get_settings


class InvalidTokenError(ValueError):
    pass


@dataclass(slots=True)
class TokenPayload:
    subject: str
    token_type: str
    expires_at: datetime
    token_id: str | None = None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected_digest = password_hash.split("$", maxsplit=1)
    except ValueError:
        return False

    actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_ttl_minutes)
    return _encode_token(subject=subject, token_type="access", expires_at=expires_at)


def create_refresh_token(subject: str, token_id: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    return _encode_token(
        subject=subject,
        token_type="refresh",
        expires_at=expires_at,
        token_id=token_id,
    )


def decode_token(token: str, *, expected_token_type: str) -> TokenPayload:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Invalid token") from exc

    token_type = payload.get("type")
    if token_type != expected_token_type:
        raise InvalidTokenError("Unexpected token type")

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token subject is required")

    expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)

    return TokenPayload(
        subject=subject,
        token_type=token_type,
        expires_at=expires_at,
        token_id=payload.get("jti"),
    )


def _encode_token(
    *,
    subject: str,
    token_type: str,
    expires_at: datetime,
    token_id: str | None = None,
) -> str:
    settings = get_settings()
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expires_at,
    }
    if token_id is not None:
        payload["jti"] = token_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
