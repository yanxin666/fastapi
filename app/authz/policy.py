"""
授权策略模块

定义了端点权限策略的配置和解析机制。
通过策略配置，可以灵活地控制每个 API 端点所需的权限。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.authz.codes import PermissionCode


@dataclass(frozen=True)
class EndpointPolicy:
    """
    端点权限策略数据类

    用于配置每个 API 端点的访问控制策略。

    Attributes:
        public: 是否为公开端点（不需要认证即可访问）
        permissions: 访问该端点所需的权限列表（空列表表示只需登录）
    """

    public: bool = False
    """是否为公开端点，True 表示不需要认证"""

    permissions: tuple[PermissionCode, ...] = ()
    """访问所需的权限码列表，空 tuple 表示只需要登录"""


def endpoint_key(endpoint: Callable) -> str:
    """
    生成端点的唯一标识键

    通过端点函数的模块名和限定名生成一个唯一字符串，
    用于在策略字典中查找对应的权限策略。

    Args:
        endpoint: 端点函数对象

    Returns:
        str: 端点的唯一标识，格式为 "模块名:函数名"
    """
    # 获取端点函数所在的模块名
    module_name = getattr(endpoint, "__module__", "")

    # 获取端点函数的限定名（包含类名等信息）
    # 如果没有 __qualname__，则使用 __name__
    qualname = getattr(endpoint, "__qualname__", getattr(endpoint, "__name__", ""))

    # 组合成 "模块名:限定名" 格式
    return f"{module_name}:{qualname}"


class PolicyResolver:
    """
    端点权限策略解析器

    负责根据端点函数查找对应的权限策略。
    """

    def __init__(self, endpoint_policies: dict[str, EndpointPolicy]) -> None:
        """
        初始化策略解析器

        Args:
            endpoint_policies: 端点策略字典，键是端点标识，值是策略对象
        """
        self._endpoint_policies = endpoint_policies
        """存储所有端点的权限策略"""

    def resolve(self, endpoint: Callable) -> EndpointPolicy | None:
        """
        解析端点的权限策略

        Args:
            endpoint: 端点函数对象

        Returns:
            EndpointPolicy | None: 找到的策略对象，如果没有配置则返回 None
        """
        # 先生成端点的标识键，然后在字典中查找
        return self._endpoint_policies.get(endpoint_key(endpoint))


def build_default_policy_resolver() -> PolicyResolver:
    """
    构建默认的权限策略解析器

    这里配置了系统中所有 API 端点的权限策略。
    新增端点时，需要在这里添加对应的策略配置。

    Returns:
        PolicyResolver: 配置好的策略解析器
    """
    # 端点策略字典
    # 键格式："模块名:函数名"，由 endpoint_key 函数生成
    endpoint_policies = {
        # ==================== 系统健康检查接口 ====================
        "app.api.system.health:health_check": EndpointPolicy(public=True),
        # 健康检查接口，公开访问，不需要认证
        # ==================== 用户管理接口 ====================
        "app.api.system.users:list_users": EndpointPolicy(
            permissions=(PermissionCode.USER_VIEW,)
        ),
        # 用户列表接口，需要 user:view 权限
        "app.api.system.users:get_user_detail": EndpointPolicy(
            permissions=(PermissionCode.USER_VIEW,)
        ),
        # 用户详情接口，需要 user:view 权限
        "app.api.system.users:create_user": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        # 创建用户接口，需要 user:create 权限
        "app.api.system.users:update_user": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        # 更新用户接口，需要 user:create 权限
        "app.api.system.users:assign_user_roles": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        # 分配用户角色接口，需要 user:create 权限
        "app.api.system.users:toggle_user_active": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        # 启用/禁用用户接口，需要 user:create 权限
        "app.api.system.users:reset_user_password": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        # 重置用户密码接口，需要 user:create 权限
        # ==================== 角色管理接口 ====================
        "app.api.system.roles:list_roles": EndpointPolicy(
            permissions=(PermissionCode.ROLE_VIEW,)
        ),
        # 角色列表接口，需要 role:view 权限
        "app.api.system.roles:get_role_detail": EndpointPolicy(
            permissions=(PermissionCode.ROLE_VIEW,)
        ),
        # 角色详情接口，需要 role:view 权限
        "app.api.system.roles:create_role": EndpointPolicy(
            permissions=(PermissionCode.ROLE_CREATE,)
        ),
        # 创建角色接口，需要 role:create 权限
        "app.api.system.roles:update_role": EndpointPolicy(
            permissions=(PermissionCode.ROLE_UPDATE,)
        ),
        # 更新角色接口，需要 role:update 权限
        "app.api.system.roles:delete_role": EndpointPolicy(
            permissions=(PermissionCode.ROLE_DELETE,)
        ),
        # 删除角色接口，需要 role:delete 权限
        "app.api.system.roles:assign_role_permissions": EndpointPolicy(
            permissions=(PermissionCode.ROLE_UPDATE,)
        ),
        # 分配角色权限接口，需要 role:update 权限
        # ==================== 权限管理接口 ====================
        "app.api.system.permissions:list_permissions": EndpointPolicy(
            permissions=(PermissionCode.PERMISSION_VIEW,)
        ),
        # 权限列表接口，需要 permission:view 权限
    }

    # 创建并返回策略解析器
    return PolicyResolver(endpoint_policies)
