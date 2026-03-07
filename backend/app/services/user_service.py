"""用户管理服务：用户列表、详情、管理员更新（角色/部门/团队/管理关系）。"""

from types import SimpleNamespace

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.guards import assert_can_manage_system_resource, assert_can_update
from app.models import Department, Team, User
from app.schemas.user import CurrentUser, Role
from app.schemas.user_manage import UserListParams

_DIRECTOR_ROLE_VALUES = {Role.QGS_DIRECTOR.value, Role.HGS_DIRECTOR.value}
_MANAGER_ROLE_RELATIONS: dict[str, set[str]] = {
    Role.ADMIN.value: {
        Role.SUB_ADMIN.value,
        Role.QGS_DIRECTOR.value,
        Role.QGS_LEADER.value,
        Role.QGS_MEMBER.value,
        Role.HGS_DIRECTOR.value,
        Role.HGS_LEADER.value,
        Role.HGS_MEMBER.value,
        Role.PENDING_MEMBER.value,
    },
    Role.SUB_ADMIN.value: {
        Role.QGS_DIRECTOR.value,
        Role.QGS_LEADER.value,
        Role.QGS_MEMBER.value,
        Role.HGS_DIRECTOR.value,
        Role.HGS_LEADER.value,
        Role.HGS_MEMBER.value,
        Role.PENDING_MEMBER.value,
    },
    Role.QGS_DIRECTOR.value: {Role.QGS_LEADER.value, Role.QGS_MEMBER.value, Role.PENDING_MEMBER.value},
    Role.QGS_LEADER.value: {Role.QGS_MEMBER.value, Role.PENDING_MEMBER.value},
    Role.HGS_DIRECTOR.value: {Role.HGS_LEADER.value, Role.HGS_MEMBER.value, Role.PENDING_MEMBER.value},
    Role.HGS_LEADER.value: {Role.HGS_MEMBER.value, Role.PENDING_MEMBER.value},
}


def _is_director_role(role: str | None) -> bool:
    return role in _DIRECTOR_ROLE_VALUES


def get_department_id_from_role(role: str) -> int | None:
    """从角色推断部门ID（QGS_* → 1, HGS_* → 2）"""
    if role.startswith("QGS_"):
        return 1
    elif role.startswith("HGS_"):
        return 2
    return None


def get_department_code_from_role(role: str) -> str | None:
    """从角色推断部门代码（QGS_* → QGS, HGS_* → HGS）"""
    if role.startswith("QGS_"):
        return "QGS"
    elif role.startswith("HGS_"):
        return "HGS"
    return None


def _can_manage_role(manager_role: str | None, target_role: str | None) -> bool:
    if not manager_role or not target_role:
        return False
    return target_role in _MANAGER_ROLE_RELATIONS.get(manager_role, set())


def _display_user_name(alias: str | None, user: str) -> str:
    alias_text = (alias or "").strip()
    return alias_text or user


async def resolve_user_display_name(session: AsyncSession, user_id: int) -> str | None:
    result = await session.execute(
        select(User.alias, User.user).where(
            User.id == user_id,
            User.is_deleted == False,
        )
    )
    row = result.first()
    if not row:
        return None
    return _display_user_name(row[0], row[1])


def _normalize_positive_int(raw: object, field_name: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as e:
        raise BusinessError(code="INVALID_PARAM", message=f"{field_name} 包含无效ID") from e
    if value <= 0:
        raise BusinessError(code="INVALID_PARAM", message=f"{field_name} 包含无效ID")
    return value


def _normalize_team_id_list(raw: object) -> list[int]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise BusinessError(code="INVALID_PARAM", message="managed_team_ids 必须是数组")

    team_ids: list[int] = []
    for item in raw:
        team_id = _normalize_positive_int(item, "managed_team_ids")
        if team_id not in team_ids:
            team_ids.append(team_id)
    return team_ids


def _normalize_user_id_list(raw: object, field_name: str) -> list[int]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise BusinessError(code="INVALID_PARAM", message=f"{field_name} 必须是数组")

    user_ids: list[int] = []
    for item in raw:
        user_id = _normalize_positive_int(item, field_name)
        if user_id not in user_ids:
            user_ids.append(user_id)
    return user_ids


async def _fetch_department_name_map(session: AsyncSession, dept_ids: set[int]) -> dict[int, str]:
    if not dept_ids:
        return {}
    result = await session.execute(
        select(Department.id, Department.name).where(
            Department.id.in_(dept_ids),
            Department.is_deleted == False,
        )
    )
    return {row[0]: row[1] for row in result.all()}


async def _fetch_team_name_map(session: AsyncSession, team_ids: set[int]) -> dict[int, str]:
    if not team_ids:
        return {}
    result = await session.execute(
        select(Team.id, Team.name).where(
            Team.id.in_(team_ids),
            Team.is_deleted == False,
        )
    )
    return {row[0]: row[1] for row in result.all()}


async def _fetch_user_name_map(session: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    result = await session.execute(
        select(User.id, User.alias, User.user).where(
            User.id.in_(user_ids),
            User.is_deleted == False,
        )
    )
    return {row[0]: _display_user_name(row[1], row[2]) for row in result.all()}


async def _fetch_managed_users_by_manager(
    session: AsyncSession,
    manager_ids: set[int],
) -> dict[int, list[tuple[int, str]]]:
    if not manager_ids:
        return {}
    result = await session.execute(
        select(User.id, User.manager_id, User.alias, User.user).where(
            User.manager_id.in_(manager_ids),
            User.is_deleted == False,
        )
    )
    rows = result.all()
    managed_map: dict[int, list[tuple[int, str]]] = {manager_id: [] for manager_id in manager_ids}
    for user_id, manager_id, alias, user_name in rows:
        if manager_id is None:
            continue
        managed_map.setdefault(manager_id, []).append((user_id, _display_user_name(alias, user_name)))
    for manager_id in managed_map:
        managed_map[manager_id].sort(key=lambda item: item[0])
    return managed_map


def _get_user_managed_team_ids(user: User) -> list[int]:
    return _normalize_team_id_list(user.managed_team_ids or [])


def _build_managed_team_names(managed_team_ids: list[int], team_name_map: dict[int, str]) -> list[str]:
    return [team_name_map[team_id] for team_id in managed_team_ids if team_id in team_name_map]


async def _validate_department_and_team_ids(
    session: AsyncSession,
    *,
    department_id: int | None,
    team_id: int | None,
    managed_team_ids: list[int],
) -> None:
    if department_id is not None:
        dept_exists = (
            await session.execute(
                select(Department.id).where(
                    Department.id == department_id,
                    Department.is_deleted == False,
                )
            )
        ).first()
        if dept_exists is None:
            raise BusinessError(code="NOT_FOUND", message="部门不存在")

    related_team_ids = set(managed_team_ids)
    if team_id is not None:
        related_team_ids.add(team_id)

    if not related_team_ids:
        return

    team_rows = (
        await session.execute(
            select(Team.id, Team.department_id).where(
                Team.id.in_(related_team_ids),
                Team.is_deleted == False,
            )
        )
    ).all()
    team_department_map = {row[0]: row[1] for row in team_rows}

    if len(team_department_map) != len(related_team_ids):
        raise BusinessError(code="NOT_FOUND", message="团队不存在")

    if department_id is not None:
        invalid_team_ids = [
            team_id_item
            for team_id_item, team_department_id in team_department_map.items()
            if team_department_id != department_id
        ]
        if invalid_team_ids:
            raise BusinessError(code="INVALID_PARAM", message="团队不属于所选部门")


async def _resolve_user_org_fields(
    session: AsyncSession,
    user: User,
) -> tuple[str | None, str | None, list[int], list[str]]:
    """解析用户组织字段（部门、团队）。managed_team_ids 已废弃，始终返回空数组。"""
    dept_name_map = await _fetch_department_name_map(
        session,
        {user.department_id} if user.department_id is not None else set(),
    )

    team_name_map = await _fetch_team_name_map(
        session,
        {user.team_id} if user.team_id is not None else set()
    )

    department_name = dept_name_map.get(user.department_id) if user.department_id is not None else None
    team_name = team_name_map.get(user.team_id) if user.team_id is not None else None

    return department_name, team_name, [], []  # managed_team_ids 和 managed_team_names 废弃


async def _resolve_user_management_fields(
    session: AsyncSession,
    user: User,
) -> tuple[str | None, list[int], list[str]]:
    manager_name = None
    if user.manager_id is not None:
        manager_name_map = await _fetch_user_name_map(session, {user.manager_id})
        manager_name = manager_name_map.get(user.manager_id)

    managed_map = await _fetch_managed_users_by_manager(session, {user.id})
    managed_items = managed_map.get(user.id, [])
    managed_user_ids = [item[0] for item in managed_items]
    managed_user_names = [item[1] for item in managed_items]
    return manager_name, managed_user_ids, managed_user_names


async def list_users(
    session: AsyncSession, user: CurrentUser, params: UserListParams
) -> tuple[list[dict], int]:
    """用户列表：分页、关键字、角色筛选。"""
    _ = user
    q = select(User).where(User.is_deleted == False)
    if params.keyword and params.keyword.strip():
        kw = f"%{params.keyword.strip()}%"
        q = q.where(
            or_(
                User.user.ilike(kw),
                User.email.ilike(kw),
                (User.alias.isnot(None) & User.alias.ilike(kw)),
            )
        )
    if params.role and params.role.strip():
        q = q.where(User.role == params.role.strip())

    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    q = q.offset((params.page - 1) * params.page_size).limit(params.page_size)
    users = list((await session.execute(q)).scalars().all())

    dept_ids = {u.department_id for u in users if u.department_id is not None}
    team_ids: set[int] = {u.team_id for u in users if u.team_id is not None}
    manager_ids = {u.manager_id for u in users if u.manager_id is not None}
    user_ids = {u.id for u in users}

    dept_name_map = await _fetch_department_name_map(session, dept_ids)
    team_name_map = await _fetch_team_name_map(session, team_ids)
    manager_name_map = await _fetch_user_name_map(session, manager_ids)
    managed_user_map = await _fetch_managed_users_by_manager(session, user_ids)

    items: list[dict] = []
    for u in users:
        managed_users = managed_user_map.get(u.id, [])
        items.append(
            {
                "id": u.id,
                "user": u.user,
                "alias": u.alias,
                "email": u.email,
                "role": u.role,
                "department_id": u.department_id,
                "team_id": u.team_id,
                "managed_team_ids": [],  # 废弃
                "manager_id": u.manager_id,
                "manager_name": manager_name_map.get(u.manager_id) if u.manager_id is not None else None,
                "managed_user_ids": [item[0] for item in managed_users],
                "managed_user_names": [item[1] for item in managed_users],
                "department_name": dept_name_map.get(u.department_id) if u.department_id else None,
                "team_name": team_name_map.get(u.team_id) if u.team_id else None,
                "managed_team_names": [],  # 废弃
                "is_admin": u.is_admin,
                "enabled": u.enabled,
                "created_at": u.created_at,
            }
        )

    return items, total


async def list_user_options(
    session: AsyncSession,
    user: CurrentUser,
    keyword: str | None = None,
) -> list[dict]:
    """用户选项（供用户管理中的管理关系配置使用）。"""
    _ = user
    q = select(User.id, User.user, User.alias, User.role).where(User.is_deleted == False)
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        q = q.where(
            or_(
                User.user.ilike(kw),
                (User.alias.isnot(None) & User.alias.ilike(kw)),
                User.email.ilike(kw),
            )
        )
    q = q.order_by(User.id.asc())
    rows = (await session.execute(q)).all()
    return [
        {
            "id": row[0],
            "user": row[1],
            "alias": row[2],
            "role": row[3],
        }
        for row in rows
    ]


async def _build_user_payload(session: AsyncSession, u: User) -> dict:
    department_name, team_name, managed_team_ids, managed_team_names = await _resolve_user_org_fields(session, u)
    manager_name, managed_user_ids, managed_user_names = await _resolve_user_management_fields(session, u)
    return {
        "id": u.id,
        "user": u.user,
        "alias": u.alias,
        "email": u.email,
        "role": u.role,
        "department_id": u.department_id,
        "team_id": u.team_id,
        "managed_team_ids": managed_team_ids,
        "manager_id": u.manager_id,
        "manager_name": manager_name,
        "managed_user_ids": managed_user_ids,
        "managed_user_names": managed_user_names,
        "department_name": department_name,
        "team_name": team_name,
        "managed_team_names": managed_team_names,
        "is_admin": u.is_admin,
        "enabled": u.enabled,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
    }


async def get_user_by_id(
    session: AsyncSession, current_user: CurrentUser, user_id: int
) -> dict | None:
    """获取用户详情。"""
    _ = current_user
    u = (
        await session.execute(
            select(User).where(User.id == user_id, User.is_deleted == False)
        )
    ).scalars().first()
    if not u:
        return None

    return await _build_user_payload(session, u)


async def update_user_by_admin(
    session: AsyncSession,
    current_user: CurrentUser,
    user_id: int,
    data: dict,
) -> dict:
    """管理员更新用户（角色/部门/团队/管理关系）。"""
    u = (
        await session.execute(
            select(User).where(User.id == user_id, User.is_deleted == False)
        )
    ).scalars().first()
    if not u:
        raise BusinessError(code="NOT_FOUND", message="用户不存在")

    # 保护唯一ADMIN用户
    if u.role == Role.ADMIN.value:
        admin_count = (await session.execute(
            select(func.count(User.id)).where(User.role == Role.ADMIN.value, User.is_deleted == False)
        )).scalar()
        if admin_count == 1:
            raise BusinessError(code="PERMISSION_DENIED", message="系统唯一ADMIN用户不可修改")
    
    target = SimpleNamespace(owner_id=u.id, department_id=u.department_id, team_id=u.team_id)
    assert_can_update(current_user, target, target_role=Role(u.role))

    next_role = u.role
    if "role" in data:
        role_val = data["role"]
        if role_val is not None:
            try:
                Role(role_val)
            except ValueError as e:
                raise BusinessError(code="INVALID_ROLE", message="无效角色") from e
        next_role = role_val if role_val else Role.PENDING_MEMBER.value

    # 自动从 role 推断 department_id
    next_department_id = u.department_id
    if "role" in data:
        auto_dept_id = get_department_id_from_role(next_role)
        if auto_dept_id is not None:
            next_department_id = auto_dept_id
    if "department_id" in data:
        next_department_id = data["department_id"] if data["department_id"] else None

    next_team_id = u.team_id
    if "team_id" in data:
        next_team_id = data["team_id"] if data["team_id"] else None

    # 废弃 managed_team_ids，强制设为空数组
    next_managed_team_ids = []

    next_manager_id = u.manager_id
    if "manager_id" in data:
        raw_manager_id = data["manager_id"]
        if raw_manager_id in (None, ""):
            next_manager_id = None
        else:
            next_manager_id = _normalize_positive_int(raw_manager_id, "manager_id")

    if next_manager_id == u.id:
        raise BusinessError(code="INVALID_PARAM", message="直属上级不能是自己")

    next_managed_user_ids: list[int] | None = None
    if "managed_user_ids" in data:
        next_managed_user_ids = _normalize_user_id_list(data["managed_user_ids"], "managed_user_ids")
        if u.id in next_managed_user_ids:
            raise BusinessError(code="INVALID_PARAM", message="管理对象不能包含自己")

    should_sync_managed_users = (
        "managed_user_ids" in data or next_role not in _MANAGER_ROLE_RELATIONS or next_role != u.role
    )
    if next_role not in _MANAGER_ROLE_RELATIONS:
        if next_managed_user_ids:
            raise BusinessError(code="INVALID_PARAM", message="当前角色不支持设置管理对象")
        next_managed_user_ids = []
    elif should_sync_managed_users and next_managed_user_ids is None:
        next_managed_user_ids = []

    if next_manager_id is not None:
        manager = (
            await session.execute(
                select(User).where(
                    User.id == next_manager_id,
                    User.is_deleted == False,
                )
            )
        ).scalars().first()
        if manager is None:
            raise BusinessError(code="NOT_FOUND", message="直属上级不存在")
        if not _can_manage_role(manager.role, next_role):
            raise BusinessError(code="INVALID_PARAM", message="直属上级与当前角色不匹配")
        currently_managed_ids = set(
            (
                await session.execute(
                    select(User.id).where(User.manager_id == u.id, User.is_deleted == False)
                )
            ).scalars().all()
        )
        if next_manager_id in currently_managed_ids and (
            next_managed_user_ids is None or next_manager_id in set(next_managed_user_ids)
        ):
            raise BusinessError(code="INVALID_PARAM", message="直属上级不能同时是被管理对象")

    managed_users_to_assign: list[User] = []
    target_managed_user_id_set: set[int] = set()
    if next_managed_user_ids is not None:
        target_managed_user_id_set = set(next_managed_user_ids)
        if next_manager_id is not None and next_manager_id in target_managed_user_id_set:
            raise BusinessError(code="INVALID_PARAM", message="直属上级不能同时是被管理对象")
        if target_managed_user_id_set:
            managed_users_to_assign = list(
                (
                    await session.execute(
                        select(User).where(
                            User.id.in_(target_managed_user_id_set),
                            User.is_deleted == False,
                        )
                    )
                ).scalars().all()
            )
            if len(managed_users_to_assign) != len(target_managed_user_id_set):
                raise BusinessError(code="NOT_FOUND", message="管理对象不存在")
            for managed_user in managed_users_to_assign:
                if not _can_manage_role(next_role, managed_user.role):
                    raise BusinessError(code="INVALID_PARAM", message="管理对象与当前角色不匹配")

    await _validate_department_and_team_ids(
        session,
        department_id=next_department_id,
        team_id=next_team_id,
        managed_team_ids=next_managed_team_ids,
    )

    u.role = next_role
    u.department_id = next_department_id
    u.team_id = next_team_id
    u.managed_team_ids = next_managed_team_ids
    u.manager_id = next_manager_id

    if "is_admin" in data:
        u.is_admin = data["is_admin"] is True
    if "enabled" in data:
        u.enabled = data["enabled"] is True

    if should_sync_managed_users:
        current_managed_users = list(
            (
                await session.execute(
                    select(User).where(
                        User.manager_id == u.id,
                        User.is_deleted == False,
                    )
                )
            ).scalars().all()
        )
        for managed_user in current_managed_users:
            if managed_user.id not in target_managed_user_id_set:
                managed_user.manager_id = None
        for managed_user in managed_users_to_assign:
            managed_user.manager_id = u.id

    await session.flush()
    await session.refresh(u)

    return await _build_user_payload(session, u)


async def list_departments(session: AsyncSession, user: CurrentUser) -> list[dict]:
    """部门列表（供用户分配部门下拉）。"""
    _ = user
    result = await session.execute(
        select(Department.id, Department.name).where(Department.is_deleted == False).order_by(Department.id)
    )
    return [{"id": row[0], "name": row[1]} for row in result.all()]


async def list_teams(
    session: AsyncSession, user: CurrentUser, department_id: int | None = None
) -> list[dict]:
    """团队列表（department_id 可选筛选）。"""
    _ = user
    q = select(Team.id, Team.name, Team.department_id).where(Team.is_deleted == False).order_by(Team.id)
    if department_id is not None:
        q = q.where(Team.department_id == department_id)

    result = await session.execute(q)
    return [{"id": row[0], "name": row[1], "department_id": row[2]} for row in result.all()]


async def create_department(
    session: AsyncSession,
    user: CurrentUser,
    name: str,
) -> dict:
    assert_can_manage_system_resource(user)
    dept_name = name.strip()
    if not dept_name:
        raise BusinessError(code="INVALID_PARAM", message="部门名称不能为空")

    existing = await session.execute(
        select(Department).where(
            Department.name == dept_name,
            Department.is_deleted == False,
        )
    )
    if existing.scalars().first():
        raise BusinessError(code="DEPARTMENT_EXISTS", message="部门已存在")

    dept = Department(name=dept_name, code=None)
    session.add(dept)
    await session.flush()
    await session.refresh(dept)
    return {"id": dept.id, "name": dept.name}


async def create_team(
    session: AsyncSession,
    user: CurrentUser,
    name: str,
    department_id: int,
) -> dict:
    assert_can_manage_system_resource(user)
    team_name = name.strip()
    if not team_name:
        raise BusinessError(code="INVALID_PARAM", message="团队名称不能为空")

    dept = await session.execute(
        select(Department).where(
            Department.id == department_id,
            Department.is_deleted == False,
        )
    )
    if dept.scalars().first() is None:
        raise BusinessError(code="NOT_FOUND", message="部门不存在")

    existing = await session.execute(
        select(Team).where(
            Team.name == team_name,
            Team.department_id == department_id,
            Team.is_deleted == False,
        )
    )
    if existing.scalars().first():
        raise BusinessError(code="TEAM_EXISTS", message="该部门下团队已存在")

    team = Team(name=team_name, department_id=department_id)
    session.add(team)
    await session.flush()
    await session.refresh(team)
    return {"id": team.id, "name": team.name, "department_id": team.department_id}


async def get_my_profile(session: AsyncSession, current_user: CurrentUser) -> dict | None:
    u = (
        await session.execute(
            select(User).where(User.id == current_user.id, User.is_deleted == False)
        )
    ).scalars().first()
    if not u:
        return None

    profile = await _build_user_payload(session, u)
    profile["avatar"] = u.avatar
    return profile


async def update_my_profile(
    session: AsyncSession, current_user: CurrentUser, data: dict
) -> dict:
    u = (
        await session.execute(
            select(User).where(User.id == current_user.id, User.is_deleted == False)
        )
    ).scalars().first()
    if not u:
        raise BusinessError(code="NOT_FOUND", message="用户不存在")

    new_user = str(data.get("user", "")).strip()
    new_email = str(data.get("email", "")).strip().lower()
    new_alias = data.get("alias")
    new_avatar = data.get("avatar")
    avatar_value: str | None = None

    if not new_user:
        raise BusinessError(code="INVALID_USER", message="用户名不能为空")
    if not new_email:
        raise BusinessError(code="INVALID_EMAIL", message="邮箱不能为空")

    if new_user != u.user:
        existing_user = await session.execute(
            select(User).where(
                User.user == new_user,
                User.id != current_user.id,
                User.is_deleted == False,
            )
        )
        if existing_user.scalars().first():
            raise BusinessError(code="USER_EXISTS", message="该用户名已被使用")

    if new_email != (u.email or "").strip().lower():
        existing_email = await session.execute(
            select(User).where(
                User.email == new_email,
                User.id != current_user.id,
                User.is_deleted == False,
            )
        )
        if existing_email.scalars().first():
            raise BusinessError(code="EMAIL_EXISTS", message="该邮箱已被使用")

    if isinstance(new_avatar, str) and new_avatar.strip():
        avatar_value = new_avatar.strip()
        if not avatar_value.startswith("data:image/"):
            raise BusinessError(code="INVALID_AVATAR", message="头像格式不正确")

    u.user = new_user
    u.email = new_email
    u.alias = str(new_alias).strip() if isinstance(new_alias, str) and new_alias.strip() else None
    u.avatar = avatar_value

    await session.flush()
    await session.refresh(u)

    profile = await get_my_profile(session, current_user)
    if profile is None:
        raise BusinessError(code="NOT_FOUND", message="用户不存在")
    return profile
