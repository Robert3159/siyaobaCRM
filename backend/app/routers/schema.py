"""Schema form routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.exceptions import BusinessError
from app.core.response import success_json
from app.schemas.schema_form import FormCreate, FormResponse, FormUpdate
from app.services.schema_service import (
    create_form,
    get_form_by_code,
    get_form_by_id,
    list_forms,
    update_form,
)

router = APIRouter()


@router.get("", response_class=None)
async def list_schemas_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: str | None = Query(None),
    enabled: bool | None = Query(None),
):
    """Schema list."""
    items, total = await list_forms(
        session,
        page=page,
        page_size=page_size,
        name=name,
        enabled=enabled,
    )
    return success_json(
        {
            "items": [FormResponse.model_validate(f).model_dump(mode="json") for f in items],
            "total": total,
        }
    )


@router.get("/by-code/{code}", response_class=None)
async def get_schema_by_code_api(
    code: str,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """Get enabled schema by code (e.g. player_form)."""
    form = await get_form_by_code(session, code)
    if form is None:
        raise BusinessError(code="NOT_FOUND", message="表单不存在或已停用")

    return success_json(FormResponse.model_validate(form).model_dump(mode="json"))


@router.get("/{form_id}", response_class=None)
async def get_schema_api(
    form_id: int,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """Schema detail by id."""
    form = await get_form_by_id(session, form_id)
    if form is None:
        raise BusinessError(code="NOT_FOUND", message="表单不存在")
    return success_json(FormResponse.model_validate(form).model_dump(mode="json"))


@router.post("", response_class=None)
async def create_schema_api(
    payload: FormCreate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """Create schema."""
    form = await create_form(session, current_user, payload)
    return success_json(FormResponse.model_validate(form).model_dump(mode="json"))


@router.patch("/{form_id}", response_class=None)
async def update_schema_api(
    form_id: int,
    payload: FormUpdate,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """Update schema and fields."""
    form = await update_form(session, current_user, form_id, payload)
    return success_json(FormResponse.model_validate(form).model_dump(mode="json"))
