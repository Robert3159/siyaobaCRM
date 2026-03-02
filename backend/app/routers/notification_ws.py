import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.database import async_session_factory
from app.core.deps import _parse_current_user_from_token
from app.schemas.user import Role
from app.services.notification_service import notification_hub
from app.services.player_service import assign_hgs_maintainer
from app.services.user_service import resolve_user_display_name

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_hgs_role(role: Role) -> bool:
    role_value = role.value
    return role_value.startswith("HGS") or role_value in ("ADMIN", "SUB_ADMIN")


@router.websocket("/notifications")
async def notifications_ws(websocket: WebSocket, token: str | None = Query(None)) -> None:
    try:
        user = _parse_current_user_from_token(token)
    except Exception as exc:
        logger.warning("WebSocket auth failed: %s", exc)
        await websocket.close(code=1008)
        return

    if not user:
        await websocket.close(code=1008)
        return

    await notification_hub.connect(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "invalid_json"})
                continue

            action = data.get("type")
            if action == "claim":
                if not _is_hgs_role(user.role):
                    await websocket.send_json({"type": "error", "message": "forbidden"})
                    continue
                message_id = str(data.get("id") or "").strip()
                if not message_id:
                    await websocket.send_json({"type": "error", "message": "missing_id"})
                    continue
                removed = await notification_hub.claim_message(message_id)
                if not removed:
                    await websocket.send_json({"type": "error", "message": "not_found"})
                    continue

                async with async_session_factory() as session:
                    try:
                        claimer_alias = await resolve_user_display_name(session, user.id)
                        claimer_display = claimer_alias or f"User-{user.id}"
                        updated = await assign_hgs_maintainer(
                            session,
                            user,
                            removed.player_id,
                            claimer_display,
                        )
                        if not updated:
                            await session.rollback()
                            await notification_hub.restore_message(removed)
                            await websocket.send_json({"type": "error", "message": "not_found"})
                            continue
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        await notification_hub.restore_message(removed)
                        await websocket.send_json({"type": "error", "message": "not_found"})
                        continue

                await notification_hub.broadcast(
                    {
                        "type": "claimed",
                        "id": message_id,
                        "player_id": removed.player_id,
                        "claimer": {"id": user.id, "role": user.role.value, "alias": claimer_display},
                    }
                )
                continue

            await websocket.send_json({"type": "error", "message": "unsupported_action"})
    except WebSocketDisconnect:
        await notification_hub.disconnect(websocket)
    except Exception:
        logger.exception("WebSocket crashed")
        await notification_hub.disconnect(websocket)
