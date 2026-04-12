"""
认证 API 模块

提供用户认证相关的接口：
1. 登录 - 获取访问令牌和刷新令牌
2. 刷新 - 使用刷新令牌获取新的访问令牌
3. 登出 - 撤销刷新令牌
4. 获取当前用户信息
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
from fastapi import APIRouter, Depends, HTTPException

# 创建路由对象，tags 用于在 OpenAPI 文档中分组
router = APIRouter(tags=["auth"])

# 路由前缀设置，使用配置中的 admin_api_prefix
router_prefix_setting = "admin_api_prefix"


class LoginRequest(BaseModel):
    """
    登录请求数据模型

    用于接收前端发送的登录请求数据
    """

    username: str
    """用户名"""
    password: str
    """密码（明文）"""


class RefreshTokenRequest(BaseModel):
    """
    刷新令牌请求数据模型

    用于接收前端发送的刷新令牌请求
    """

    refresh_token: str
    """刷新令牌"""


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录接口

    验证用户名和密码，成功后返回：
    - access_token: 访问令牌（短期有效）
    - refresh_token: 刷新令牌（长期有效）
    - token_type: 令牌类型（固定为 "bearer"）
    - user: 当前用户信息（包含角色和权限）

    Args:
        payload: 登录请求数据
        db: 数据库会话

    Returns:
        dict: 包含令牌和用户信息的字典

    Raises:
        HTTPException: 401 当用户名或密码错误时
    """
    # 根据用户名查询用户
    # scalar_one_or_none() 返回单个结果或 None
    user = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()

    # 验证用户是否存在以及密码是否正确
    # 如果用户不存在或密码验证失败，都返回 401 错误
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # 生成刷新令牌的唯一标识
    refresh_token_id = str(uuid4())

    # 获取配置
    settings = get_settings()

    # 将刷新令牌存储到数据库中
    db.add(
        RefreshToken(
            token_id=refresh_token_id,
            user_id=user.id,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_ttl_days),
        )
    )

    # 提交数据库事务
    db.commit()

    # 返回令牌和用户信息
    return {
        "access_token": create_access_token(str(user.id)),
        # 访问令牌，用于 API 认证
        "refresh_token": create_refresh_token(str(user.id), refresh_token_id),
        # 刷新令牌，用于获取新的访问令牌
        "token_type": "bearer",
        # 令牌类型
        "user": _serialize_user(user, db),
        # 用户信息（包含角色和权限）
    }


@router.post("/auth/refresh")
def refresh_access_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    刷新访问令牌接口

    使用刷新令牌获取新的访问令牌。
    为了安全起见，旧的刷新令牌会被撤销，同时生成一个新的刷新令牌。

    Args:
        payload: 刷新令牌请求数据
        db: 数据库会话

    Returns:
        dict: 包含新令牌的字典

    Raises:
        HTTPException: 401 当刷新令牌无效或已撤销时
    """
    # 获取并验证刷新令牌和对应的用户
    stored_token, user = _get_refresh_token_user(payload.refresh_token, db)

    # 撤销旧的刷新令牌
    stored_token.is_revoked = True
    stored_token.revoked_at = datetime.now(UTC)

    # 生成新的刷新令牌 ID
    new_token_id = str(uuid4())

    # 获取配置
    settings = get_settings()

    # 创建新的刷新令牌记录
    db.add(
        RefreshToken(
            token_id=new_token_id,
            user_id=user.id,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_ttl_days),
        )
    )

    # 提交数据库事务
    db.commit()

    # 返回新的访问令牌和刷新令牌
    return {
        "access_token": create_access_token(str(user.id)),
        # 新的访问令牌
        "refresh_token": create_refresh_token(str(user.id), new_token_id),
        # 新的刷新令牌
        "token_type": "bearer",
        # 令牌类型
    }


@router.post("/auth/logout")
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    用户登出接口

    撤销刷新令牌，使其无法再用于获取新的访问令牌。

    Args:
        payload: 刷新令牌请求数据
        db: 数据库会话

    Returns:
        dict: 成功标识

    Raises:
        HTTPException: 401 当刷新令牌无效时
    """
    # 获取刷新令牌记录
    stored_token, _ = _get_refresh_token_user(payload.refresh_token, db)

    # 标记刷新令牌为已撤销
    stored_token.is_revoked = True
    stored_token.revoked_at = datetime.now(UTC)

    # 提交数据库事务
    db.commit()

    # 返回成功
    return {"success": True}


@router.get("/auth/me")
def me(user_id: str = Depends(jwt_auth_dependency), db: Session = Depends(get_db)):
    """
    获取当前用户信息接口

    返回当前登录用户的详细信息，包括角色和权限列表。

    Args:
        user_id: 从 JWT token 中解析出的用户 ID
        db: 数据库会话

    Returns:
        dict: 用户信息

    Raises:
        HTTPException: 401 当 token 无效或用户不存在时
    """
    # 根据用户 ID 查询用户
    user = db.get(User, int(user_id))

    # 如果用户不存在，返回 401 错误
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 返回序列化后的用户信息
    return _serialize_user(user, db)


def _get_refresh_token_user(token: str, db: Session) -> tuple[RefreshToken, User]:
    """
    内部辅助函数：验证刷新令牌并获取对应的用户

    验证流程：
    1. 解码并验证 JWT 刷新令牌
    2. 从数据库查询刷新令牌记录
    3. 检查刷新令牌是否已被撤销
    4. 查询对应的用户并验证一致性

    Args:
        token: 刷新令牌字符串
        db: 数据库会话

    Returns:
        tuple[RefreshToken, User]: (刷新令牌记录, 用户对象)

    Raises:
        HTTPException: 401 当令牌无效、已撤销或用户不存在时
    """
    try:
        # 解码刷新令牌，期望类型是 "refresh"
        payload = decode_token(token, expected_token_type="refresh")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    # 根据 token_id 从数据库查询刷新令牌记录
    stored_token = db.execute(
        select(RefreshToken).where(RefreshToken.token_id == payload.token_id)
    ).scalar_one_or_none()

    # 检查刷新令牌是否存在且未被撤销
    if stored_token is None or stored_token.is_revoked:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 查询对应的用户
    user = db.get(User, int(payload.subject))

    # 验证用户是否存在，以及刷新令牌的 user_id 是否匹配
    if user is None or stored_token.user_id != user.id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 返回刷新令牌记录和用户对象
    return stored_token, user


def _serialize_user(user: User, db: Session) -> dict[str, object]:
    """
    内部辅助函数：序列化用户对象为字典

    包含用户的基本信息、角色列表和权限列表。

    Args:
        user: 用户对象
        db: 数据库会话

    Returns:
        dict: 序列化后的用户信息字典
    """
    # 查询用户的所有角色名称
    roles = (
        db.execute(
            select(Role.name)
            .join(User.roles)  # 关联用户和角色
            .where(User.id == user.id)  # 过滤当前用户
            .order_by(Role.name)  # 按角色名称排序
        )
        .scalars()
        .all()
    )

    # 查询用户的所有权限码（通过角色关联）
    permissions = (
        db.execute(
            select(Permission.code)
            .join(Role.permissions)  # 关联角色和权限
            .join(Role.users)  # 关联角色和用户
            .where(User.id == user.id)  # 过滤当前用户
            .distinct()  # 去重，避免重复的权限
            .order_by(Permission.code)  # 按权限码排序
        )
        .scalars()
        .all()
    )

    # 返回序列化后的用户信息
    return {
        "id": user.id,
        # 用户 ID
        "username": user.username,
        # 用户名
        "email": user.email,
        # 邮箱
        "is_active": user.is_active,
        # 账号是否激活
        "is_superuser": user.is_superuser,
        # 是否是超级用户
        "roles": roles,
        # 角色名称列表
        "permissions": permissions,
        # 权限码列表
    }
