from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authz.router import PolicyRouter
from app.core.db import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from fastapi import Depends, HTTPException, status

router = PolicyRouter(tags=["system"])
router_prefix_setting = "admin_api_prefix"


class CreateRoleRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateRoleRequest(BaseModel):
    name: str
    description: str | None = None


class AssignRolePermissionsRequest(BaseModel):
    permission_ids: list[int]


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
):
    roles = db.execute(select(Role).order_by(Role.id)).scalars().all()
    return {"items": [_serialize_role(role) for role in roles]}


@router.get("/roles/{role_id}")
def get_role_detail(
    role_id: int,
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return _serialize_role_detail(role, db)


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def create_role(
    payload: CreateRoleRequest,
    db: Session = Depends(get_db),
):
    existing_role = db.execute(
        select(Role.id).where(Role.name == payload.name)
    ).scalar_one_or_none()
    if existing_role is not None:
        raise HTTPException(status_code=409, detail="Role name already exists")

    role = Role(name=payload.name, description=payload.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return _serialize_role(role)


@router.post("/roles/{role_id}/update")
def update_role(
    role_id: int,
    payload: UpdateRoleRequest,
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    existing_role = db.execute(
        select(Role.id).where(Role.name == payload.name, Role.id != role_id)
    ).scalar_one_or_none()
    if existing_role is not None:
        raise HTTPException(status_code=409, detail="Role name already exists")

    role.name = payload.name
    role.description = payload.description
    db.commit()
    db.refresh(role)
    return _serialize_role(role)


@router.post("/roles/{role_id}/delete")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    assigned_user_id = db.execute(
        select(User.id).join(User.roles).where(Role.id == role_id).limit(1)
    ).scalar_one_or_none()
    if assigned_user_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Role is assigned to users and cannot be deleted",
        )

    db.delete(role)
    db.commit()
    return {"success": True}


@router.post("/roles/{role_id}/permissions")
def assign_role_permissions(
    role_id: int,
    payload: AssignRolePermissionsRequest,
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = []
    if payload.permission_ids:
        permissions = (
            db.execute(
                select(Permission).where(Permission.id.in_(payload.permission_ids))
            )
            .scalars()
            .all()
        )

    role.permissions = permissions
    db.commit()
    return {"success": True}


def _serialize_role(role: Role) -> dict[str, object]:
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
    }


def _serialize_role_detail(role: Role, db: Session) -> dict[str, object]:
    permission_codes = (
        db.execute(
            select(Permission.code)
            .join(Role.permissions)
            .where(Role.id == role.id)
            .order_by(Permission.code)
        )
        .scalars()
        .all()
    )
    return {
        **_serialize_role(role),
        "permissions": permission_codes,
    }
