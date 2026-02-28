"""邮箱验证码内存存储（仅用于开发/单机，生产可换 Redis）。"""

import logging
import secrets
import time

# email -> (code, expiry_ts)
_email_codes: dict[str, tuple[str, float]] = {}
_CODE_EXPIRE_SECONDS = 60 * 5  # 5 分钟

logger = logging.getLogger(__name__)


def set_code(email: str) -> str:
    email = (email or "").strip().lower()
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    _email_codes[email] = (code, time.time() + _CODE_EXPIRE_SECONDS)
    return code


def verify_code(email: str, code: str) -> bool:
    email = (email or "").strip().lower()
    code = (code or "").strip()
    if not code:
        return False
    if email not in _email_codes:
        logger.warning("验证码校验失败：邮箱不存在于存储中 email=%s", email)
        return False
    stored, expiry = _email_codes[email]
    now = time.time()
    if now > expiry:
        del _email_codes[email]
        logger.warning("验证码校验失败：已过期 email=%s 过期时间=%.0fs", email, expiry - now)
        return False
    if not secrets.compare_digest(stored, code):
        logger.warning("验证码校验失败：与存储不一致 email=%s", email)
        return False
    del _email_codes[email]
    return True
