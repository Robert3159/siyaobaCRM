"""客户 Service：列表、详情（需登录 + build_scope_filter）。"""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scope import build_scope_filter
from app.models import Customer
from app.schemas.customer import CustomerListParams
from app.schemas.user import CurrentUser


def _scope_conditions(model: type, scope: dict) -> list:
    return [getattr(model, key) == value for key, value in scope.items()]


async def list_customers(
    session: AsyncSession,
    user: CurrentUser,
    params: CustomerListParams,
) -> tuple[list[Customer], int]:
    """客户列表：分页、按名称/联系方式筛选；数据范围由 build_scope_filter 控制。"""
    scope = build_scope_filter(user, "customer")
    base = and_(Customer.is_deleted == False, *_scope_conditions(Customer, scope))
    query = select(Customer).where(base)

    if params.name:
        query = query.where(Customer.name.ilike(f"%{params.name}%"))
    if params.contact:
        query = query.where(Customer.contact.ilike(f"%{params.contact}%"))

    total_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_stmt)).scalar() or 0

    query = query.order_by(Customer.id.desc())
    query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def get_customer(
    session: AsyncSession,
    user: CurrentUser,
    customer_id: int,
) -> Customer | None:
    """客户详情；无权限或不存在返回 None。"""
    scope = build_scope_filter(user, "customer")
    query = select(Customer).where(
        and_(
            Customer.id == customer_id,
            Customer.is_deleted == False,
            *_scope_conditions(Customer, scope),
        )
    )
    result = await session.execute(query)
    return result.scalars().first()
