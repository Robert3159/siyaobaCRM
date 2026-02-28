"""
写操作权限 Guard（规则书第十一章）。

- 可见 ≠ 可改 ≠ 可删，写操作必须显式调用本模块方法。
- assert_can_update：更新前校验（MEMBER 仅本人 / LEADER 本团队 / DIRECTOR 部门内非 DIRECTOR / ADMIN 全部）。
- assert_can_delete：删除前校验（MEMBER/LEADER 不可删 / DIRECTOR 仅业务数据 / ADMIN 可删）。
- assert_can_manage_system_resource：无归属的系统资源（如 Form）仅 ADMIN、SUB_ADMIN 可增删改。
"""

from typing import Protocol

from app.core.exceptions import BusinessError
from app.schemas.user import CurrentUser, Role


class _OwnedTarget(Protocol):
    """具备归属字段的目标（Project、Player、Customer 或 User 作为被更新目标）。"""

    owner_id: int
    department_id: int | None
    team_id: int | None


# 业务资源类型（用于删除权限判断）
_RESOURCE_BUSINESS = frozenset({"project", "player", "customer", "form"})


def assert_can_update(
    user: CurrentUser,
    target: _OwnedTarget,
    *,
    target_role: Role | None = None,
) -> None:
    """
    规则书 11.2：更新前校验。无权限时抛出 BusinessError PERMISSION_DENIED。

    - target：具备 owner_id、department_id、team_id 的对象（ORM 或 SimpleNamespace）。
    - target_role：仅当目标是「用户」时传入，用于「不能更新同级 LEADER」「部门内非 DIRECTOR」等判断。
    """
    if user.role == Role.ADMIN:
        return

    if user.role == Role.SUB_ADMIN:
        if user.department_id is None:
            raise BusinessError(code="PERMISSION_DENIED", message="无更新权限")
        if target.department_id != user.department_id:
            raise BusinessError(code="PERMISSION_DENIED", message="无更新权限")
        return

    if user.role in (Role.QGS_DIRECTOR, Role.HGS_DIRECTOR):
        if user.department_id is None:
            raise BusinessError(code="PERMISSION_DENIED", message="无更新权限")
        if target.department_id != user.department_id:
            raise BusinessError(code="PERMISSION_DENIED", message="无更新权限")
        if target_role is not None and target_role in (
            Role.QGS_DIRECTOR,
            Role.HGS_DIRECTOR,
        ):
            raise BusinessError(
                code="PERMISSION_DENIED",
                message="不能更新同级或更高级别角色",
            )
        return

    if user.role in (Role.QGS_LEADER, Role.HGS_LEADER):
        if user.team_id is None:
            raise BusinessError(code="PERMISSION_DENIED", message="无更新权限")
        if target.team_id != user.team_id:
            raise BusinessError(code="PERMISSION_DENIED", message="无更新权限")
        if target_role is not None and target_role in (
            Role.QGS_LEADER,
            Role.HGS_LEADER,
        ):
            raise BusinessError(
                code="PERMISSION_DENIED",
                message="不能更新同级 LEADER",
            )
        return

    if user.role in (Role.QGS_MEMBER, Role.HGS_MEMBER):
        if target.owner_id != user.id:
            raise BusinessError(code="PERMISSION_DENIED", message="不能更新他人数据")
        return

    raise BusinessError(code="PERMISSION_DENIED", message="无更新权限")


def assert_can_delete(
    user: CurrentUser,
    resource_type: str,
    target: _OwnedTarget | None = None,
) -> None:
    """
    规则书 11.3：删除前校验。默认禁止物理删除；此处仅做「是否允许执行删除操作」判断。

    - resource_type: "project" | "player" | "customer" | "form" | "user"
    - target: 业务数据时传入（用于 DIRECTOR 同部门校验）；删除用户时传被删用户或 None（仅 ADMIN 可删）。
    """
    if user.role == Role.ADMIN:
        return

    if user.role in (Role.QGS_MEMBER, Role.HGS_MEMBER):
        raise BusinessError(code="PERMISSION_DENIED", message="无删除权限")

    if user.role in (Role.QGS_LEADER, Role.HGS_LEADER):
        raise BusinessError(code="PERMISSION_DENIED", message="无删除权限")

    if user.role in (Role.QGS_DIRECTOR, Role.HGS_DIRECTOR):
        if resource_type == "user":
            raise BusinessError(code="PERMISSION_DENIED", message="仅管理员可删除用户")
        if resource_type not in _RESOURCE_BUSINESS:
            raise BusinessError(code="PERMISSION_DENIED", message="无删除权限")
        if user.department_id is None:
            raise BusinessError(code="PERMISSION_DENIED", message="无删除权限")
        if target is not None and target.department_id != user.department_id:
            raise BusinessError(code="PERMISSION_DENIED", message="仅可删除本部门数据")
        return

    if user.role == Role.SUB_ADMIN:
        if resource_type == "user":
            raise BusinessError(code="PERMISSION_DENIED", message="仅管理员可删除用户")
        if user.department_id is None:
            raise BusinessError(code="PERMISSION_DENIED", message="无删除权限")
        if target is not None and target.department_id != user.department_id:
            raise BusinessError(code="PERMISSION_DENIED", message="仅可删除本部门数据")
        return

    raise BusinessError(code="PERMISSION_DENIED", message="无删除权限")


def assert_can_manage_system_resource(user: CurrentUser) -> None:
    """
    无归属的系统资源（如 Form 表单定义）的增删改：仅 ADMIN、SUB_ADMIN 可操作。
    规则书 SUB_ADMIN「仅限被授权模块」本期按「允许管理」处理。
    """
    if user.role in (Role.ADMIN, Role.SUB_ADMIN):
        return
    raise BusinessError(
        code="PERMISSION_DENIED",
        message="仅管理员可管理该资源",
    )
