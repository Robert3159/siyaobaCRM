from typing import Annotated, Optional

from fastapi import Depends, Request

from app.core.exceptions import BusinessError
from app.core.security import decode_token
from app.schemas.user import CurrentUser


def _parse_current_user_from_token(token: str | None) -> Optional[CurrentUser]:
    if not token:
        return None

    try:
        payload = decode_token(token)
    except ValueError:
        raise BusinessError(code="INVALID_TOKEN", message="登录状态无效，请重新登录")

    return CurrentUser(
        id=int(payload["id"]),
        role=payload["role"],
        department_id=payload.get("department_id"),
        team_id=payload.get("team_id"),
        is_admin=payload.get("is_admin", False),
    )


async def get_current_user_optional(request: Request) -> Optional[CurrentUser]:
    """
    从 Authorization Bearer Token 中解析可选 CurrentUser。

    说明：
    - 只做身份解析，不做权限判断
    - 若无 token，则返回 None
    """
    auth_header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    token = auth_header[len(prefix) :] if auth_header.startswith(prefix) else None

    return _parse_current_user_from_token(token)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user_optional)]

