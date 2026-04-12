"""
角色数据模型模块

定义了角色（Role）模型以及相关的多对多关联表：
- user_roles: 用户-角色关联表
- role_permissions: 角色-权限关联表
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# 用户-角色多对多关联表
# 这是一个关联表，用于实现用户和角色之间的多对多关系
# 一个用户可以拥有多个角色，一个角色也可以分配给多个用户
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    # 用户 ID，外键关联到 users 表，级联删除：用户删除时，关联记录也自动删除
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    # 角色 ID，外键关联到 roles 表，级联删除：角色删除时，关联记录也自动删除
)


# 角色-权限多对多关联表
# 这是一个关联表，用于实现角色和权限之间的多对多关系
# 一个角色可以拥有多个权限，一个权限也可以分配给多个角色
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    # 角色 ID，外键关联到 roles 表，级联删除
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # 权限 ID，外键关联到 permissions 表，级联删除
)


class Role(Base):
    """
    角色数据模型

    角色用于分组管理权限，然后将角色分配给用户。
    通过角色，可以灵活地管理用户的权限集合。
    """

    __tablename__ = "roles"
    """数据库表名"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """角色 ID，主键，自增"""

    name: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    """角色名称，唯一，不能为空，建立索引用于快速查询"""

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """角色描述，可选，用于说明角色的用途"""

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

    # 多对多关系：一个角色可以有多个用户
    users = relationship("User", secondary=user_roles, back_populates="roles")
    """
    与用户的多对多关系
    - secondary=user_roles: 使用 user_roles 关联表
    - back_populates="roles": 与 User 模型中的 roles 属性对应
    """

    # 多对多关系：一个角色可以有多个权限
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    """
    与权限的多对多关系
    - secondary=role_permissions: 使用 role_permissions 关联表
    - back_populates="roles": 与 Permission 模型中的 roles 属性对应
    """
