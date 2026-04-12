from enum import StrEnum


class PermissionCode(StrEnum):
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    ROLE_VIEW = "role:view"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    PERMISSION_VIEW = "permission:view"
