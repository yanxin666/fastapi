import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Depends, Request

# ============================================================
# 一、ContextVar（演示用，不作为主共享通道）
# ============================================================

# ⚠️ 注意：
# ContextVar 在 FastAPI 中并不能保证在所有 task 中可见，
# 这里只是演示“它能用，但不适合作为主 Context 方案”
# 仅用于演示：推荐实际业务用 request.state.ctx 代替 ContextVar
request_ctx_var: ContextVar[Optional["RequestContext"]] = ContextVar(
    "request_ctx", default=None
)


# ============================================================
# 二、RequestContext 定义（业务上下文）
# ============================================================
@dataclass
class RequestContext:
    # 请求级基础信息
    request_id: str
    start_time: float = field(default_factory=time.time)

    # 用户与权限
    user_id: Optional[int] = None
    user: Optional[dict] = None
    roles: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)

    # 环境 / 租户
    env: str = "prod"
    tenant_id: Optional[int] = None

    # 兜底扩展字段
    extra: dict = field(default_factory=dict)


# ============================================================
# 三、Context 构建入口（唯一 new 的地方）
# ============================================================
def build_request_context(request: Request) -> RequestContext:
    """
    构建请求级 Context：
    1. new Context
    2. 绑定到 request.state
    3. 顺便写入 ContextVar（仅用于演示）
    """
    ctx = RequestContext(
        request_id=request.headers.get("X-Request-ID", str(uuid.uuid4()))
    )

    # 绑定到 Request（推荐、稳定）
    request.state.ctx = ctx

    # 同时写入 ContextVar（不推荐作为主方案）
    request_ctx_var.set(ctx)

    return ctx


# ============================================================
# 四、Depends 链：逐步 enrich Context
# ============================================================
def load_user(
    ctx: RequestContext = Depends(build_request_context),
) -> RequestContext:
    """
    模拟用户加载逻辑（如从 token / session 中解析）
    """
    ctx.user_id = 1
    ctx.user = {"id": 1, "name": "Tom"}
    ctx.roles = ["admin"]
    return ctx


# 计算权限
def load_permissions(
    ctx: RequestContext = Depends(load_user),
) -> RequestContext:
    """
    根据角色计算权限
    """
    if "admin" in ctx.roles:
        ctx.permissions.update({"read", "write"})
    else:
        ctx.permissions.add("read")
    return ctx


# 加载环境 / 租户信息
def load_env(
    ctx: RequestContext = Depends(load_permissions),
) -> RequestContext:
    """
    加载环境 / 租户信息
    """
    ctx.env = "gray"
    ctx.tenant_id = 1001
    return ctx
