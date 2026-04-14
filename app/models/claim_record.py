"""
认领记录数据模型模块

定义了认领记录（ClaimRecord）模型，用于追踪客户的认领、释放、调配历史。
每条记录代表一次认领状态变更事件，customers.user_id 是当前状态的冗余快照。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ClaimRecord(Base):
    """
    认领记录模型

    记录客户的认领状态变更历史，支持：
    - claimed：用户从公海认领
    - released：用户释放认领
    - assigned：主管调配给指定用户
    """

    __tablename__ = "claim_records"
    """数据库表名"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """记录 ID，主键，自增"""

    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    """客户 ID，FK 到 customers 表"""

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False,
    )
    """认领用户 ID，FK 到 users 表"""

    claim_status: Mapped[str] = mapped_column(String(20), nullable=False)
    """认领状态：claimed（已认领）/ released（已释放）/ assigned（已调配）"""

    claim_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    """认领/调配发生时间"""

    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    """释放时间，仍被认领时为 NULL"""

    assigned_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    """调配人用户 ID，仅 claim_status=assigned 时有值"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    """记录创建时间"""
