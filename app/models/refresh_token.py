"""
刷新令牌数据模型模块

定义了刷新令牌（RefreshToken）模型，用于实现 JWT 令牌的刷新机制。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class RefreshToken(Base):
    """
    刷新令牌数据模型

    刷新令牌用于在访问令牌（Access Token）过期后获取新的访问令牌。
    刷新令牌有更长的有效期，可以被主动撤销。

    为什么需要刷新令牌？
    - 访问令牌有效期短，即使泄露也风险有限
    - 刷新令牌只在刷新时使用，减少暴露机会
    - 可以通过撤销刷新令牌来强制用户重新登录
    """

    __tablename__ = "refresh_tokens"
    """数据库表名"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """刷新令牌记录 ID，主键，自增"""

    token_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    """
    令牌唯一标识（JWT ID）
    这个 ID 会被编码到 JWT token 中，用于唯一标识一个刷新令牌
    """

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    """
    用户 ID，外键关联到 users 表
    级联删除：用户删除时，其所有刷新令牌也自动删除
    """

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    """刷新令牌过期时间，带时区"""

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """撤销时间，如果被撤销则记录撤销时间，否则为 None"""

    is_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    """是否已被撤销，True 表示已撤销，False 表示有效"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    """创建时间，自动设置为当前时间，带时区"""

    # 多对一关系：多个刷新令牌属于一个用户
    user = relationship("User", back_populates="refresh_tokens")
    """
    与用户的多对一关系
    - back_populates="refresh_tokens": 与 User 模型中的 refresh_tokens 属性对应
    """
