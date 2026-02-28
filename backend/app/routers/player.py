"""玩家/提交记录：提交（POST）、列表（GET）；后端只控制数据行范围。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.response import success_json
from app.schemas.player import PlayerListResponse, PlayerResponse, PlayerSubmit, PlayerUpdate
from app.schemas.user import CurrentUser
from app.services.player_service import list_players, submit_player, update_player
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("", response_class=None)
async def submit_player_api(
    payload: PlayerSubmit,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """qgs_submit 提交：project_id + content（与 player_form 字段对应）。"""
    player = await submit_player(
        session,
        current_user,
        payload.project_id,
        payload.content,
    )
    return success_json(PlayerResponse.model_validate(player).model_dump(mode="json"))


@router.get("", response_class=None)
async def list_players_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    project_id: int | None = Query(None),
    player_id: int | None = Query(None),
    alias: str | None = Query(None),
    server: str | None = Query(None),
    keyword: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
):
    """玩家列表：分页、可选 project_id；数据行范围由后端 scope 控制，列可见性由前端控制。"""
    items, total = await list_players(
        session,
        current_user,
        page=page,
        page_size=page_size,
        project_id=project_id,
        player_id=player_id,
        alias=alias,
        server=server,
        keyword=keyword,
        start_time=start_time,
        end_time=end_time,
    )
    return success_json(
        PlayerListResponse(
            items=[PlayerResponse.model_validate(p) for p in items],
            total=total,
        ).model_dump(mode="json")
    )


@router.patch("/{player_id}", response_class=None)
async def update_player_api(
    player_id: int,
    payload: PlayerUpdate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """编辑玩家记录。"""
    player = await update_player(
        session,
        current_user,
        player_id,
        project_id=payload.project_id,
        content=payload.content,
    )
    return success_json(PlayerResponse.model_validate(player).model_dump(mode="json"))
