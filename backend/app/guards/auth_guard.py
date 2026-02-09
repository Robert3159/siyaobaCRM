from app.core.exceptions import BusinessError
from app.schemas.user import CurrentUser


def ensure_authenticated(user: CurrentUser | None) -> CurrentUser:
    """
    最基础的登录校验 Guard。
    """
    if user is None:
        raise BusinessError(code="UNAUTHENTICATED", message="未登录或登录已过期")
    return user

