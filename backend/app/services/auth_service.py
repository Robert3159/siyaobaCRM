from prisma.models import User

from app.core.exceptions import BusinessError
from app.core.security import create_access_token, verify_password
from app.models import prisma


async def authenticate_user(email: str, password: str) -> User:
    """
    认证用户：
    - 根据 email 查询用户（过滤软删除）
    - 校验密码
    """
    user = await prisma.user.find_first(
        where={
            "email": email,
            "is_deleted": False,
        }
    )

    if user is None:
        raise BusinessError(code="INVALID_CREDENTIALS", message="邮箱或密码错误")

    if not verify_password(password, user.hashed_password):
        raise BusinessError(code="INVALID_CREDENTIALS", message="邮箱或密码错误")

    return user


async def login(email: str, password: str) -> str:
    """
    登录服务：
    - 调用 authenticate_user 完成身份校验
    - 生成访问 Token，携带 CurrentUser 所需字段
    """
    user = await authenticate_user(email=email, password=password)

    token = create_access_token(
        subject=user.id,
        extra_claims={
            "id": user.id,
            "role": user.role,
            "department_id": user.department_id,
            "team_id": user.team_id,
            "is_admin": user.is_admin,
        },
    )
    return token

