"""角色管理：列表、权限选项、获取/更新角色权限（仅 ADMIN）。"""

from fastapi import APIRouter, Depends

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.response import success_json
from app.schemas.role import (
    PermissionOption,
    RoleDetailResponse,
    RoleItem,
    RoleUpdateRequest,
    RolePermissionsResponse,
    RolePermissionsUpdate,
)
from app.services.role_service import (
    get_role_detail as get_role_detail_svc,
    get_permission_options as get_options_svc,
    get_role_permissions as get_perms_svc,
    list_roles as list_roles_svc,
    update_role as update_role_svc,
    update_role_permissions as update_perms_svc,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/roles", response_class=None)
async def list_roles_api(current_user: CurrentUserDepRequired):
    """角色列表（固定枚举 + 展示名）。"""
    roles = await list_roles_svc(current_user)
    return success_json([RoleItem.model_validate(r) for r in roles])


@router.get("/permission-options", response_class=None)
async def get_permission_options_api(current_user: CurrentUserDepRequired):
    """权限选项列表（供角色权限勾选）。"""
    options = await get_options_svc(current_user)
    return success_json([PermissionOption.model_validate(o) for o in options])


@router.get("/roles/{role}/permissions", response_class=None)
async def get_role_permissions_api(
    role: str,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """获取某角色的权限列表。"""
    perms = await get_perms_svc(session, current_user, role)
    return success_json(
        RolePermissionsResponse(role=role, permissions=perms).model_dump()
    )


@router.get("/roles/{role}", response_class=None)
async def get_role_detail_api(
    role: str,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    detail = await get_role_detail_svc(session, current_user, role)
    return success_json(RoleDetailResponse.model_validate(detail).model_dump(mode="json"))


@router.put("/roles/{role}", response_class=None)
async def update_role_api(
    role: str,
    payload: RoleUpdateRequest,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    detail = await update_role_svc(
        session,
        current_user,
        role,
        payload.permissions,
        payload.home_route,
    )
    return success_json(RoleDetailResponse.model_validate(detail).model_dump(mode="json"))


@router.put("/roles/{role}/permissions", response_class=None)
async def update_role_permissions_api(
    role: str,
    payload: RolePermissionsUpdate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """更新某角色的权限（全量替换）。"""
    perms = await update_perms_svc(
        session, current_user, role, payload.permissions
    )
    return success_json(
        RolePermissionsResponse(role=role, permissions=perms).model_dump()
    )
