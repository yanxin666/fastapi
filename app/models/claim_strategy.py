"""
认领策略数据模型模块

定义了认领策略（ClaimStrategy）模型，用于控制每个用户同时认领客户的数量上限。
user_id 为 NULL 时表示系统默认策略。
"""

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ClaimStrategy(Base):
    """
    认领策略模型

    每个用户最多一条策略记录，通过 user_id 的 UNIQUE 约束保证。
    user_id=NULL 的行表示系统默认策略，查询时先查用户专属再回退到默认。
    """

    __tablename__ = "claim_strategies"
    """数据库表名"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """策略 ID，主键，自增"""

    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, unique=True, index=True,
    )
    """用户 ID，FK 到 users 表，NULL 表示系统默认策略"""

    max_claim_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50, server_default="50",
    )
    """同时认领客户数上限，默认 50"""

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )
    """更新时间"""
