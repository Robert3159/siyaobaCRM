"""客户：列表、详情（需登录 + 数据范围）。"""

from fastapi import APIRouter, Depends, Query

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.exceptions import BusinessError
from app.core.response import success_json
from app.schemas.customer import (
    CustomerListParams,
    CustomerListResponse,
    CustomerResponse,
)
from app.schemas.user import CurrentUser
from app.services.customer_service import get_customer, list_customers
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("", response_class=None)
async def list_customers_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    name: str | None = Query(None),
    contact: str | None = Query(None),
):
    """客户列表：分页、按名称/联系方式筛选；数据范围由后端 scope 控制。"""
    params = CustomerListParams(
        page=page, page_size=page_size, name=name, contact=contact
    )
    items, total = await list_customers(session, current_user, params)
    return success_json(
        CustomerListResponse(
            items=[CustomerResponse.model_validate(c) for c in items],
            total=total,
        ).model_dump(mode="json")
    )


@router.get("/{customer_id}", response_class=None)
async def get_customer_api(
    customer_id: int,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """客户详情。"""
    customer = await get_customer(session, current_user, customer_id)
    if customer is None:
        raise BusinessError(code="NOT_FOUND", message="客户不存在或无权访问")
    return success_json(
        CustomerResponse.model_validate(customer).model_dump(mode="json")
    )
