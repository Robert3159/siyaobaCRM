"""项目管理：列表、详情、新建、更新（含启用/停用）。"""

from fastapi import APIRouter, Depends, Query

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.response import success_json
from app.schemas.project import (
    ProjectCreate,
    ProjectListParams,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.schemas.user import CurrentUser
from app.services.project_service import (
    create_project,
    get_project,
    list_projects,
    update_project,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("", response_class=None)
async def list_projects_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    name: str | None = Query(None),
    enabled: bool | None = Query(None),
):
    """项目列表：分页、按名称/启用状态筛选；数据范围由后端 scope 控制。"""
    params = ProjectListParams(page=page, page_size=page_size, name=name, enabled=enabled)
    items, total = await list_projects(session, current_user, params)
    return success_json(
        ProjectListResponse(
            items=[ProjectResponse.model_validate(p) for p in items],
            total=total,
        ).model_dump(mode="json")
    )


@router.get("/{project_id}", response_class=None)
async def get_project_api(
    project_id: int,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """项目详情。"""
    project = await get_project(session, current_user, project_id)
    if project is None:
        from app.core.exceptions import BusinessError
        raise BusinessError(code="NOT_FOUND", message="项目不存在或无权访问")
    return success_json(ProjectResponse.model_validate(project).model_dump(mode="json"))


@router.post("", response_class=None)
async def create_project_api(
    payload: ProjectCreate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """新建项目；项目 ID（project_no）由后端生成。"""
    project = await create_project(session, current_user, payload)
    return success_json(ProjectResponse.model_validate(project).model_dump(mode="json"))


@router.patch("/{project_id}", response_class=None)
async def update_project_api(
    project_id: int,
    payload: ProjectUpdate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """更新项目（名称、日期、备注、启用/停用）。"""
    project = await update_project(session, current_user, project_id, payload)
    return success_json(ProjectResponse.model_validate(project).model_dump(mode="json"))
