"""Menu management service."""

from collections import defaultdict, deque
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.guards import assert_can_manage_system_resource
from app.models import Menu
from app.schemas.menu import MenuCreate, MenuUpdate
from app.schemas.user import CurrentUser


def _normalize_text(value: str) -> str:
    return value.strip()


def _menu_to_dict(menu: Menu) -> dict:
    return {
        "id": menu.id,
        "menu_type": menu.menu_type,
        "menu_name": menu.menu_name,
        "icon": menu.icon,
        "route_name": menu.route_name,
        "route_path": menu.route_path,
        "status": menu.status,
        "hide_in_menu": menu.hide_in_menu,
        "order": menu.order,
        "parent_id": menu.parent_id,
        "children": [],
        "created_at": menu.created_at,
        "updated_at": menu.updated_at,
    }


async def _ensure_route_name_unique(
    session: AsyncSession, route_name: str, *, exclude_id: int | None = None
) -> None:
    stmt = select(Menu).where(Menu.is_deleted == False, Menu.route_name == route_name)
    if exclude_id is not None:
        stmt = stmt.where(Menu.id != exclude_id)
    existing = (await session.execute(stmt)).scalars().first()
    if existing is not None:
        raise BusinessError(code="MENU_ROUTE_NAME_EXISTS", message="route_name already exists")


async def _validate_parent_relation(
    session: AsyncSession, menu_type: int, parent_id: int | None
) -> None:
    if parent_id is None:
        if menu_type != 1:
            raise BusinessError(code="INVALID_MENU_LEVEL", message="top-level menu must be menu_type=1")
        return

    parent = (
        await session.execute(
            select(Menu).where(Menu.id == parent_id, Menu.is_deleted == False)
        )
    ).scalars().first()
    if parent is None:
        raise BusinessError(code="MENU_PARENT_NOT_FOUND", message="parent menu not found")

    if parent.menu_type >= 3:
        raise BusinessError(code="INVALID_MENU_LEVEL", message="page menu cannot have child")

    expected_type = parent.menu_type + 1
    if menu_type != expected_type:
        raise BusinessError(
            code="INVALID_MENU_LEVEL",
            message=f"invalid menu_type for parent; expected {expected_type}",
        )


async def list_menus(session: AsyncSession, _user: CurrentUser) -> list[dict]:
    stmt = (
        select(Menu)
        .where(Menu.is_deleted == False)
        .order_by(Menu.order.asc(), Menu.id.asc())
    )
    rows = list((await session.execute(stmt)).scalars().all())

    nodes: dict[int, dict] = {row.id: _menu_to_dict(row) for row in rows}
    roots: list[dict] = []

    for row in rows:
        node = nodes[row.id]
        if row.parent_id is not None and row.parent_id in nodes:
            nodes[row.parent_id]["children"].append(node)
        else:
            roots.append(node)

    def _sort_tree(items: list[dict]) -> None:
        items.sort(key=lambda x: (x["order"], x["id"]))
        for item in items:
            if item["children"]:
                _sort_tree(item["children"])

    _sort_tree(roots)
    return roots


async def create_menu(
    session: AsyncSession, user: CurrentUser, payload: MenuCreate
) -> dict:
    assert_can_manage_system_resource(user)

    menu_name = _normalize_text(payload.menu_name)
    route_name = _normalize_text(payload.route_name)
    route_path = _normalize_text(payload.route_path)
    icon = _normalize_text(payload.icon) if isinstance(payload.icon, str) else None

    await _validate_parent_relation(session, payload.menu_type, payload.parent_id)
    await _ensure_route_name_unique(session, route_name)

    menu = Menu(
        menu_type=payload.menu_type,
        menu_name=menu_name,
        icon=icon if icon else None,
        route_name=route_name,
        route_path=route_path,
        status=payload.status,
        hide_in_menu=payload.hide_in_menu,
        order=payload.order,
        parent_id=payload.parent_id,
    )
    session.add(menu)
    await session.flush()
    await session.refresh(menu)
    return _menu_to_dict(menu)


async def update_menu(
    session: AsyncSession, user: CurrentUser, menu_id: int, payload: MenuUpdate
) -> dict:
    assert_can_manage_system_resource(user)

    menu = (
        await session.execute(
            select(Menu).where(Menu.id == menu_id, Menu.is_deleted == False)
        )
    ).scalars().first()
    if menu is None:
        raise BusinessError(code="MENU_NOT_FOUND", message="menu not found")

    data = payload.model_dump(exclude_unset=True)

    if "menu_name" in data and data["menu_name"] is not None:
        menu.menu_name = _normalize_text(data["menu_name"])
    if "icon" in data:
        icon = data["icon"]
        menu.icon = _normalize_text(icon) if isinstance(icon, str) and icon.strip() else None
    if "route_name" in data and data["route_name"] is not None:
        route_name = _normalize_text(data["route_name"])
        await _ensure_route_name_unique(session, route_name, exclude_id=menu.id)
        menu.route_name = route_name
    if "route_path" in data and data["route_path"] is not None:
        menu.route_path = _normalize_text(data["route_path"])
    if "status" in data and data["status"] is not None:
        menu.status = bool(data["status"])
    if "hide_in_menu" in data and data["hide_in_menu"] is not None:
        menu.hide_in_menu = bool(data["hide_in_menu"])
    if "order" in data and data["order"] is not None:
        menu.order = int(data["order"])

    await session.flush()
    await session.refresh(menu)
    return _menu_to_dict(menu)


def _collect_descendant_ids(all_menus: list[Menu], root_ids: set[int]) -> set[int]:
    children_map: dict[int, list[int]] = defaultdict(list)
    existing_ids = set()
    for menu in all_menus:
        existing_ids.add(menu.id)
        if menu.parent_id is not None:
            children_map[menu.parent_id].append(menu.id)

    queue = deque([menu_id for menu_id in root_ids if menu_id in existing_ids])
    collected: set[int] = set()
    while queue:
        current_id = queue.popleft()
        if current_id in collected:
            continue
        collected.add(current_id)
        for child_id in children_map.get(current_id, []):
            if child_id not in collected:
                queue.append(child_id)
    return collected


async def delete_menu(session: AsyncSession, user: CurrentUser, menu_id: int) -> int:
    assert_can_manage_system_resource(user)

    rows = list(
        (
            await session.execute(select(Menu).where(Menu.is_deleted == False))
        ).scalars().all()
    )
    delete_ids = _collect_descendant_ids(rows, {menu_id})
    if not delete_ids:
        raise BusinessError(code="MENU_NOT_FOUND", message="menu not found")

    now = datetime.utcnow()
    for row in rows:
        if row.id in delete_ids:
            row.is_deleted = True
            row.deleted_at = now

    await session.flush()
    return len(delete_ids)


async def batch_delete_menus(
    session: AsyncSession, user: CurrentUser, menu_ids: list[int]
) -> int:
    assert_can_manage_system_resource(user)

    target_ids = {menu_id for menu_id in menu_ids if menu_id > 0}
    if not target_ids:
        return 0

    rows = list(
        (
            await session.execute(select(Menu).where(Menu.is_deleted == False))
        ).scalars().all()
    )
    delete_ids = _collect_descendant_ids(rows, target_ids)
    if not delete_ids:
        return 0

    now = datetime.utcnow()
    for row in rows:
        if row.id in delete_ids:
            row.is_deleted = True
            row.deleted_at = now

    await session.flush()
    return len(delete_ids)
