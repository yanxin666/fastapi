"""
客户管理 API 路由模块

提供客户数据的 CRUD 接口，支持：
- 列表查询（分页、关键词搜索、状态/阶段筛选）
- 详情查看
- 创建客户
- 编辑客户
- 软删除客户（设置 is_deleted=True，不物理删除）
"""

from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.authz.router import PolicyRouter
from app.core.db import get_db
from app.middleware.jwt import get_current_user
from app.models.customer import Customer
from app.models.user import User
from fastapi import Depends, HTTPException, Query, status

router = PolicyRouter(tags=["system"])
router_prefix_setting = "admin_api_prefix"


# ==================== 请求模型 ====================

# 创建/编辑时可更新的字段（业务字段，不含系统字段如 is_deleted、created_at 等）
_CUSTOMER_EDITABLE_FIELDS = [
    "name",
    "phone",
    "wechat",
    "wechat_status",
    "qq",
    "province",
    "region",
    "grade",
    "remark",
    "tag",
    "intention",
    "feedback_status",
    "customer_stage",
    "source_name",
    "owner",
    "primary_project",
    "project",
    "business_dept",
    "call_dept",
    "call_group",
    "advertiser",
    "landing_page",
    "assign_method",
    "assign_type",
    "assigned_at",
    "creator",
    "creator_org",
    "first_consultant",
    "last_consultant",
    "first_assign_org",
    "first_assign_person",
    "first_assign_time",
    "last_first_consult_time",
    "last_first_consult_person",
    "registration_count",
    "daily_outbound_count",
    "daily_connected_count",
    "daily_connected_duration",
    "ip",
    "ip_province",
    "ip_city",
    "raw_chat_records",
    "chat_records",
    "original_id",
]


class CreateCustomerRequest(BaseModel):
    """创建客户请求，所有业务字段均可选"""

    name: str | None = None
    phone: str | None = None
    wechat: str | None = None
    wechat_status: str | None = None
    qq: str | None = None
    province: str | None = None
    region: str | None = None
    grade: str | None = None
    remark: str | None = None
    tag: str | None = None
    intention: str | None = None
    feedback_status: str | None = None
    customer_stage: str | None = None
    source_name: str | None = None
    owner: str | None = None
    primary_project: str | None = None
    project: str | None = None
    business_dept: str | None = None
    call_dept: str | None = None
    call_group: str | None = None
    advertiser: str | None = None
    landing_page: str | None = None
    assign_method: str | None = None
    assign_type: str | None = None
    assigned_at: datetime | None = None
    creator: str | None = None
    creator_org: str | None = None
    first_consultant: str | None = None
    last_consultant: str | None = None
    first_assign_org: str | None = None
    first_assign_person: str | None = None
    first_assign_time: datetime | None = None
    last_first_consult_time: datetime | None = None
    last_first_consult_person: str | None = None
    registration_count: int | None = None
    daily_outbound_count: int | None = None
    daily_connected_count: int | None = None
    daily_connected_duration: int | None = None
    ip: str | None = None
    ip_province: str | None = None
    ip_city: str | None = None
    raw_chat_records: str | None = None
    chat_records: str | None = None
    original_id: str | None = None


class UpdateCustomerRequest(BaseModel):
    """编辑客户请求，字段同创建"""

    name: str | None = None
    phone: str | None = None
    wechat: str | None = None
    wechat_status: str | None = None
    qq: str | None = None
    province: str | None = None
    region: str | None = None
    grade: str | None = None
    remark: str | None = None
    tag: str | None = None
    intention: str | None = None
    feedback_status: str | None = None
    customer_stage: str | None = None
    source_name: str | None = None
    owner: str | None = None
    primary_project: str | None = None
    project: str | None = None
    business_dept: str | None = None
    call_dept: str | None = None
    call_group: str | None = None
    advertiser: str | None = None
    landing_page: str | None = None
    assign_method: str | None = None
    assign_type: str | None = None
    assigned_at: datetime | None = None
    creator: str | None = None
    creator_org: str | None = None
    first_consultant: str | None = None
    last_consultant: str | None = None
    first_assign_org: str | None = None
    first_assign_person: str | None = None
    first_assign_time: datetime | None = None
    last_first_consult_time: datetime | None = None
    last_first_consult_person: str | None = None
    registration_count: int | None = None
    daily_outbound_count: int | None = None
    daily_connected_count: int | None = None
    daily_connected_duration: int | None = None
    ip: str | None = None
    ip_province: str | None = None
    ip_city: str | None = None
    raw_chat_records: str | None = None
    chat_records: str | None = None
    original_id: str | None = None


# ==================== API 端点 ====================


@router.get("/customers")
def list_customers(
    keyword: str | None = Query(None, description="关键词搜索（姓名/电话）"),
    feedback_status: str | None = Query(None, description="反馈状态筛选"),
    customer_stage: str | None = Query(None, description="客户阶段筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    客户列表接口

    - 默认过滤已软删除的记录（is_deleted=False）
    - 支持按姓名/电话关键词模糊搜索
    - 支持按反馈状态、客户阶段筛选
    - 后端分页，返回 items + total
    - 非超级管理员手机号脱敏展示
    """
    # 基础查询：仅查询未删除的记录
    query = select(Customer).where(Customer.is_deleted.is_(False))

    # 关键词搜索：姓名或电话模糊匹配
    if keyword:
        query = query.where(
            or_(
                Customer.name.ilike(f"%{keyword}%"),
                Customer.phone.ilike(f"%{keyword}%"),
            )
        )

    # 反馈状态筛选
    if feedback_status:
        query = query.where(Customer.feedback_status == feedback_status)

    # 客户阶段筛选
    if customer_stage:
        query = query.where(Customer.customer_stage == customer_stage)

    # 计算总数（在分页前）
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()

    # 分页查询，按创建时间倒序
    items_query = (
        query.order_by(Customer.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    customers = db.execute(items_query).scalars().all()

    return {
        "items": [_serialize_customer(c, current_user) for c in customers],
        "total": total,
    }


@router.get("/customers/{customer_id}")
def get_customer_detail(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    客户详情接口

    返回客户的所有字段，包括已软删除的客户也可以查看详情。
    非超级管理员手机号脱敏展示。
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return _serialize_customer(customer, current_user)


@router.post("/customers", status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CreateCustomerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建客户接口

    仅设置请求中非 None 的字段，其余使用数据库默认值。
    """
    # 仅提取请求中显式传入的字段，忽略未传的 None
    data = payload.model_dump(exclude_none=True)
    customer = Customer(**data)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return _serialize_customer(customer, current_user)


@router.post("/customers/{customer_id}/update")
def update_customer(
    customer_id: int,
    payload: UpdateCustomerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    编辑客户接口

    仅更新请求中显式传入的字段，未传的字段保持不变。
    已软删除的客户不允许编辑。
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 已软删除的客户不允许编辑
    if customer.is_deleted:
        raise HTTPException(status_code=400, detail="已删除的客户不能编辑")

    # 仅更新请求中显式传入的字段
    data = payload.model_dump(exclude_none=True)
    for field, value in data.items():
        if field in _CUSTOMER_EDITABLE_FIELDS:
            setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return _serialize_customer(customer, current_user)


@router.post("/customers/{customer_id}/delete")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
):
    """
    软删除客户接口

    不物理删除记录，而是设置 is_deleted=True 和 deleted_at=当前时间。
    已软删除的客户重复删除返回错误。
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 防止重复删除
    if customer.is_deleted:
        raise HTTPException(status_code=400, detail="客户已被删除")

    # 软删除：设置标记和删除时间
    customer.is_deleted = True
    customer.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}


# ==================== 序列化函数 ====================


def _mask_phone(phone: str | None) -> str | None:
    """
    手机号脱敏处理

    规则：保留前 3 位和后 4 位，中间用 **** 替换。
    如 18912341234 → 189****1234。
    不足 7 位的号码不脱敏（非标准手机号格式），直接返回原值。
    """
    if not phone or len(phone) < 7:
        return phone
    return phone[:3] + "****" + phone[-4:]


def _serialize_customer(customer: Customer, current_user: User) -> dict[str, object]:
    """
    客户数据序列化

    输出所有字段的扁平 JSON，前端可直接使用。
    datetime 类型转为 ISO 格式字符串。
    非超级管理员的手机号脱敏展示，保护敏感信息。
    """
    # 超级管理员看原始手机号，其他用户看脱敏后的
    phone_value = (
        customer.phone if current_user.is_superuser else _mask_phone(customer.phone)
    )

    return {
        "id": customer.id,
        # 基本信息
        "name": customer.name,
        "phone": phone_value,
        "wechat": customer.wechat,
        "wechat_status": customer.wechat_status,
        "qq": customer.qq,
        "province": customer.province,
        "region": customer.region,
        "grade": customer.grade,
        "remark": customer.remark,
        "tag": customer.tag,
        # 意向与状态
        "intention": customer.intention,
        "feedback_status": customer.feedback_status,
        "customer_stage": customer.customer_stage,
        # 来源与归属
        "source_name": customer.source_name,
        "owner": customer.owner,
        "primary_project": customer.primary_project,
        "project": customer.project,
        "business_dept": customer.business_dept,
        "call_dept": customer.call_dept,
        "call_group": customer.call_group,
        "advertiser": customer.advertiser,
        "landing_page": customer.landing_page,
        # 分配信息
        "assign_method": customer.assign_method,
        "assign_type": customer.assign_type,
        "assigned_at": (
            customer.assigned_at.isoformat() if customer.assigned_at else None
        ),
        "creator": customer.creator,
        "creator_org": customer.creator_org,
        # 咨询信息
        "first_consultant": customer.first_consultant,
        "last_consultant": customer.last_consultant,
        "first_assign_org": customer.first_assign_org,
        "first_assign_person": customer.first_assign_person,
        "first_assign_time": (
            customer.first_assign_time.isoformat()
            if customer.first_assign_time
            else None
        ),
        "last_first_consult_time": (
            customer.last_first_consult_time.isoformat()
            if customer.last_first_consult_time
            else None
        ),
        "last_first_consult_person": customer.last_first_consult_person,
        # 统计追踪
        "registration_count": customer.registration_count,
        "daily_outbound_count": customer.daily_outbound_count,
        "daily_connected_count": customer.daily_connected_count,
        "daily_connected_duration": customer.daily_connected_duration,
        "ip": customer.ip,
        "ip_province": customer.ip_province,
        "ip_city": customer.ip_city,
        # 聊天记录
        "raw_chat_records": customer.raw_chat_records,
        "chat_records": customer.chat_records,
        # 系统字段
        "original_id": customer.original_id,
        "is_deleted": customer.is_deleted,
        "deleted_at": customer.deleted_at.isoformat() if customer.deleted_at else None,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
    }
