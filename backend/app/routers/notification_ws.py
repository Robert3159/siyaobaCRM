import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.deps import _parse_current_user_from_token
from app.schemas.user import Role
from app.services.notification_service import notification_hub

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
                ok = await notification_hub.claim_message(message_id, user)
                if not ok:
                    await websocket.send_json({"type": "error", "message": "not_found"})
                continue

            await websocket.send_json({"type": "error", "message": "unsupported_action"})
    except WebSocketDisconnect:
        await notification_hub.disconnect(websocket)
    except Exception:
        logger.exception("WebSocket crashed")
        await notification_hub.disconnect(websocket)
