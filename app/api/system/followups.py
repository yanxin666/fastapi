"""
跟进记录管理接口模块

提供跟进记录的查询、创建、删除操作，包括：
- 按客户 ID 查询跟进记录列表（分页，按联系时间倒序）
- 创建跟进记录（需校验客户已被当前用户认领或拥有调配权限）
- 软删除跟进记录
"""

from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.authz.codes import PermissionCode
from app.authz.router import PolicyRouter
from app.core.db import get_db
from app.middleware.jwt import get_current_user
from app.models.customer import Customer
from app.models.followup_record import FollowupRecord
from app.models.user import User
from fastapi import Depends, HTTPException, Query, status

router = PolicyRouter(tags=["system"])
router_prefix_setting = "admin_api_prefix"


class CreateFollowupRequest(BaseModel):
    """创建跟进记录请求体"""

    customer_id: int
    """客户 ID"""

    contact_time: datetime
    """联系时间"""

    method: str
    """跟进方式：电话/微信/面访/其他"""

    intention: str | None = None
    """联系后意向度"""

    notes: str | None = None
    """跟进说明"""

    next_followup_time: datetime | None = None
    """下次计划跟进时间"""


@router.get("/followups")
def list_followups(
    customer_id: int = Query(..., description="客户 ID，必填"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """
    跟进记录列表接口

    - 按客户 ID 查询该客户的跟进记录
    - 默认过滤已软删除的记录（is_deleted=False）
    - 按联系时间倒序排列
    - 后端分页，返回 items + total
    """
    # 基础查询：仅查询未删除的记录
    query = select(FollowupRecord).where(
        FollowupRecord.customer_id == customer_id,
        FollowupRecord.is_deleted.is_(False),
    )

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()

    # 分页查询，按联系时间倒序
    items_query = (
        query.order_by(FollowupRecord.contact_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    records = db.execute(items_query).scalars().all()

    # 批量查询创建人用户名，避免 N+1
    user_ids = {r.user_id for r in records if r.user_id is not None}
    user_names = {}
    if user_ids:
        user_names = dict(
            db.execute(
                select(User.id, User.username).where(User.id.in_(user_ids))
            ).all()
        )

    return {
        "items": [_serialize_followup(r, user_names) for r in records],
        "total": total,
    }


@router.post("/followups", status_code=status.HTTP_201_CREATED)
def create_followup(
    payload: CreateFollowupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建跟进记录接口

    校验规则：
    - 客户必须存在且未软删除
    - 客户必须被当前用户认领，或当前用户拥有 customer:assign 权限
    """
    # 验证客户存在且未删除
    customer = db.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    if customer.is_deleted:
        raise HTTPException(status_code=400, detail="已删除的客户不能创建跟进记录")

    # 校验跟进权限：客户被当前用户认领，或拥有调配权限
    is_owner = customer.user_id == current_user.id
    has_assign_perm = _has_permission(db, current_user, PermissionCode.CUSTOMER_ASSIGN)
    if not is_owner and not has_assign_perm and not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="只能为自己认领的客户创建跟进记录")

    # 创建跟进记录
    record = FollowupRecord(
        customer_id=payload.customer_id,
        user_id=current_user.id,
        contact_time=payload.contact_time,
        method=payload.method,
        intention=payload.intention,
        notes=payload.notes,
        next_followup_time=payload.next_followup_time,
    )
    db.add(record)

    # 同步更新客户的最新跟进日期
    customer.followup_at = payload.contact_time

    db.commit()
    db.refresh(record)

    # 序列化时需要当前用户名
    user_names = {current_user.id: current_user.username}
    return _serialize_followup(record, user_names)


@router.post("/followups/{followup_id}/delete")
def delete_followup(
    followup_id: int,
    db: Session = Depends(get_db),
):
    """
    软删除跟进记录接口

    不物理删除记录，而是设置 is_deleted=True 和 deleted_at=当前时间。
    已软删除的记录重复删除返回错误。
    """
    record = db.get(FollowupRecord, followup_id)
    if record is None:
        raise HTTPException(status_code=404, detail="跟进记录不存在")

    # 防止重复删除
    if record.is_deleted:
        raise HTTPException(status_code=400, detail="跟进记录已被删除")

    # 软删除
    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}


def _has_permission(db: Session, user: User, permission_code: str) -> bool:
    """
    检查用户是否拥有指定权限码

    超级用户直接返回 True，普通用户通过角色关联查询权限。

    Args:
        db: 数据库会话
        user: 用户对象
        permission_code: 权限码字符串

    Returns:
        bool: 是否拥有该权限
    """
    if user.is_superuser:
        return True

    from app.models.permission import Permission
    from app.models.role import Role

    result = db.execute(
        select(Permission.id)
        .join(Role.permissions)
        .join(Role.users)
        .where(User.id == user.id, Permission.code == permission_code)
        .limit(1)
    ).scalar_one_or_none()

    return result is not None


def _serialize_followup(
    record: FollowupRecord, user_names: dict[int, str] | None = None
) -> dict:
    """
    序列化跟进记录为字典

    Args:
        record: 跟进记录对象
        user_names: 用户名映射 {user_id: username}，批量传入避免 N+1

    Returns:
        dict: 序列化后的跟进记录数据
    """
    return {
        "id": record.id,
        "customer_id": record.customer_id,
        "user_id": record.user_id,
        "username": user_names.get(record.user_id) if user_names and record.user_id else None,
        "contact_time": record.contact_time.isoformat() if record.contact_time else None,
        "method": record.method,
        "intention": record.intention,
        "notes": record.notes,
        "next_followup_time": (
            record.next_followup_time.isoformat() if record.next_followup_time else None
        ),
        "is_deleted": record.is_deleted,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
