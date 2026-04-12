"""
审计日志数据模型模块

定义了审计日志（AuditLog）模型，用于记录系统中的重要操作。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AuditLog(Base):
    """
    审计日志数据模型

    用于记录系统中的重要操作，如：
    - 用户登录/登出
    - 数据的创建、修改、删除
    - 权限变更
    - 配置修改等

    审计日志是只读的，记录后不应被修改。
    """

    __tablename__ = "audit_logs"
    """数据库表名"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """审计日志 ID，主键，自增"""

    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    """
    操作名称，例如 "user.login"、"role.create"、"permission.update"
    建立索引用于按操作类型查询
    """

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    """
    操作者用户 ID，外键关联到 users 表
    可以为空（例如系统自动执行的操作）
    ondelete="SET NULL"：用户删除时，此字段设为 NULL，保留日志记录
    """

    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """资源类型，例如 "user"、"role"、"permission"，可选"""

    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """资源 ID，字符串格式，可以存储数字 ID 或 UUID，可选"""

    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    """详细信息，JSON 格式或文本格式，记录操作的详细数据，可选"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    """创建时间，自动设置为当前时间，带时区"""

    # 多对一关系：多条审计日志属于一个操作者
    actor = relationship("User", back_populates="audit_logs")
    """
    与用户的多对一关系（操作者）
    - back_populates="audit_logs": 与 User 模型中的 audit_logs 属性对应
    """
