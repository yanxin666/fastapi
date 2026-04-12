from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import InvalidTokenError, decode_token
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from fastapi import Depends, HTTPException, Request


# JWT 校验依赖函数
def jwt_auth_dependency(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header[7:]
    try:
        payload = decode_token(token, expected_token_type="access")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    request.state.user_id = payload.subject
    return payload.subject


def get_current_user(
    user_id: str = Depends(jwt_auth_dependency), db: Session = Depends(get_db)
) -> User:
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def require_permissions(*required_permissions: str):
    def dependency(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        permissions = set(
            db.execute(
                select(Permission.code)
                .join(Role.permissions)
                .join(Role.users)
                .where(User.id == user.id)
                .distinct()
            ).scalars()
        )
        if not set(required_permissions).issubset(permissions):
            raise HTTPException(status_code=403, detail="Permission denied")
        return user

    return dependency
