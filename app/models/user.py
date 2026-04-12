"""
用户数据模型模块

定义了用户（User）模型，存储系统用户的基本信息。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, false, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.role import user_roles


class User(Base):
    """
    用户数据模型

    存储系统用户的核心信息，包括：
    - 登录凭据（用户名、邮箱、密码哈希）
    - 账号状态（是否激活、是否是超级用户）
    - 时间戳（创建时间、更新时间）
    """

    __tablename__ = "users"
    """数据库表名"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """用户 ID，主键，自增"""

    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    """用户名，唯一，不能为空，建立索引用于快速查询"""

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    """邮箱地址，唯一，不能为空，建立索引用于快速查询"""

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    """密码哈希值，不存储原始密码，只存储哈希后的结果"""

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    """账号是否激活，默认为 True，server_default 是数据库层面的默认值"""

    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    """是否是超级用户，超级用户拥有所有权限，默认为 False"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    """创建时间，自动设置为当前时间，带时区"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    """更新时间，自动设置为当前时间，更新记录时自动更新为当前时间"""

    # 多对多关系：一个用户可以有多个角色
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    """
    与角色的多对多关系
    - secondary=user_roles: 使用 user_roles 关联表
    - back_populates="users": 与 Role 模型中的 users 属性对应
    """

    # 一对多关系：一个用户可以有多个刷新令牌
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    """
    与刷新令牌的一对多关系
    - back_populates="user": 与 RefreshToken 模型中的 user 属性对应
    - cascade="all, delete-orphan": 级联操作，删除用户时同时删除其所有刷新令牌
    """

    # 一对多关系：一个用户可以有多条审计日志
    audit_logs = relationship("AuditLog", back_populates="actor")
    """
    与审计日志的一对多关系
    - back_populates="actor": 与 AuditLog 模型中的 actor 属性对应
    """
