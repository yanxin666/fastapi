"""
权限数据种子模块

确保数据库中存在 PermissionCode 枚举中定义的所有权限码。
新增权限时，只需在 codes.py 中添加枚举值，然后运行 seed 函数即可，
无需手动编写 SQL 插入语句。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authz.codes import PermissionCode
from app.models.permission import Permission

# 权限码对应的中文描述，用于数据库中的 description 字段
# 与 PermissionCode 枚举的 docstring 保持一致
_PERMISSION_DESCRIPTIONS: dict[PermissionCode, str] = {
    PermissionCode.USER_VIEW: "查看用户列表和详情",
    PermissionCode.USER_CREATE: "创建用户、编辑用户、分配角色、启用/禁用用户、重置密码",
    PermissionCode.ROLE_VIEW: "查看角色列表和详情",
    PermissionCode.ROLE_CREATE: "创建角色",
    PermissionCode.ROLE_UPDATE: "更新角色信息、分配角色权限",
    PermissionCode.ROLE_DELETE: "删除角色",
    PermissionCode.PERMISSION_VIEW: "查看权限列表",
    PermissionCode.CUSTOMER_VIEW: "查看客户列表和详情",
    PermissionCode.CUSTOMER_CREATE: "创建客户",
    PermissionCode.CUSTOMER_UPDATE: "编辑客户",
    PermissionCode.CUSTOMER_DELETE: "删除客户（软删除）",
}


def seed_permissions(db: Session) -> list[Permission]:
    """
    同步权限码到数据库。

    - 已存在的权限码：更新描述（如果枚举注释有变化）
    - 不存在的权限码：插入新行
    - 数据库中多余的权限码：不删除（可能是历史数据或自定义权限）

    Args:
        db: 数据库会话

    Returns:
        list[Permission]: 数据库中所有权限对象
    """
    # 查询数据库中已有的权限码，避免重复插入
    existing = {p.code: p for p in db.execute(select(Permission)).scalars().all()}

    for code in PermissionCode:
        permission = existing.get(code)
        description = _PERMISSION_DESCRIPTIONS.get(code)

        if permission is None:
            # 新增权限码
            db.add(Permission(code=code, description=description))
        elif description is not None and permission.description != description:
            # 更新已有权限码的描述
            permission.description = description

    db.flush()

    return db.execute(select(Permission).order_by(Permission.id)).scalars().all()
