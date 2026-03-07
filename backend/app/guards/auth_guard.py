from app.core.exceptions import BusinessError
from app.schemas.user import CurrentUser, Role


def ensure_authenticated(user: CurrentUser | None) -> CurrentUser:
    """
    最基础的登录校验 Guard。
    """
    if user is None:
        raise BusinessError(code="UNAUTHENTICATED", message="未登录或登录已过期")
    if user.role == Role.PENDING_MEMBER:
        raise BusinessError(code="PERMISSION_DENIED", message="待审核用户无法访问系统")
    return user

