"""
客户管理 API 路由模块

提供客户数据的 CRUD 接口，支持：
- 列表查询（分页、关键词搜索、状态/阶段/认领状态筛选）
- 详情查看
- 创建客户
- 编辑客户
- 软删除客户（设置 is_deleted=True，不物理删除）
- 认领/批量认领客户
- 释放/批量释放认领
- 主管调配客户
"""

from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.authz.router import PolicyRouter
from app.core.db import get_db
from app.middleware.jwt import get_current_user
from app.models.claim_record import ClaimRecord
from app.models.claim_strategy import ClaimStrategy
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


class BatchClaimRequest(BaseModel):
    """批量认领请求"""

    customer_ids: list[int]
    """要认领的客户 ID 列表"""


class BatchReleaseRequest(BaseModel):
    """批量释放认领请求"""

    customer_ids: list[int]
    """要释放认领的客户 ID 列表"""


class AssignCustomerRequest(BaseModel):
    """主管调配客户请求"""

    target_user_id: int
    """目标用户 ID，将客户调配给该用户"""


# ==================== API 端点 ====================


@router.get("/customers")
def list_customers(
    keyword: str | None = Query(None, description="关键词搜索（姓名/电话）"),
    feedback_status: str | None = Query(None, description="反馈状态筛选"),
    customer_stage: str | None = Query(None, description="客户阶段筛选"),
    customer_tag: str | None = Query(None, description="客户标签筛选"),
    claim_status: str | None = Query(
        None, description="认领状态筛选：unclaimed(公海)/claimed(已认领)/possession(长期客户)"
    ),
    claimed_by: int | None = Query(None, description="按认领用户 ID 筛选"),
    intention: str | None = Query(None, description="意向筛选"),
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
    - 支持按认领状态筛选：unclaimed(公海)、claimed(已认领)
    - 支持按认领用户 ID 筛选
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
        query = query.where(Customer.feedback_status == feedback_status)  # 确保类型一致

    # 客户阶段筛选
    if customer_stage:
        query = query.where(Customer.customer_stage == customer_stage)  # 确保类型一致

    # 客户标签筛选
    if customer_tag:
        query = query.where(Customer.tag == customer_tag)  # 确保类型一致

    # 认领状态筛选
    if claim_status == "unclaimed":
        # 公海客户：claim_status 为 NULL
        query = query.where(Customer.claim_status.is_(None))
    elif claim_status == "claimed":
        # 已认领客户（不含长期客户）
        query = query.where(Customer.claim_status == "claimed")
    elif claim_status == "possession":
        # 长期客户
        query = query.where(Customer.claim_status == "possession")

    # 按认领用户筛选
    if claimed_by is not None:
        query = query.where(Customer.user_id == claimed_by)  # 确保类型一致

    if intention is not None:
        query = query.where(Customer.intention == intention)  # 确保类型一致

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

    # 批量查询认领人用户名，避免 N+1 查询
    claim_user_ids = {c.user_id for c in customers if c.user_id is not None}
    claim_user_names = {}
    if claim_user_ids:
        claim_user_names = dict(
            db.execute(
                select(User.id, User.username).where(User.id.in_(claim_user_ids))
            ).all()
        )

    return {
        "items": [
            _serialize_customer(c, current_user, claim_user_names) for c in customers
        ],
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

    # 详情接口单独查询认领人用户名
    claim_user_names = None
    if customer.user_id is not None:
        claim_user = db.get(User, customer.user_id)
        if claim_user:
            claim_user_names = {customer.user_id: claim_user.username}

    return _serialize_customer(customer, current_user, claim_user_names)


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


# ==================== 认领/释放/调配接口 ====================


def _get_claim_limit(db: Session, user_id: int) -> int:
    """
    获取用户的认领上限

    查询策略的回退逻辑：先查用户专属策略 → 再查系统默认策略 → 代码默认值 50

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        int: 认领上限
    """
    # 先查用户专属策略
    user_strategy = db.execute(
        select(ClaimStrategy).where(ClaimStrategy.user_id == user_id)
    ).scalar_one_or_none()

    if user_strategy is not None:
        return user_strategy.max_claim_count

    # 再查系统默认策略
    default_strategy = db.execute(
        select(ClaimStrategy).where(ClaimStrategy.user_id.is_(None))
    ).scalar_one_or_none()

    if default_strategy is not None:
        return default_strategy.max_claim_count

    # 代码默认值
    return 50


def _get_current_claim_count(db: Session, user_id: int) -> int:
    """
    获取用户当前已认领的客户数

    统计 claim_records 中 status=claimed 的记录数。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        int: 当前已认领数量
    """
    return (
        db.execute(
            select(func.count(ClaimRecord.id)).where(
                ClaimRecord.user_id == user_id,
                or_(
                    ClaimRecord.claim_status == "claimed",
                    ClaimRecord.claim_status == "possession"
                ),
            )
        ).scalar()
        or 0
    )


@router.post("/customers/{customer_id}/claim")
def claim_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    认领单个客户

    逻辑：
    1. 验证客户未被认领且未软删除
    2. 查询认领策略上限
    3. 检查当前用户是否已达上限
    4. 事务中：插入 claim_record + 更新 customers.user_id + 更新 assign_type
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 验证客户未被软删除
    if customer.is_deleted:
        raise HTTPException(status_code=400, detail="已删除的客户不能认领")

    # 验证客户未被认领
    if customer.user_id is not None:
        raise HTTPException(status_code=400, detail="该客户已被认领")

    # 检查认领上限
    claim_limit = _get_claim_limit(db, current_user.id)
    current_count = _get_current_claim_count(db, current_user.id)
    if current_count >= claim_limit:
        raise HTTPException(
            status_code=400,
            detail=f"已达到认领上限（{claim_limit}），无法继续认领",
        )

    # 执行认领：插入认领记录 + 更新客户表
    now = datetime.now(timezone.utc)
    claim_record = ClaimRecord(
        customer_id=customer_id,
        user_id=current_user.id,
        claim_status="claimed",
        claim_time=now,
    )
    db.add(claim_record)

    # 冗余更新 customers.user_id，加速"我的客户"查询
    customer.user_id = current_user.id
    customer.claim_status = "claimed"
    # 更新分配类型为公海领取
    customer.assign_type = "公海领取"
    customer.assigned_at = now

    db.commit()
    db.refresh(customer)
    return _serialize_customer(customer, current_user)


@router.post("/customers/batch-claim")
def batch_claim_customers(
    payload: BatchClaimRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量认领客户

    逐个认领，返回成功和失败的明细。
    部分成功时不会回滚已成功的部分。
    """
    # 先检查认领上限，避免无意义的逐个尝试
    claim_limit = _get_claim_limit(db, current_user.id)
    current_count = _get_current_claim_count(db, current_user.id)
    remaining_quota = claim_limit - current_count

    success_ids = []
    failed = []

    for cid in payload.customer_ids:
        # 检查是否还有剩余配额
        if remaining_quota <= 0:
            failed.append({"id": cid, "reason": "已达到认领上限"})
            continue

        customer = db.get(Customer, cid)
        if customer is None:
            failed.append({"id": cid, "reason": "客户不存在"})
            continue

        if customer.is_deleted:
            failed.append({"id": cid, "reason": "已删除的客户不能认领"})
            continue

        if customer.user_id is not None:
            failed.append({"id": cid, "reason": "已被认领"})
            continue

        # 执行认领
        now = datetime.now(timezone.utc)
        claim_record = ClaimRecord(
            customer_id=cid,
            user_id=current_user.id,
            claim_status="claimed",
            claim_time=now,
        )
        db.add(claim_record)
        customer.user_id = current_user.id
        customer.claim_status = "claimed"
        customer.assign_type = "公海领取"
        customer.assigned_at = now

        success_ids.append(cid)
        remaining_quota -= 1

    db.commit()
    return {"success": success_ids, "failed": failed}


@router.post("/customers/{customer_id}/release")
def release_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    释放单个认领

    逻辑：
    1. 验证客户被当前用户认领
    2. 事务中：更新 claim_record(status=released) + 设置 customers.user_id=NULL
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 验证客户被当前用户认领
    if customer.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="只能释放自己认领的客户")

    # 执行释放：更新释放记录
    now = datetime.now(timezone.utc)  # 使用 UTC 时间
    db.query(ClaimRecord).filter(
        ClaimRecord.customer_id == customer_id,
        ClaimRecord.user_id == current_user.id,
    ).update(
        {
            ClaimRecord.claim_status: "released",
            ClaimRecord.released_at: now,
        }
    )

    # 清除冗余的 user_id，客户回到公海
    customer.user_id = None
    customer.claim_status = None
    customer.assign_type = None
    customer.assigned_at = None

    # 提交事务
    db.commit()
    db.refresh(customer)
    return _serialize_customer(customer, current_user)


@router.post("/customers/batch-release")
def batch_release_customers(
    payload: BatchReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量释放认领

    逐个释放，返回成功和失败的明细。
    """
    success_ids = []
    failed = []

    for cid in payload.customer_ids:
        customer = db.get(Customer, cid)
        if customer is None:
            failed.append({"id": cid, "reason": "客户不存在"})
            continue

        if customer.user_id != current_user.id:
            failed.append({"id": cid, "reason": "只能释放自己认领的客户"})
            continue

        # 执行释放
        now = datetime.now(timezone.utc)
        claim_record = ClaimRecord(
            customer_id=cid,
            user_id=current_user.id,
            claim_status="released",
            claim_time=now,
            released_at=now,
        )
        db.add(claim_record)
        customer.user_id = None
        customer.claim_status = None
        customer.assign_type = None
        customer.assigned_at = None

        success_ids.append(cid)

    db.commit()
    return {"success": success_ids, "failed": failed}


@router.post("/customers/{customer_id}/assign")
def assign_customer(
    customer_id: int,
    payload: AssignCustomerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    主管调配客户给指定用户

    逻辑：
    1. 验证目标用户存在且活跃
    2. 检查目标用户认领上限
    3. 如客户已被认领，先为原用户创建 released 记录
    4. 事务中：插入 claim_record(status=assigned) + 更新 customers.user_id
    """
    # 验证目标用户存在且活跃
    target_user = db.get(User, payload.target_user_id)
    if target_user is None:
        raise HTTPException(status_code=400, detail="目标用户不存在")
    if not target_user.is_active:
        raise HTTPException(status_code=400, detail="目标用户已被禁用")

    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 验证客户未被软删除
    if customer.is_deleted:
        raise HTTPException(status_code=400, detail="已删除的客户不能调配")

    # 检查目标用户认领上限（统计目标用户当前认领数，排除本客户如果已属于目标用户）
    claim_limit = int(_get_claim_limit(db, target_user.id))  # 显式转换为 int
    target_claim_count = int(_get_current_claim_count(db, target_user.id))  # 显式转换为 int
    # 如果客户已被目标用户认领，不需要额外配额
    if customer.user_id != target_user.id and target_claim_count >= claim_limit:
        raise HTTPException(
            status_code=400,
            detail=f"目标用户已达到认领上限（{claim_limit}），无法调配",
        )

    now = datetime.now(timezone.utc)

    # 如果客户已被其他人认领，先为原用户创建 released 记录
    if customer.user_id is not None and customer.user_id != target_user.id:
        old_user_id = customer.user_id
        release_record = ClaimRecord(
            customer_id=customer_id,
            user_id=int(old_user_id),  # 显式转换为 int
            claim_status="released",
            claim_time=now,
            released_at=now,
        )
        db.add(release_record)

    # 为目标用户创建 assigned 记录
    claim_record = ClaimRecord(
        customer_id=customer_id,
        user_id=int(target_user.id),  # 显式转换为 int
        claim_status="assigned",
        claim_time=now,
        assigned_by=current_user.id,
    )
    db.add(claim_record)

    # 更新客户表的冗余字段
    customer.user_id = target_user.id
    customer.claim_status = "claimed"
    customer.assign_type = "主管调配"
    customer.assigned_at = now

    db.commit()
    db.refresh(customer)
    return _serialize_customer(customer, current_user)

@router.post("/customers/{customer_id}/possession")
def claim_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    占有单个客户

    逻辑：
    1. 验证客户被认领且未软删除
    2. 查询认领策略上限
    3. 检查当前用户是否已达上限
    4. 事务中：更新 claim_record + 更新 customers.user_id
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 验证客户未被软删除
    if customer.is_deleted:
        raise HTTPException(status_code=400, detail="已删除的客户不能认领")

    # 验证客户未被认领
    if customer.user_id is None:
        raise HTTPException(status_code=400, detail="该客户未被认领")
    if customer.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="只能占有自己认领的客户")

    # 检查认领上限
    claim_limit = _get_claim_limit(db, current_user.id)
    current_count = _get_current_claim_count(db, current_user.id)
    if current_count >= claim_limit:
        raise HTTPException(
            status_code=400,
            detail=f"已达到认领上限（{claim_limit}），无法继续认领",
        )

    # 执行认领：插入认领记录 + 更新客户表
    now = datetime.now(timezone.utc)
    db.query(ClaimRecord).filter(
        ClaimRecord.customer_id == customer_id,
        ClaimRecord.user_id == current_user.id,
        ClaimRecord.claim_status == "claimed",
    ).update(
        {
            ClaimRecord.claim_status: "possession",
            ClaimRecord.claim_time: now,
        }
    )

    # 冗余更新 customers.user_id，加速"我的客户"查询
    customer.user_id = current_user.id
    # 锁定客户：更新认领状态为 possession
    customer.claim_status = "possession"
    # 更新分配类型为公海领取
    customer.assign_type = "公海领取"
    customer.assigned_at = now

    db.commit()
    db.refresh(customer)
    return _serialize_customer(customer, current_user)

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


def _serialize_customer(
    customer: Customer,
    current_user: User,
    claim_user_names: dict[int, str] | None = None,
) -> dict[str, object]:
    """
    客户数据序列化

    输出所有字段的扁平 JSON，前端可直接使用。
    datetime 类型转为 ISO 格式字符串。
    非超级管理员的手机号脱敏展示，保护敏感信息。
    新增认领相关字段：user_id、claim_status、claim_user_name。

    Args:
        customer: 客户对象
        current_user: 当前请求用户，用于判断手机号脱敏
        claim_user_names: 认领人用户名映射 {user_id: username}，列表接口批量传入避免 N+1
    """
    # 超级管理员看原始手机号，其他用户看脱敏后的
    # phone_value = (
    #     customer.phone if current_user.is_superuser else _mask_phone(customer.phone)
    # )

    # 认领人用户名：优先从批量映射取，否则单独查询（详情接口场景）
    claim_user_name = None
    if customer.user_id is not None:
        if claim_user_names and customer.user_id in claim_user_names:
            claim_user_name = claim_user_names[customer.user_id]

    return {
        "id": customer.id,
        # 认领信息
        "user_id": customer.user_id,
        "claim_status": customer.claim_status or "unclaimed",
        "claim_user_name": claim_user_name,
        "followup_at": (
            customer.followup_at.isoformat() if customer.followup_at else None
        ),
        # 基本信息
        "name": customer.name,
        "phone": customer.phone,
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
