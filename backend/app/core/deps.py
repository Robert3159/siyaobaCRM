from typing import Annotated, Optional

from fastapi import Depends, Request

from app.core.exceptions import BusinessError
from app.core.security import decode_token
from app.guards.auth_guard import ensure_authenticated
from app.schemas.user import CurrentUser, Role


def _parse_current_user_from_token(token: str | None) -> Optional[CurrentUser]:
    if not token:
        return None

    try:
        payload = decode_token(token)
    except ValueError:
        raise BusinessError(code="INVALID_TOKEN", message="登录状态无效，请重新登录")

    try:
        role = Role(payload["role"])
    except (KeyError, ValueError):
        raise BusinessError(code="INVALID_TOKEN", message="登录状态无效，请重新登录")

    raw_department_id = payload.get("department_id")
    raw_team_id = payload.get("team_id")
    raw_managed_team_ids = payload.get("managed_team_ids")

    department_id: int | None = int(raw_department_id) if raw_department_id is not None else None
    team_id: int | None = int(raw_team_id) if raw_team_id is not None else None

    managed_team_ids: list[int] = []
    if isinstance(raw_managed_team_ids, list):
        for raw_managed_team_id in raw_managed_team_ids:
            try:
                managed_team_id = int(raw_managed_team_id)
            except (TypeError, ValueError):
                continue
            if managed_team_id > 0 and managed_team_id not in managed_team_ids:
                managed_team_ids.append(managed_team_id)

    return CurrentUser(
        id=int(payload["id"]),
        role=role,
        department_id=department_id,
        team_id=team_id,
        managed_team_ids=managed_team_ids,
        is_admin=payload.get("is_admin", False),
    )


async def get_current_user_optional(request: Request) -> Optional[CurrentUser]:
    auth_header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    token = auth_header[len(prefix) :] if auth_header.startswith(prefix) else None

    return _parse_current_user_from_token(token)


async def get_current_user(
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
) -> CurrentUser:
    return ensure_authenticated(current_user)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user_optional)]
CurrentUserDepRequired = Annotated[CurrentUser, Depends(get_current_user)]
