"""用户管理：列表、详情、更新（分配角色/部门/团队）；部门/团队列表（仅 ADMIN）。"""

from fastapi import APIRouter, Depends, Query

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.exceptions import BusinessError
from app.core.response import success_json
from app.schemas.user import CurrentUser
from app.schemas.user_manage import (
    DepartmentCreate,
    TeamCreate,
    UserListItem,
    UserOptionItem,
    UserListParams,
    UserProfileResponse,
    UserProfileUpdate,
    UserListResponse,
    UserUpdateByAdmin,
)
from app.services.user_service import (
    create_department as create_department_svc,
    create_team as create_team_svc,
    get_my_profile as get_my_profile_svc,
    get_user_by_id as get_user_svc,
    list_departments as list_depts_svc,
    list_teams as list_teams_svc,
    list_user_options as list_user_options_svc,
    list_users as list_users_svc,
    update_my_profile as update_my_profile_svc,
    update_user_by_admin as update_user_svc,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("", response_class=None)
async def list_users_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    keyword: str | None = Query(None),
    role: str | None = Query(None),
):
    """用户列表：分页、关键词、角色筛选。"""
    params = UserListParams(
        page=page, page_size=page_size, keyword=keyword, role=role
    )
    items, total = await list_users_svc(session, current_user, params)
    return success_json(
        UserListResponse(
            items=[UserListItem.model_validate(i) for i in items],
            total=total,
        ).model_dump(mode="json")
    )


@router.get("/departments", response_class=None)
async def list_departments_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """部门列表（供用户分配部门下拉）。"""
    depts = await list_depts_svc(session, current_user)
    return success_json(depts)


@router.post("/departments", response_class=None)
async def create_department_api(
    payload: DepartmentCreate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    dept = await create_department_svc(session, current_user, payload.name)
    return success_json(dept)


@router.get("/teams", response_class=None)
async def list_teams_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    department_id: int | None = Query(None),
):
    """团队列表（可选按部门筛选）。"""
    teams = await list_teams_svc(session, current_user, department_id)
    return success_json(teams)


@router.post("/teams", response_class=None)
async def create_team_api(
    payload: TeamCreate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    team = await create_team_svc(
        session,
        current_user,
        payload.name,
        payload.department_id,
    )
    return success_json(team)


@router.get("/options", response_class=None)
async def list_user_options_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    keyword: str | None = Query(None),
):
    options = await list_user_options_svc(session, current_user, keyword)
    return success_json([UserOptionItem.model_validate(item).model_dump(mode="json") for item in options])


@router.get("/profile", response_class=None)
async def get_my_profile_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    profile = await get_my_profile_svc(session, current_user)
    if profile is None:
        raise BusinessError(code="NOT_FOUND", message="用户不存在")
    return success_json(UserProfileResponse.model_validate(profile).model_dump(mode="json"))


@router.patch("/profile", response_class=None)
async def update_my_profile_api(
    payload: UserProfileUpdate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    profile = await update_my_profile_svc(
        session,
        current_user,
        payload.model_dump(),
    )
    return success_json(UserProfileResponse.model_validate(profile).model_dump(mode="json"))


@router.get("/{user_id:int}", response_class=None)
async def get_user_api(
    user_id: int,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """用户详情。"""
    user = await get_user_svc(session, current_user, user_id)
    if user is None:
        raise BusinessError(code="NOT_FOUND", message="用户不存在")
    return success_json(user)


@router.patch("/{user_id:int}", response_class=None)
async def update_user_api(
    user_id: int,
    payload: UserUpdateByAdmin,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """管理员更新用户：分配角色、部门、团队（传 null 表示待分配）。仅更新请求体中出现的字段。"""
    update_data = payload.model_dump(exclude_unset=True)
    user = await update_user_svc(session, current_user, user_id, update_data)
    return success_json(user)
