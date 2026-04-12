"""
权限码定义模块

使用 StrEnum 定义所有系统权限码，
便于在代码中使用，避免硬编码字符串。
"""

from enum import StrEnum


class PermissionCode(StrEnum):
    """
    系统权限码枚举

    权限码命名规则：资源:操作
    例如：user:view 表示查看用户资源
    """

    # 用户管理相关权限
    USER_VIEW = "user:view"
    """查看用户列表和详情"""

    USER_CREATE = "user:create"
    """创建用户、编辑用户、分配角色、启用/禁用用户、重置密码"""

    # 角色管理相关权限
    ROLE_VIEW = "role:view"
    """查看角色列表和详情"""

    ROLE_CREATE = "role:create"
    """创建角色"""

    ROLE_UPDATE = "role:update"
    """更新角色信息、分配角色权限"""

    ROLE_DELETE = "role:delete"
    """删除角色"""

    # 权限管理相关权限
    PERMISSION_VIEW = "permission:view"
    """查看权限列表"""
