from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.core.scope import build_scope_filter
from app.guards import assert_can_update
from app.models import Department, Project, Team
from app.schemas.project import ProjectCreate, ProjectListParams, ProjectUpdate
from app.schemas.user import CurrentUser


async def _generate_project_no(session: AsyncSession) -> str:
    prefix = f"P-{datetime.utcnow().strftime('%Y%m')}-"
    count_stmt = select(func.count(Project.id)).where(
        Project.project_no.like(f"{prefix}%"),
        Project.is_deleted == False,
    )
    result = await session.execute(count_stmt)
    cnt = result.scalar() or 0
    return f"{prefix}{int(cnt) + 1:03d}"


def _scope_conditions(model: type, scope: dict) -> list:
    return [getattr(model, key) == value for key, value in scope.items()]


def _normalize_datetime_for_db(value: datetime | None) -> datetime | None:
    """Normalize payload datetime to TIMESTAMP WITHOUT TIME ZONE (naive UTC)."""
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


async def list_projects(
    session: AsyncSession,
    user: CurrentUser,
    params: ProjectListParams,
) -> tuple[list[Project], int]:
    scope = build_scope_filter(user, "project")
    base = and_(Project.is_deleted == False, *_scope_conditions(Project, scope))
    query = select(Project).where(base)

    if params.name:
        query = query.where(Project.name.ilike(f"%{params.name}%"))
    if params.enabled is not None:
        query = query.where(Project.enabled == params.enabled)

    total_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_stmt)).scalar() or 0

    query = query.order_by(Project.id.desc())
    query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def get_project(
    session: AsyncSession,
    user: CurrentUser,
    project_id: int,
) -> Project | None:
    scope = build_scope_filter(user, "project")
    query = select(Project).where(
        and_(
            Project.id == project_id,
            Project.is_deleted == False,
            *_scope_conditions(Project, scope),
        )
    )
    result = await session.execute(query)
    return result.scalars().first()


async def create_project(
    session: AsyncSession,
    user: CurrentUser,
    payload: ProjectCreate,
) -> Project:
    dept_id = user.department_id
    team_id = user.team_id

    if dept_id is None:
        first_dept = (
            await session.execute(
                select(Department).where(Department.is_deleted == False).limit(1)
            )
        ).scalars().first()
        if first_dept is not None:
            dept_id = first_dept.id

    if team_id is None:
        first_team = (
            await session.execute(
                select(Team).where(Team.is_deleted == False).limit(1)
            )
        ).scalars().first()
        if first_team is not None:
            team_id = first_team.id

    project = Project(
        project_no=await _generate_project_no(session),
        name=payload.name,
        date=_normalize_datetime_for_db(payload.date),
        remark=payload.remark,
        enabled=True,
        owner_id=user.id,
        department_id=dept_id,
        team_id=team_id,
    )
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project


async def update_project(
    session: AsyncSession,
    user: CurrentUser,
    project_id: int,
    payload: ProjectUpdate,
) -> Project:
    project = await get_project(session, user, project_id)
    if project is None:
        raise BusinessError(code="NOT_FOUND", message="项目不存在或无权访问")
    assert_can_update(user, project)

    if payload.name is not None:
        project.name = payload.name
    if payload.date is not None:
        project.date = _normalize_datetime_for_db(payload.date)
    if payload.remark is not None:
        project.remark = payload.remark
    if payload.enabled is not None:
        project.enabled = payload.enabled

    await session.flush()
    await session.refresh(project)
    return project
