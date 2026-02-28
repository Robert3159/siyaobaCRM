"""Role management service."""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models import Menu, RolePermission, SystemRole
from app.schemas.user import CurrentUser, Role

ROLE_LABELS: dict[str, str] = {
    "ADMIN": "超级管理员",
    "SUB_ADMIN": "子管理员",
    "QGS_DIRECTOR": "前端主管",
    "QGS_LEADER": "前端组长",
    "QGS_MEMBER": "前端成员",
    "HGS_DIRECTOR": "后端主管",
    "HGS_LEADER": "后端组长",
    "HGS_MEMBER": "后端成员",
    "PENDING_MEMBER": "待审核成员",
}

PERMISSION_OPTIONS: list[tuple[str, str]] = [
    ("dashboard_overall", "控制台"),
    ("dashboard_qgs", "前端看板"),
    ("dashboard_hgs", "后端看板"),
    ("qgs_submit", "提交注册"),
    ("qgs_list", "玩家列表"),
    ("qgs_statistics", "数据统计"),
    ("hgs_list", "玩家列表"),
    ("hgs_order", "订单列表"),
    ("hgs_statistics", "数据统计"),
    ("business_project", "项目管理"),
    ("business_schema", "表单管理"),
    ("system_user", "用户管理"),
    ("system_role", "角色管理"),
    ("system_log", "操作日志"),
    ("system_profile", "个人中心"),
    ("system_menu", "菜单管理"),
    ("system_permission", "权限设置")
]

ENTRY_ROLES_FOR_DISPLAY = [
    Role.ADMIN,
    Role.SUB_ADMIN,
    Role.QGS_DIRECTOR,
    Role.QGS_LEADER,
    Role.QGS_MEMBER,
    Role.HGS_DIRECTOR,
    Role.HGS_LEADER,
    Role.HGS_MEMBER,
]


def _validate_role(role: str) -> None:
    try:
        Role(role)
    except ValueError as e:
        raise BusinessError(code="INVALID_ROLE", message="无效角色") from e


def _dedupe_permissions(permissions: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for permission_code in permissions:
        if permission_code in seen:
            continue
        seen.add(permission_code)
        result.append(permission_code)
    return result


def _validate_permissions(permissions: list[str]) -> list[str]:
    valid_codes = {item[0] for item in PERMISSION_OPTIONS}
    deduped = _dedupe_permissions(permissions)
    for permission_code in deduped:
        if permission_code not in valid_codes:
            raise BusinessError(
                code="INVALID_PERMISSION",
                message=f"无效权限码: {permission_code}",
            )
    return deduped


def _menu_node(menu: Menu) -> dict:
    return {
        "id": menu.id,
        "menu_type": menu.menu_type,
        "menu_name": menu.menu_name,
        "route_name": menu.route_name,
        "route_path": menu.route_path,
        "parent_id": menu.parent_id,
        "children": [],
    }


def _build_access_snapshot(
    menus: list[Menu], permission_set: set[str]
) -> tuple[list[dict], list[str]]:
    if not menus:
        return [], []

    menu_by_id = {menu.id: menu for menu in menus}
    children_map: dict[int, list[int]] = defaultdict(list)
    root_ids: list[int] = []

    for menu in menus:
        if menu.parent_id and menu.parent_id in menu_by_id:
            children_map[menu.parent_id].append(menu.id)
        else:
            root_ids.append(menu.id)

    for child_ids in children_map.values():
        child_ids.sort(key=lambda menu_id: (menu_by_id[menu_id].order, menu_id))
    root_ids.sort(key=lambda menu_id: (menu_by_id[menu_id].order, menu_id))

    authorized_ids = {
        menu.id
        for menu in menus
        if menu.route_name in permission_set
    }
    if not authorized_ids:
        return [], []

    include_ids = set(authorized_ids)
    for menu_id in list(authorized_ids):
        current = menu_by_id[menu_id]
        while current.parent_id is not None and current.parent_id in menu_by_id:
            include_ids.add(current.parent_id)
            current = menu_by_id[current.parent_id]

    nodes = {
        menu_id: _menu_node(menu_by_id[menu_id])
        for menu_id in include_ids
    }
    roots: list[dict] = []

    for menu_id in include_ids:
        menu = menu_by_id[menu_id]
        node = nodes[menu_id]
        if menu.parent_id and menu.parent_id in nodes:
            nodes[menu.parent_id]["children"].append(node)
        else:
            roots.append(node)

    def _sort_tree(items: list[dict]) -> None:
        items.sort(key=lambda item: (menu_by_id[item["id"]].order, item["id"]))
        for item in items:
            if item["children"]:
                _sort_tree(item["children"])

    _sort_tree(roots)

    available_home_routes: list[str] = []
    seen_routes: set[str] = set()

    def _collect_home_routes(item: dict) -> None:
        menu = menu_by_id[item["id"]]
        is_leaf = len(children_map.get(menu.id, [])) == 0
        if menu.id in authorized_ids and (menu.menu_type == 3 or is_leaf):
            route_name = menu.route_name
            if route_name not in seen_routes:
                seen_routes.add(route_name)
                available_home_routes.append(route_name)

        for child in item["children"]:
            _collect_home_routes(child)

    for root in roots:
        _collect_home_routes(root)

    return roots, available_home_routes


async def _list_active_menus(session: AsyncSession) -> list[Menu]:
    result = await session.execute(
        select(Menu)
        .where(Menu.is_deleted == False, Menu.status == True)
        .order_by(Menu.order.asc(), Menu.id.asc())
    )
    return list(result.scalars().all())


async def _get_role_permissions(
    session: AsyncSession, role: str
) -> list[str]:
    result = await session.execute(
        select(RolePermission.permission_code)
        .where(RolePermission.role_name == role)
        .order_by(RolePermission.id.asc())
    )
    return list(result.scalars().all())  # type: ignore[arg-type]


async def _get_role_setting(
    session: AsyncSession, role: str
) -> SystemRole | None:
    result = await session.execute(
        select(SystemRole).where(SystemRole.role_name == role)
    )
    return result.scalars().first()


async def _set_role_home_route(
    session: AsyncSession, role: str, home_route: str | None
) -> datetime | None:
    setting = await _get_role_setting(session, role)
    if setting is None:
        if home_route is None:
            return None
        setting = SystemRole(role_name=role, home_route=home_route)
        session.add(setting)
    else:
        setting.home_route = home_route

    await session.flush()
    await session.refresh(setting)
    return setting.updated_at


def _normalize_home_route(home_route: str | None) -> str | None:
    if home_route is None:
        return None
    normalized = home_route.strip()
    return normalized or None


async def list_roles(_user: CurrentUser) -> list[dict]:
    return [
        {"role": role.value, "label": ROLE_LABELS.get(role.value, role.value)}
        for role in ENTRY_ROLES_FOR_DISPLAY
    ]


async def get_permission_options(_user: CurrentUser) -> list[dict]:
    return [{"code": code, "label": label} for code, label in PERMISSION_OPTIONS]


async def get_role_detail(
    session: AsyncSession, _user: CurrentUser, role: str
) -> dict:
    _validate_role(role)

    permissions = await _get_role_permissions(session, role)
    permission_set = set(permissions)
    menus = await _list_active_menus(session)
    menu_tree, available_home_routes = _build_access_snapshot(menus, permission_set)

    setting = await _get_role_setting(session, role)
    configured_home_route = _normalize_home_route(
        setting.home_route if setting else None
    )
    home_route = (
        configured_home_route
        if configured_home_route in set(available_home_routes)
        else None
    )

    return {
        "role": role,
        "label": ROLE_LABELS.get(role, role),
        "permissions": permissions,
        "home_route": home_route,
        "available_home_routes": available_home_routes,
        "menu_tree": menu_tree,
        "updated_at": setting.updated_at if setting else None,
    }


async def update_role(
    session: AsyncSession,
    _user: CurrentUser,
    role: str,
    permissions: list[str],
    home_route: str | None,
) -> dict:
    _validate_role(role)
    validated_permissions = _validate_permissions(permissions)
    validated_home_route = _normalize_home_route(home_route)

    menus = await _list_active_menus(session)
    menu_tree, available_home_routes = _build_access_snapshot(
        menus, set(validated_permissions)
    )
    available_home_route_set = set(available_home_routes)

    if (
        validated_home_route is not None
        and validated_home_route not in available_home_route_set
    ):
        raise BusinessError(
            code="INVALID_HOME_ROUTE",
            message="首页路由必须属于该角色已授权且可访问的菜单路由",
        )

    await session.execute(
        delete(RolePermission).where(RolePermission.role_name == role)
    )
    for permission_code in validated_permissions:
        session.add(
            RolePermission(role_name=role, permission_code=permission_code)
        )

    updated_at = await _set_role_home_route(session, role, validated_home_route)

    return {
        "role": role,
        "label": ROLE_LABELS.get(role, role),
        "permissions": validated_permissions,
        "home_route": validated_home_route,
        "available_home_routes": available_home_routes,
        "menu_tree": menu_tree,
        "updated_at": updated_at,
    }


async def get_role_permissions(
    session: AsyncSession, user: CurrentUser, role: str
) -> list[str]:
    detail = await get_role_detail(session, user, role)
    return detail["permissions"]


async def update_role_permissions(
    session: AsyncSession, user: CurrentUser, role: str, permissions: list[str]
) -> list[str]:
    detail = await get_role_detail(session, user, role)
    updated = await update_role(
        session,
        user,
        role,
        permissions,
        detail["home_route"],
    )
    return updated["permissions"]


async def get_role_auth_profile(
    session: AsyncSession, role: str
) -> dict:
    _validate_role(role)
    permissions = await _get_role_permissions(session, role)
    menus = await _list_active_menus(session)
    _, available_home_routes = _build_access_snapshot(menus, set(permissions))

    setting = await _get_role_setting(session, role)
    configured_home_route = _normalize_home_route(
        setting.home_route if setting else None
    )
    home_route = (
        configured_home_route
        if configured_home_route in set(available_home_routes)
        else None
    )

    return {
        "home_route": home_route,
        "available_home_routes": available_home_routes,
    }

