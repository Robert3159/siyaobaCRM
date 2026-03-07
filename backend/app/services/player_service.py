import logging
from datetime import datetime

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.core.scope import build_scope_filter
from app.guards import assert_can_update
from app.models import Form, Player, Project
from app.schemas.user import CurrentUser, Role
from app.services.notification_service import QGS_AUTHOR_KEY, build_notification_message, notification_hub
from app.services.user_service import resolve_user_display_name

SERVER_CONTENT_KEYS = ("server", "server_name", "zone", "qufu", "region", "area")
HGS_MAINTAINER_KEY = "hgs_maintainer"
logger = logging.getLogger(__name__)


def _scope_conditions(model: type, scope: dict) -> list:
    return [getattr(model, key) == value for key, value in scope.items()]


async def _load_player_form_fields(session: AsyncSession) -> list[dict]:
    stmt = select(Form.fields).where(
        and_(
            Form.code == "player_form",
            Form.is_deleted == False,
            Form.enabled == True,
        )
    )
    fields = (await session.execute(stmt)).scalar_one_or_none()
    if not isinstance(fields, list):
        return []
    return [item for item in fields if isinstance(item, dict)]


async def submit_player(
    session: AsyncSession,
    user: CurrentUser,
    project_id: int,
    content: dict,
) -> Player:
    scope = build_scope_filter(user, "project")
    project_query = select(Project).where(
        and_(
            Project.id == project_id,
            Project.is_deleted == False,
            Project.enabled == True,
            *_scope_conditions(Project, scope),
        )
    )
    result = await session.execute(project_query)
    project = result.scalars().first()
    if project is None:
        raise BusinessError(code="PROJECT_NOT_FOUND", message="项目不存在或未启用")

    next_content = dict(content or {})
    submitter_alias = await resolve_user_display_name(session, user.id)
    if submitter_alias:
        next_content[QGS_AUTHOR_KEY] = submitter_alias

    player = Player(
        project_id=project_id,
        content=next_content,
        owner_id=user.id,
        department_id=user.department_id,
        team_id=user.team_id,
    )
    session.add(player)
    await session.flush()
    await session.refresh(player)

    try:
        submitter = submitter_alias or f"User-{user.id}"
        schema_fields = await _load_player_form_fields(session)
        message = build_notification_message(
            next_content,
            submitter,
            player.id,
            schema_fields=schema_fields,
        )
        await notification_hub.enqueue_message(message)
    except Exception:
        logger.exception("Failed to broadcast notification message")
    return player


async def assign_hgs_maintainer(
    session: AsyncSession,
    user: CurrentUser,
    player_id: int,
    alias: str,
) -> bool:
    if not alias:
        return False

    # Claim action is already permission-checked in websocket router.
    # Do not apply row-level visibility here; otherwise HGS roles outside
    # submitter scope cannot claim pending registrations.
    if user.role not in (
        Role.ADMIN,
        Role.SUB_ADMIN,
        Role.HGS_DIRECTOR,
        Role.HGS_LEADER,
        Role.HGS_MEMBER,
    ):
        return False

    query = select(Player).where(
        and_(
            Player.id == player_id,
            Player.is_deleted == False,
        )
    )
    player = (await session.execute(query)).scalars().first()
    if player is None:
        return False

    content = dict(player.content or {})
    existing = content.get(HGS_MAINTAINER_KEY)
    if isinstance(existing, str) and existing.strip():
        return True

    content[HGS_MAINTAINER_KEY] = alias
    player.content = content
    await session.flush()
    await session.refresh(player)
    return True


async def list_players(
    session: AsyncSession,
    user: CurrentUser,
    page: int = 1,
    page_size: int = 50,
    project_id: int | None = None,
    player_id: int | None = None,
    alias: str | None = None,
    server: str | None = None,
    keyword: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[list[Player], int]:
    scope = build_scope_filter(user, "player")
    base = and_(Player.is_deleted == False, *_scope_conditions(Player, scope))
    query = select(Player).where(base)
    if project_id is not None:
        query = query.where(Player.project_id == project_id)
    if player_id is not None:
        query = query.where(Player.id == player_id)
    if alias and alias.strip():
        alias_kw = f"%{alias.strip()}%"
        query = query.where(Player.content["alias"].astext.ilike(alias_kw))
    if server and server.strip():
        server_kw = f"%{server.strip()}%"
        server_conditions = [Player.content[key].astext.ilike(server_kw) for key in SERVER_CONTENT_KEYS]
        query = query.where(or_(*server_conditions))
    if keyword and keyword.strip():
        keyword_kw = f"%{keyword.strip()}%"
        query = query.where(
            or_(
                cast(Player.id, String).ilike(keyword_kw),
                cast(Player.project_id, String).ilike(keyword_kw),
                cast(Player.content, String).ilike(keyword_kw),
            )
        )
    if start_time is not None:
        query = query.where(Player.created_at >= start_time)
    if end_time is not None:
        query = query.where(Player.created_at <= end_time)

    total_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_stmt)).scalar() or 0

    query = query.order_by(Player.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def get_player(
    session: AsyncSession,
    user: CurrentUser,
    player_id: int,
) -> Player | None:
    scope = build_scope_filter(user, "player")
    query = select(Player).where(
        and_(
            Player.id == player_id,
            Player.is_deleted == False,
            *_scope_conditions(Player, scope),
        )
    )
    result = await session.execute(query)
    return result.scalars().first()


async def update_player(
    session: AsyncSession,
    user: CurrentUser,
    player_id: int,
    *,
    project_id: int | None = None,
    content: dict | None = None,
) -> Player:
    player = await get_player(session, user, player_id)
    if player is None:
        raise BusinessError(code="NOT_FOUND", message="玩家记录不存在或无权限访问")

    assert_can_update(user, player)

    if project_id is not None and project_id != player.project_id:
        project_scope = build_scope_filter(user, "project")
        project_query = select(Project).where(
            and_(
                Project.id == project_id,
                Project.is_deleted == False,
                Project.enabled == True,
                *_scope_conditions(Project, project_scope),
            )
        )
        project = (await session.execute(project_query)).scalars().first()
        if project is None:
            raise BusinessError(code="PROJECT_NOT_FOUND", message="项目不存在或未启用")
        player.project_id = project_id

    if content is not None:
        player.content = content

    await session.flush()
    await session.refresh(player)
    return player
