"""
权限数据模型模块

定义了权限（Permission）模型，权限是系统中最小的权限控制单元。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.role import role_permissions


class Permission(Base):
    """
    权限数据模型

    权限是系统中最小的权限控制单元，通过权限码（code）来标识。
    权限通常以 "资源:操作" 的格式命名，例如：
    - user:view（查看用户）
    - user:create（创建用户）
    - role:update（更新角色）

    权限不直接分配给用户，而是通过角色进行间接分配。
    """

    __tablename__ = "permissions"
    """数据库表名"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """权限 ID，主键，自增"""

    code: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    """权限码，唯一标识一个权限，例如 "user:view"，不能为空，建立索引"""

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """权限描述，可选，用于说明权限的用途"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    """创建时间，自动设置为当前时间，带时区"""

    # 多对多关系：一个权限可以分配给多个角色
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )
    """
    与角色的多对多关系
    - secondary=role_permissions: 使用 role_permissions 关联表
    - back_populates="permissions": 与 Role 模型中的 permissions 属性对应
    """
