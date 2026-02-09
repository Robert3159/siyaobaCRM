from fastapi import APIRouter, Depends

from app.core.deps import get_current_user_optional
from app.schemas.auth import AccessTokenResponse, LoginRequest
from app.schemas.user import CurrentUser
from app.services.auth_service import login as login_service

router = APIRouter()


@router.post("/login", response_model=AccessTokenResponse)
async def login(payload: LoginRequest) -> AccessTokenResponse:
    """
    用户登录：
    - 仅接收 email/password
    - 调用 Service 完成认证与 Token 生成
    """
    token = await login_service(email=payload.email, password=payload.password)
    return AccessTokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUser | None)
async def get_me(
    current_user: CurrentUser | None = Depends(get_current_user_optional),
) -> CurrentUser | None:
    """
    获取当前登录用户信息。

    说明：
    - 这里只做 HTTP 层：URL / Method / Depends / response_model
    - 不做任何权限逻辑与数据库访问，完全符合规则书对 Router 的约束
    """
    return current_user

