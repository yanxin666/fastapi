from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.middleware.jwt import jwt_auth_dependency
from app.models.permission import Permission
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User

router = APIRouter(tags=["auth"])
router_prefix_setting = "admin_api_prefix"


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    refresh_token_id = str(uuid4())
    settings = get_settings()
    db.add(
        RefreshToken(
            token_id=refresh_token_id,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    db.commit()

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id), refresh_token_id),
        "token_type": "bearer",
        "user": _serialize_user(user, db),
    }


@router.post("/auth/refresh")
def refresh_access_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    stored_token, user = _get_refresh_token_user(payload.refresh_token, db)
    stored_token.is_revoked = True
    stored_token.revoked_at = datetime.now(UTC)

    new_token_id = str(uuid4())
    settings = get_settings()
    db.add(
        RefreshToken(
            token_id=new_token_id,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    db.commit()

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id), new_token_id),
        "token_type": "bearer",
    }


@router.post("/auth/logout")
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    stored_token, _ = _get_refresh_token_user(payload.refresh_token, db)
    stored_token.is_revoked = True
    stored_token.revoked_at = datetime.now(UTC)
    db.commit()
    return {"success": True}


@router.get("/auth/me")
def me(user_id: str = Depends(jwt_auth_dependency), db: Session = Depends(get_db)):
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return _serialize_user(user, db)


def _get_refresh_token_user(token: str, db: Session) -> tuple[RefreshToken, User]:
    try:
        payload = decode_token(token, expected_token_type="refresh")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    stored_token = db.execute(
        select(RefreshToken).where(RefreshToken.token_id == payload.token_id)
    ).scalar_one_or_none()
    if stored_token is None or stored_token.is_revoked:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(User, int(payload.subject))
    if user is None or stored_token.user_id != user.id:
        raise HTTPException(status_code=401, detail="Invalid token")

    return stored_token, user


def _serialize_user(user: User, db: Session) -> dict[str, object]:
    roles = db.execute(
        select(Role.name).join(User.roles).where(User.id == user.id).order_by(Role.name)
    ).scalars().all()
    permissions = db.execute(
        select(Permission.code)
        .join(Role.permissions)
        .join(Role.users)
        .where(User.id == user.id)
        .distinct()
        .order_by(Permission.code)
    ).scalars().all()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": roles,
        "permissions": permissions,
    }
