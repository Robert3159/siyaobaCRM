from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.exceptions import BusinessError
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import User
from app.schemas.user import CurrentUser, Role
from app.services.email_code_store import verify_code as verify_email_code
from app.services.role_service import get_role_auth_profile


async def _get_user_by_name(session: AsyncSession, user_name: str) -> User | None:
    result = await session.execute(
        select(User).where(User.user == user_name, User.is_deleted == False)
    )
    return result.scalars().first()


async def authenticate_user(user_name: str, password: str) -> User:
    """Authenticate by username and password."""
    async with async_session_factory() as session:
        user = await _get_user_by_name(session, user_name)
        if user is None:
            raise BusinessError(code="INVALID_CREDENTIALS", message="您的用户名或密码错误，请重试")
        if not user.enabled:
            raise BusinessError(code="ACCOUNT_DISABLED", message="账号已停用，请联系管理员")
        if not verify_password(password, user.hashed_password):
            raise BusinessError(code="INVALID_CREDENTIALS", message="您的用户名或密码错误，请重试")
        return user


# Roles that can enter the system.
_ENTRY_ROLES = {
    Role.ADMIN,
    Role.SUB_ADMIN,
    Role.QGS_DIRECTOR,
    Role.QGS_LEADER,
    Role.QGS_MEMBER,
    Role.HGS_DIRECTOR,
    Role.HGS_LEADER,
    Role.HGS_MEMBER,
}

# Message after successful registration when account is still pending review.
ACCOUNT_PENDING_MESSAGE = "您的账号已注册成功，请联系管理员开通"
# Message for login when account is pending review.
LOGIN_PENDING_MESSAGE = "您暂无权限登录，请联系管理员开通"


async def _load_role_profile(role: Role) -> dict:
    if role not in _ENTRY_ROLES:
        return {
            "home_route": None,
            "available_home_routes": [],
        }

    async with async_session_factory() as session:
        return await get_role_auth_profile(session, role.value)


async def login(user_name: str, password: str) -> tuple[str, dict]:
    """Login and return token with lightweight user claims."""
    user = await authenticate_user(user_name=user_name, password=password)

    try:
        role = Role(user.role)
    except ValueError:
        raise BusinessError(
            code="INVALID_USER_ROLE",
            message="用户角色配置异常，请联系管理员",
        )

    if role == Role.PENDING_MEMBER or role not in _ENTRY_ROLES:
        raise BusinessError(
            code="ACCOUNT_PENDING",
            message=LOGIN_PENDING_MESSAGE,
        )

    role_profile = await _load_role_profile(role)

    token = create_access_token(
        subject=user.id,
        extra_claims={
            "id": user.id,
            "role": user.role,
            "department_id": user.department_id,
            "team_id": user.team_id,
            "managed_team_ids": list(user.managed_team_ids or []),
            "is_admin": user.is_admin,
        },
    )
    user_dict = {
        "id": user.id,
        "role": user.role,
        "department_id": user.department_id,
        "team_id": user.team_id,
        "managed_team_ids": list(user.managed_team_ids or []),
        "is_admin": user.is_admin,
        "home_route": role_profile["home_route"],
        "available_home_routes": role_profile["available_home_routes"],
    }
    return token, user_dict


async def register(
    user_name: str, alias: str, email: str, code: str, password: str
) -> tuple[str, dict]:
    """Register user and return token plus lightweight claims."""
    from sqlalchemy.exc import IntegrityError

    email_ = (email or "").strip().lower()
    code_ = (code or "").strip()
    if not verify_email_code(email_, code_):
        raise BusinessError(code="INVALID_EMAIL_CODE", message="验证码错误或已过期")

    try:
        async with async_session_factory() as session:
            existing_email = await session.execute(
                select(User).where(User.email == email_, User.is_deleted == False)
            )
            if existing_email.scalars().first():
                raise BusinessError(code="EMAIL_EXISTS", message="该邮箱已注册")

            existing_user = await _get_user_by_name(session, user_name)
            if existing_user:
                raise BusinessError(code="USER_EXISTS", message="该用户名已被使用")

            user = User(
                user=user_name,
                alias=alias.strip() or None,
                email=email_,
                hashed_password=get_password_hash(password),
                role=Role.PENDING_MEMBER.value,
                department_id=None,
                team_id=None,
                managed_team_ids=[],
                is_admin=False,
                enabled=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id
            user_role = user.role
            user_department_id = user.department_id
            user_team_id = user.team_id
            user_managed_team_ids = list(user.managed_team_ids or [])
            user_is_admin = user.is_admin
    except IntegrityError:
        raise BusinessError(
            code="USER_EXISTS",
            message="该用户名或邮箱已被使用",
        )

    try:
        role = Role(user_role)
    except ValueError:
        raise BusinessError(
            code="INVALID_USER_ROLE",
            message="用户角色配置异常，请联系管理员",
        )

    role_profile = await _load_role_profile(role)

    token = create_access_token(
        subject=user_id,
        extra_claims={
            "id": user_id,
            "role": user_role,
            "department_id": user_department_id,
            "team_id": user_team_id,
            "managed_team_ids": user_managed_team_ids,
            "is_admin": user_is_admin,
        },
    )
    user_dict = {
        "id": user_id,
        "role": user_role,
        "department_id": user_department_id,
        "team_id": user_team_id,
        "managed_team_ids": user_managed_team_ids,
        "is_admin": user_is_admin,
        "home_route": role_profile["home_route"],
        "available_home_routes": role_profile["available_home_routes"],
    }
    return token, user_dict


async def reset_password_by_email_for_current_user(
    current_user: CurrentUser,
    email: str,
    code: str,
    password: str,
) -> None:
    email_ = (email or "").strip().lower()
    code_ = (code or "").strip()
    if not verify_email_code(email_, code_):
        raise BusinessError(code="INVALID_EMAIL_CODE", message="验证码错误或已过期")

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == current_user.id, User.is_deleted == False)
        )
        user = result.scalars().first()
        if user is None:
            raise BusinessError(code="NOT_FOUND", message="用户不存在")

        user_email = (user.email or "").strip().lower()
        if user_email != email_:
            raise BusinessError(code="EMAIL_MISMATCH", message="请输入当前绑定邮箱")

        user.hashed_password = get_password_hash(password)
        await session.commit()
