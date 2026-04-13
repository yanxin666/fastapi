"""
JWT 认证中间件模块

提供了 JWT 认证相关的依赖注入函数，包括：
1. JWT token 解析
2. 当前用户获取
3. 权限校验
"""

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
    """
    JWT 认证依赖函数

    从请求头中提取并验证 JWT access token。
    验证成功后，将用户 ID 存储到 request.state 中，供后续使用。

    使用方式：
        @app.get("/protected")
        def protected_route(user_id: str = Depends(jwt_auth_dependency)):
            ...

    Args:
        request: FastAPI 请求对象

    Returns:
        str: 用户 ID（字符串格式）

    Raises:
        HTTPException: 401 当 token 缺失、无效或过期时
    """
    # 从请求头中获取 Authorization 头
    auth_header = request.headers.get("Authorization")

    # 检查 Authorization 头是否存在且格式正确（Bearer token）
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    # 提取 token 部分（去掉 "Bearer " 前缀，共 7 个字符）
    token = auth_header[7:]

    try:
        # 解码并验证 token，期望是 access token 类型
        payload = decode_token(token, expected_token_type="access")
    except InvalidTokenError as exc:
        # token 无效（签名错误、已过期、类型不匹配等）
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    # 将用户 ID 存储到 request.state 中，方便其他依赖或路由函数使用
    request.state.user_id = payload.subject

    # 返回用户 ID
    return payload.subject


def get_current_user(
    user_id: str = Depends(jwt_auth_dependency), db: Session = Depends(get_db)
) -> User:
    """
    获取当前用户依赖函数

    首先通过 jwt_auth_dependency 验证 token 并获取用户 ID，
    然后从数据库中查询完整的用户对象。

    使用方式：
        @app.get("/me")
        def get_current_user_info(user: User = Depends(get_current_user)):
            ...

    Args:
        user_id: 从 jwt_auth_dependency 依赖获取的用户 ID
        db: 数据库会话

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 401 当 token 无效或用户不存在时
    """
    # 根据用户 ID 从数据库查询用户对象
    # 注意：user_id 是字符串，需要转换为 int
    user = db.get(User, int(user_id))

    # 如果用户不存在，返回 401 错误
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 返回用户对象
    return user


def require_permissions(*required_permissions: str):
    """
    权限校验依赖函数（工厂函数）

    这是一个装饰器工厂，用于创建权限校验依赖。
    检查当前用户是否拥有所有必需的权限。

    工作原理：
    1. 先通过 get_current_user 获取当前用户
    2. 查询该用户拥有的所有权限（通过角色关联）
    3. 检查是否包含所有必需的权限

    使用方式：
        @app.get("/users")
        def list_users(
            user: User = Depends(require_permissions("user:view"))
        ):
            ...

        @app.post("/users")
        def create_user(
            user: User = Depends(require_permissions("user:view", "user:create"))
        ):
            ...

    Args:
        *required_permissions: 可变参数，所需的权限码列表

    Returns:
        function: 依赖函数，返回当前用户对象

    Raises:
        HTTPException: 403 当用户缺少任一必需权限时
    """

    def dependency(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        """
        实际的依赖函数

        Args:
            user: 当前用户对象
            db: 数据库会话

        Returns:
            User: 当前用户对象

        Raises:
            HTTPException: 403 权限不足
        """
        # 超级用户拥有全部权限，跳过权限查询以减少数据库访问
        if user.is_superuser:
            return user

        # 查询当前用户拥有的所有权限码
        # 通过多对多关系：User -> Role -> Permission
        permissions = set(
            db.execute(
                select(Permission.code)
                .join(Role.permissions)  # 关联角色和权限
                .join(Role.users)  # 关联角色和用户
                .where(User.id == user.id)  # 过滤当前用户
                .distinct()  # 去重，避免重复的权限码
            ).scalars()
        )

        # 检查用户是否拥有所有必需的权限
        # set(required_permissions).issubset(permissions) 表示：
        # required_permissions 中的每个元素都必须在 permissions 中
        if not set(required_permissions).issubset(permissions):
            raise HTTPException(status_code=403, detail="Permission denied")

        # 返回用户对象，方便后续使用
        return user

    # 返回依赖函数
    return dependency
