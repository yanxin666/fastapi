"""
认领策略管理接口模块

提供认领策略的 CRUD 操作，包括：
- 列出所有策略（含系统默认策略），每条附当前认领数
- 创建策略（指定用户 + 认领上限，user_id=null 为默认策略）
- 更新策略的认领上限
- 删除策略（恢复为系统默认）
"""

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.authz.router import PolicyRouter
from app.core.db import get_db
from app.models.claim_record import ClaimRecord
from app.models.claim_strategy import ClaimStrategy
from app.models.user import User
from fastapi import Depends, HTTPException, status

router = PolicyRouter(tags=["system"])
router_prefix_setting = "admin_api_prefix"


class CreateStrategyRequest(BaseModel):
    """创建认领策略请求体"""

    user_id: int | None = None
    """用户 ID，null 表示系统默认策略"""

    max_claim_count: int
    """同时认领客户数上限"""


class UpdateStrategyRequest(BaseModel):
    """更新认领策略请求体"""

    max_claim_count: int
    """同时认领客户数上限"""


@router.get("/strategies")
def list_strategies(db: Session = Depends(get_db)):
    """
    列出所有认领策略

    返回所有策略（含系统默认策略），每条附当前该用户的已认领客户数。
    系统默认策略（user_id=NULL）排在最前面。
    """
    # 查询所有策略，默认策略排前面
    strategies = (
        db.execute(select(ClaimStrategy).order_by(ClaimStrategy.user_id.asc()))
        .scalars()
        .all()
    )

    # 批量查询每个用户当前已认领的客户数
    # 统计 claim_records 中 status=claimed 且未释放的记录数
    claim_counts = dict(
        db.execute(
            select(ClaimRecord.user_id, func.count(ClaimRecord.id))
            .where(ClaimRecord.claim_status == "claimed")
            .group_by(ClaimRecord.user_id)
        ).all()
    )

    return {
        "items": [
            _serialize_strategy(s, claim_counts.get(s.user_id, 0), db)
            for s in strategies
        ]
    }


@router.post("/strategies", status_code=status.HTTP_201_CREATED)
def create_strategy(
    payload: CreateStrategyRequest,
    db: Session = Depends(get_db),
):
    """
    创建认领策略

    - user_id=null 时创建系统默认策略（全局只能有一条）
    - user_id 为具体用户时创建用户专属策略（每个用户只能有一条）
    """
    # 校验：如果是用户专属策略，确保用户存在
    if payload.user_id is not None:
        user = db.get(User, payload.user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="用户不存在")

    # 校验：同一 user_id 不能重复创建策略
    existing = db.execute(
        select(ClaimStrategy).where(ClaimStrategy.user_id == payload.user_id)
    ).scalar_one_or_none()
    if existing is not None:
        label = (
            "系统默认策略"
            if payload.user_id is None
            else f"用户 {payload.user_id} 的策略"
        )
        raise HTTPException(status_code=409, detail=f"{label}已存在")

    # 校验：认领上限必须大于 0
    if payload.max_claim_count <= 0:
        raise HTTPException(status_code=400, detail="认领上限必须大于 0")

    strategy = ClaimStrategy(
        user_id=payload.user_id,
        max_claim_count=payload.max_claim_count,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)

    # 新创建的策略，当前认领数一定为 0
    return _serialize_strategy(strategy, 0, db)


@router.post("/strategies/{strategy_id}/update")
def update_strategy(
    strategy_id: int,
    payload: UpdateStrategyRequest,
    db: Session = Depends(get_db),
):
    """
    更新认领策略的认领上限

    只允许修改 max_claim_count，不允许修改 user_id。
    如果用户当前已认领数超过新上限，仍允许更新（但后续认领操作会被拦截）。
    """
    strategy = db.get(ClaimStrategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="策略不存在")

    # 校验：认领上限必须大于 0
    if payload.max_claim_count <= 0:
        raise HTTPException(status_code=400, detail="认领上限必须大于 0")

    strategy.max_claim_count = payload.max_claim_count
    db.commit()
    db.refresh(strategy)

    # 查询当前认领数
    current_count = (
        db.execute(
            select(func.count(ClaimRecord.id)).where(
                ClaimRecord.user_id == strategy.user_id,
                ClaimRecord.claim_status == "claimed",
            )
        ).scalar()
        or 0
    )

    return _serialize_strategy(strategy, current_count, db)


@router.post("/strategies/{strategy_id}/delete")
def delete_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
):
    """
    删除认领策略

    删除后，该用户将回退到系统默认策略（user_id=NULL 的策略）。
    不允许删除系统默认策略。
    """
    strategy = db.get(ClaimStrategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="策略不存在")

    # 不允许删除系统默认策略
    if strategy.user_id is None:
        raise HTTPException(status_code=400, detail="不允许删除系统默认策略")

    db.delete(strategy)
    db.commit()
    return {"success": True}


def _serialize_strategy(
    strategy: ClaimStrategy, current_claim_count: int, db: Session
) -> dict:
    """
    序列化认领策略为字典

    Args:
        strategy: 认领策略对象
        current_claim_count: 该策略对应用户当前已认领的客户数
        db: 数据库会话，用于查询关联用户名

    Returns:
        dict: 序列化后的策略数据
    """
    result = {
        "id": strategy.id,
        "user_id": strategy.user_id,
        "max_claim_count": strategy.max_claim_count,
        "current_claim_count": current_claim_count,
        "is_default": strategy.user_id is None,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
        "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
    }

    # 如果是用户专属策略，查询用户名
    if strategy.user_id is not None:
        user = db.get(User, strategy.user_id)
        result["username"] = user.username if user else None
    else:
        # 系统默认策略标记
        result["username"] = "系统默认"

    return result
