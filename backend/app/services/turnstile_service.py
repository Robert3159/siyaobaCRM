"""Cloudflare Turnstile 人机验证：仅作防御恶意攻击，不参与登录/注册的验证判断。"""

from app.core.config import settings
from app.core.exceptions import BusinessError


def require_turnstile_token(token: str) -> None:
    """
    仅校验前端传入了人机验证 token（非空即可）。
    不请求 Cloudflare，不参与任何业务验证逻辑，只为防御无 token 的脚本请求。
    开发环境下跳过验证。
    """
    # 开发环境跳过验证
    if settings.turnstile_disabled:
        return
    if not (token or "").strip():
        raise BusinessError(code="TURNSTILE_REQUIRED", message="请完成人机验证")


# ---------- 以下为可选：需请求 Cloudflare 时可调用 verify_turnstile（当前未使用） ----------

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_TURNSTILE_ERRORS = frozenset({"timeout-or-duplicate"})


async def verify_turnstile(token: str) -> None:
    """
    校验 Turnstile 前端返回的 token。
    未配置 secret 时跳过校验；配置了则请求 Cloudflare 校验。
    开发环境下跳过校验。
    """
    # 开发环境跳过验证
    if settings.turnstile_disabled:
        return
    if not settings.turnstile_secret_key:
        return
    if not (token or "").strip():
        raise BusinessError(code="TURNSTILE_REQUIRED", message="请完成人机验证")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": settings.turnstile_secret_key, "response": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    data = resp.json()
    if data.get("success"):
        return
    error_codes = data.get("error-codes") or []
    if ALLOWED_TURNSTILE_ERRORS & set(error_codes):
        logger.warning(
            "Turnstile token 过期或已使用，放行请求（防恶意用，不拦正常用户）. error_codes=%s",
            error_codes,
        )
        return
    logger.warning("Turnstile 校验未通过: error_codes=%s", error_codes)
    raise BusinessError(
        code="TURNSTILE_FAILED",
        message="人机验证未通过，请重试",
    )
