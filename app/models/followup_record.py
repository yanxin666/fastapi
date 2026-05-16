"""
跟进记录数据模型模块

定义了跟进记录（FollowupRecord）模型，用于存储用户对认领客户的跟进联系记录。
一条客户可以有多条跟进记录，关键信息是客户 ID 和用户 ID。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FollowupRecord(Base):
    """
    跟进记录模型

    存储用户对客户的跟进联系记录，采用软删除机制。
    创建跟进记录时需校验客户已被当前用户认领。
    """

    __tablename__ = "followup_records"
    """数据库表名"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """记录 ID，主键，自增"""

    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    """客户 ID，FK 到 customers 表"""

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    """创建跟进记录的用户 ID"""

    contact_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    """联系时间"""

    method: Mapped[str] = mapped_column(String(20), nullable=False)
    """跟进方式：电话/微信/面访/其他"""

    intention: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """联系后意向度"""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """跟进说明"""

    next_followup_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    """下次计划跟进时间，用于任务调度查询"""

    # ==================== 系统字段 ====================
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    """软删除标记"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    """删除时间"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    """更新时间"""
