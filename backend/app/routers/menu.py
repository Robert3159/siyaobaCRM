"""Menu management router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.response import success_json
from app.schemas.menu import MenuBatchDelete, MenuCreate, MenuItem, MenuUpdate
from app.services.menu_service import (
    batch_delete_menus as batch_delete_menus_svc,
    create_menu as create_menu_svc,
    delete_menu as delete_menu_svc,
    list_menus as list_menus_svc,
    update_menu as update_menu_svc,
)

router = APIRouter()


@router.get("/menus", response_class=None)
async def list_menus_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    menus = await list_menus_svc(session, current_user)
    return success_json([MenuItem.model_validate(item).model_dump(mode="json") for item in menus])


@router.post("/menus", response_class=None)
async def create_menu_api(
    payload: MenuCreate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    menu = await create_menu_svc(session, current_user, payload)
    return success_json(MenuItem.model_validate(menu).model_dump(mode="json"))


@router.patch("/menus/{menu_id:int}", response_class=None)
async def update_menu_api(
    menu_id: int,
    payload: MenuUpdate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    menu = await update_menu_svc(session, current_user, menu_id, payload)
    return success_json(MenuItem.model_validate(menu).model_dump(mode="json"))


@router.delete("/menus/{menu_id:int}", response_class=None)
async def delete_menu_api(
    menu_id: int,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    deleted_count = await delete_menu_svc(session, current_user, menu_id)
    return success_json({"deleted_count": deleted_count})


@router.post("/menus/batch-delete", response_class=None)
async def batch_delete_menus_api(
    payload: MenuBatchDelete,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    deleted_count = await batch_delete_menus_svc(session, current_user, payload.ids)
    return success_json({"deleted_count": deleted_count})
