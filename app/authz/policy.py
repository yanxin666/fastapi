from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.authz.codes import PermissionCode


@dataclass(frozen=True)
class EndpointPolicy:
    public: bool = False
    permissions: tuple[PermissionCode, ...] = ()


def endpoint_key(endpoint: Callable) -> str:
    module_name = getattr(endpoint, "__module__", "")
    qualname = getattr(endpoint, "__qualname__", getattr(endpoint, "__name__", ""))
    return f"{module_name}:{qualname}"


class PolicyResolver:
    def __init__(self, endpoint_policies: dict[str, EndpointPolicy]) -> None:
        self._endpoint_policies = endpoint_policies

    def resolve(self, endpoint: Callable) -> EndpointPolicy | None:
        return self._endpoint_policies.get(endpoint_key(endpoint))


def build_default_policy_resolver() -> PolicyResolver:
    endpoint_policies = {
        # system.health
        "app.api.system.health:health_check": EndpointPolicy(public=True),
        # system.users
        "app.api.system.users:list_users": EndpointPolicy(
            permissions=(PermissionCode.USER_VIEW,)
        ),
        "app.api.system.users:get_user_detail": EndpointPolicy(
            permissions=(PermissionCode.USER_VIEW,)
        ),
        "app.api.system.users:create_user": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        "app.api.system.users:update_user": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        "app.api.system.users:assign_user_roles": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        "app.api.system.users:toggle_user_active": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        "app.api.system.users:reset_user_password": EndpointPolicy(
            permissions=(PermissionCode.USER_CREATE,)
        ),
        # system.roles
        "app.api.system.roles:list_roles": EndpointPolicy(
            permissions=(PermissionCode.ROLE_VIEW,)
        ),
        "app.api.system.roles:get_role_detail": EndpointPolicy(
            permissions=(PermissionCode.ROLE_VIEW,)
        ),
        "app.api.system.roles:create_role": EndpointPolicy(
            permissions=(PermissionCode.ROLE_CREATE,)
        ),
        "app.api.system.roles:update_role": EndpointPolicy(
            permissions=(PermissionCode.ROLE_UPDATE,)
        ),
        "app.api.system.roles:delete_role": EndpointPolicy(
            permissions=(PermissionCode.ROLE_DELETE,)
        ),
        "app.api.system.roles:assign_role_permissions": EndpointPolicy(
            permissions=(PermissionCode.ROLE_UPDATE,)
        ),
        # system.permissions
        "app.api.system.permissions:list_permissions": EndpointPolicy(
            permissions=(PermissionCode.PERMISSION_VIEW,)
        ),
    }
    return PolicyResolver(endpoint_policies)
