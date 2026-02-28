from fastapi import APIRouter, Depends

from app.core.database import get_async_session
from app.core.deps import get_current_user, get_current_user_optional
from app.core.response import success_json
from app.schemas.auth import (
    LoginRequest,
    ResetPasswordByEmailRequest,
    RegisterRequest,
    SendEmailCodeRequest,
)
from app.schemas.user import CurrentUser
from app.services.auth_service import (
    ACCOUNT_PENDING_MESSAGE,
    login as login_service,
    reset_password_by_email_for_current_user,
    register as register_service,
)
from app.services.email_service import send_verification_email
from app.services.role_service import get_role_auth_profile
from app.services.turnstile_service import require_turnstile_token
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/login")
async def login(payload: LoginRequest):
    """用户名 user + 密码登录；Turnstile 仅防恶意请求（非空即可）。返回 { code: '0000', data: { access_token, token_type, user } }。"""
    require_turnstile_token(payload.turnstile_token)
    token, user = await login_service(user_name=payload.user, password=payload.password)
    return success_json({
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    })


@router.post("/send-email-code")
async def send_email_code(payload: SendEmailCodeRequest):
    """向邮箱发送验证码（用于注册），QQ邮箱 SMTP。"""
    from app.core.exceptions import BusinessError

    try:
        send_verification_email(payload.email)
    except BusinessError:
        raise
    except Exception:
        raise BusinessError(
            code="EMAIL_SEND_FAILED",
            message="验证码发送失败，请稍后重试",
        )
    return success_json(None)


@router.post("/register")
async def register(payload: RegisterRequest):
    """用户名 + 花名 + 邮箱 + 验证码 + 密码 注册。新用户固定为 PENDING_MEMBER，不分配 token，仅返回成功与提示文案；前端据此提示联系管理员，不可进入系统。"""
    require_turnstile_token(payload.turnstile_token)
    token, user = await register_service(
        user_name=payload.user,
        alias=payload.alias or "",
        email=payload.email,
        code=payload.code,
        password=payload.password,
    )
    # 注册后仅为待审核角色，不返回 token，避免前端误入系统
    if user.get("role") == "PENDING_MEMBER":
        return success_json({
            "registered": True,
            "message": ACCOUNT_PENDING_MESSAGE,
        })
    return success_json({
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    })


@router.post("/reset-password-by-email")
async def reset_password_by_email(
    payload: ResetPasswordByEmailRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    await reset_password_by_email_for_current_user(
        current_user=current_user,
        email=payload.email,
        code=payload.code,
        password=payload.password,
    )
    return success_json(None)


@router.get("/me")
async def get_me(
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_async_session),
):
    """获取当前登录用户信息；返回 { code: '0000', data: CurrentUser }。"""
    if current_user is None:
        return success_json(None)
    role_profile = await get_role_auth_profile(session, current_user.role.value)
    return success_json({
        **current_user.model_dump(),
        "home_route": role_profile["home_route"],
        "available_home_routes": role_profile["available_home_routes"],
    })
