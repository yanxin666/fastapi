from collections.abc import Iterable

from app.authz.codes import PermissionCode
from app.middleware.jwt import require_permissions


def require_permission_group(group: Iterable[PermissionCode]):
    # 复用既有鉴权依赖，统一把枚举转换成权限码字符串
    return require_permissions(*(permission.value for permission in group))
