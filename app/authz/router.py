from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.authz.dependencies import require_permission_group
from app.authz.policy import build_default_policy_resolver, endpoint_key
from fastapi import APIRouter, Depends
from fastapi.params import Depends as DependsParam


class PolicyRouter(APIRouter):
    """根据函数级策略自动注入权限依赖，保持业务路由代码简洁。"""

    def __init__(
        self,
        *,
        strict_policy: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._strict_policy = strict_policy
        self._resolver = build_default_policy_resolver()

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        dependencies: list[DependsParam] | None = None,
        **kwargs: Any,
    ) -> None:
        merged_dependencies: list[DependsParam] = list(dependencies or [])
        endpoint_policy = self._resolver.resolve(endpoint)

        if endpoint_policy is None:
            if self._strict_policy:
                raise RuntimeError(
                    f"Missing auth policy mapping for endpoint: {endpoint_key(endpoint)}"
                )
        elif not endpoint_policy.public and endpoint_policy.permissions:
            merged_dependencies.append(
                Depends(require_permission_group(endpoint_policy.permissions))
            )

        super().add_api_route(
            path,
            endpoint,
            dependencies=merged_dependencies,
            **kwargs,
        )
