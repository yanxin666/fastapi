from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.middleware.jwt import require_permissions
from app.models.permission import Permission
from app.models.user import User

router = APIRouter(tags=["system"])
router_prefix_setting = "admin_api_prefix"


@router.get("/permissions")
def list_permissions(
    _: User = Depends(require_permissions("permission:view")),
    db: Session = Depends(get_db),
):
    permissions = db.execute(select(Permission).order_by(Permission.id)).scalars().all()
    return {"items": [_serialize_permission(permission) for permission in permissions]}



def _serialize_permission(permission: Permission) -> dict[str, object]:
    return {
        "id": permission.id,
        "code": permission.code,
        "description": permission.description,
    }
