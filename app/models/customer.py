"""
客户数据模型模块

定义了客户（Customer）模型，用于存储客户管理系统的核心业务数据。
支持软删除（is_deleted + deleted_at），删除操作不会物理删除记录。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Customer(Base):
    """
    客户数据模型

    存储客户的基本信息、意向状态、来源归属、分配信息、咨询记录等。
    采用软删除机制，删除时设置 is_deleted=True 而非物理删除，
    以便后续数据恢复和审计追溯。
    """

    __tablename__ = "customers"
    """数据库表名"""

    # ==================== 主键 ====================
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """客户 ID，主键，自增"""

    # ==================== 认领信息 ====================
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True,
    )
    """当前认领用户 ID，FK 到 users 表，NULL 表示未被认领（公海客户）"""

    followup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    """最新跟进日期，创建跟进记录时自动更新"""

    # ==================== 基本信息 ====================
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """客户姓名"""

    phone: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    """联系电话，建索引便于按电话查询"""

    wechat: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """微信号"""

    wechat_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """微信状态，如：未添加、已加上微信"""

    qq: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """QQ号"""

    province: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """省份"""

    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """地域"""

    grade: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """年级"""

    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    """备注"""

    tag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    """标签"""

    # ==================== 意向与状态 ====================
    intention: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """意向度，如：没有咨询、不需要、无人接听等"""

    feedback_status: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    """反馈状态，如：有效、无效"""

    customer_stage: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    """客户阶段，如：回访、报名"""

    # ==================== 来源与归属 ====================
    source_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """来源名称"""

    owner: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    """归属人，建索引便于按归属人筛选"""

    primary_project: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """一级项目"""

    project: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """项目"""

    business_dept: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """事业部"""

    call_dept: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """呼叫部"""

    call_group: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """呼叫组"""

    advertiser: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """广告商"""

    landing_page: Mapped[str | None] = mapped_column(Text, nullable=True)
    """着陆页，URL 长度不可预期，使用 Text 类型"""

    # ==================== 分配信息 ====================
    assign_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """分配方式，如：手动、自动"""

    assign_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """分配类型，如：公海领取、主管调配"""

    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """分配时间"""

    creator: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """创建人"""

    creator_org: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """创建人归属机构"""

    # ==================== 咨询信息 ====================
    first_consultant: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """首次咨询师"""

    last_consultant: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """最后咨询师"""

    first_assign_org: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """首次分配归属机构"""

    first_assign_person: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """首次分配归属人"""

    first_assign_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """首次分配时间"""

    last_first_consult_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """最后一次首咨分配时间"""

    last_first_consult_person: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    """最后首咨分配归属人"""

    # ==================== 统计追踪 ====================
    registration_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    """报名次数"""

    daily_outbound_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    """当日外呼次数"""

    daily_connected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    """当日呼通次数"""

    daily_connected_duration: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    """当日接通时长（秒）"""

    ip: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """IP地址"""

    ip_province: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """IP省份"""

    ip_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """IP城市"""

    # ==================== 聊天记录 ====================
    raw_chat_records: Mapped[str | None] = mapped_column(Text, nullable=True)
    """无格式聊天记录"""

    chat_records: Mapped[str | None] = mapped_column(Text, nullable=True)
    """聊天记录"""

    # ==================== 系统字段 ====================
    original_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """原系统客户ID，用于数据迁移时保留原始标识"""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    """软删除标记，True 表示已删除，建索引便于列表查询过滤"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    """删除时间，软删除时记录"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    """创建时间，自动设置为当前时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    """更新时间，创建时自动设置，更新时自动刷新"""
