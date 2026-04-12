from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import hash_password
from app.middleware.jwt import require_permissions
from app.models.role import Role
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(tags=["system"])
router_prefix_setting = "admin_api_prefix"


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str


class UpdateUserRequest(BaseModel):
    username: str
    email: str


class ResetPasswordRequest(BaseModel):
    password: str


class AssignUserRolesRequest(BaseModel):
    role_ids: list[int]


@router.get("/users")
def list_users(
    _: User = Depends(require_permissions("user:view")),
    db: Session = Depends(get_db),
):
    users = db.execute(select(User).order_by(User.id)).scalars().all()
    return {"items": [_serialize_user(user) for user in users]}


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: int,
    _: User = Depends(require_permissions("user:view")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user_detail(user, db)


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    _: User = Depends(require_permissions("user:create")),
    db: Session = Depends(get_db),
):
    _ensure_unique_user_fields(db, username=payload.username, email=payload.email)

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.post("/users/{user_id}/update")
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    _: User = Depends(require_permissions("user:create")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_unique_user_fields(
        db,
        username=payload.username,
        email=payload.email,
        exclude_user_id=user_id,
    )

    user.username = payload.username
    user.email = payload.email
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.post("/users/{user_id}/roles")
def assign_user_roles(
    user_id: int,
    payload: AssignUserRolesRequest,
    _: User = Depends(require_permissions("user:create")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    roles = []
    if payload.role_ids:
        roles = (
            db.execute(select(Role).where(Role.id.in_(payload.role_ids)))
            .scalars()
            .all()
        )

    user.roles = roles
    db.commit()
    return {"success": True}


@router.post("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    _: User = Depends(require_permissions("user:create")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: ResetPasswordRequest,
    _: User = Depends(require_permissions("user:create")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.password)
    db.commit()
    return {"success": True}


def _ensure_unique_user_fields(
    db: Session,
    *,
    username: str,
    email: str,
    exclude_user_id: int | None = None,
) -> None:
    username_query = select(User.id).where(User.username == username)
    if exclude_user_id is not None:
        username_query = username_query.where(User.id != exclude_user_id)
    existing_username = db.execute(username_query).scalar_one_or_none()
    if existing_username is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    email_query = select(User.id).where(User.email == email)
    if exclude_user_id is not None:
        email_query = email_query.where(User.id != exclude_user_id)
    existing_email = db.execute(email_query).scalar_one_or_none()
    if existing_email is not None:
        raise HTTPException(status_code=409, detail="Email already exists")


def _serialize_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }


def _serialize_user_detail(user: User, db: Session) -> dict[str, object]:
    role_names = (
        db.execute(
            select(Role.name)
            .join(User.roles)
            .where(User.id == user.id)
            .order_by(Role.name)
        )
        .scalars()
        .all()
    )
    return {
        **_serialize_user(user),
        "roles": role_names,
    }
