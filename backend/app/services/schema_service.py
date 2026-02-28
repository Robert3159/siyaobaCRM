"""
表单管理 Service：列表、详情、按 code 获取（player_form）、新建、更新（含 fields JSON）。
Form 不做数据范围，仅软删；增删改仅 ADMIN/SUB_ADMIN（assert_can_manage_system_resource）。
"""

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.guards import assert_can_manage_system_resource
from app.models import Form
from app.schemas.schema_form import FormCreate, FormUpdate
from app.schemas.user import CurrentUser

VISIBLE_PAGE_KEYS = {"qgs/list", "hgs/list", "qgs/submit"}


def _generate_field_key(used_keys: set[str]) -> str:
    while True:
        field_key = f"fld_{uuid4().hex[:12]}"
        if field_key not in used_keys:
            used_keys.add(field_key)
            return field_key


def _normalize_visible_pages(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None

    normalized_pages: list[str] = []
    seen: set[str] = set()
    for item in value:
        page_key = str(item or "").strip().lower()
        if not page_key:
            continue
        if page_key in seen:
            continue
        if page_key not in VISIBLE_PAGE_KEYS:
            continue
        seen.add(page_key)
        normalized_pages.append(page_key)
    return normalized_pages or None


def _normalize_fields(fields: list[dict]) -> list[dict]:
    normalized_fields: list[dict] = []
    used_keys: set[str] = set()

    for index, field in enumerate(fields):
        key = (field.get("key") or "").strip()
        if key:
            if key in used_keys:
                raise BusinessError(code="FIELD_KEY_DUPLICATED", message="字段 ID 重复")
            used_keys.add(key)
        else:
            key = _generate_field_key(used_keys)

        normalized_field = {
            "key": key,
            "label": field["label"],
            "type": field["type"],
            "required": bool(field.get("required", False)),
            "options": field.get("options"),
            "order": index,
        }
        visible_pages = _normalize_visible_pages(field.get("visible_pages"))
        if visible_pages:
            normalized_field["visible_pages"] = visible_pages
        
        visible_roles = field.get("visible_roles")
        if visible_roles and isinstance(visible_roles, list):
            normalized_field["visible_roles"] = visible_roles
        editable_roles = field.get("editable_roles")
        if editable_roles and isinstance(editable_roles, list):
            normalized_field["editable_roles"] = editable_roles
        readonly_roles = field.get("readonly_roles")
        if readonly_roles and isinstance(readonly_roles, list):
            normalized_field["readonly_roles"] = readonly_roles

        normalized_fields.append(normalized_field)

    return normalized_fields


async def list_forms(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    name: str | None = None,
    enabled: bool | None = None,
) -> tuple[list[Form], int]:
    """列表：软删 + 分页 + 可选筛选。"""
    q = select(Form).where(Form.is_deleted == False)
    if name:
        q = q.where(Form.name.ilike(f"%{name}%"))
    if enabled is not None:
        q = q.where(Form.enabled == enabled)

    total_stmt = select(func.count()).select_from(q.subquery())
    total = (await session.execute(total_stmt)).scalar() or 0

    q = q.order_by(Form.id.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    return list(result.scalars().all()), total


async def get_form_by_id(session: AsyncSession, form_id: int) -> Form | None:
    """按 id 获取，未软删。"""
    result = await session.execute(
        select(Form).where(Form.id == form_id, Form.is_deleted == False)
    )
    return result.scalars().first()


async def get_form_by_code(session: AsyncSession, code: str) -> Form | None:
    """按 code 获取（如 player_form），未软删且 enabled。"""
    result = await session.execute(
        select(Form).where(
            Form.code == code,
            Form.is_deleted == False,
            Form.enabled == True,
        )
    )
    return result.scalars().first()


async def create_form(
    session: AsyncSession, user: CurrentUser, payload: FormCreate
) -> Form:
    """新建表单。仅 ADMIN、SUB_ADMIN 可操作。若同 code 已存在且未软删则报错；若已软删则恢复并更新。"""
    assert_can_manage_system_resource(user)
    fields_data = _normalize_fields([f.model_dump() for f in payload.fields])

    # 未软删的同 code：直接报已存在
    existing_live = await session.execute(
        select(Form).where(Form.code == payload.code, Form.is_deleted == False)
    )
    if existing_live.scalars().first():
        raise BusinessError(code="CODE_EXISTS", message="表单 code 已存在")

    # 已软删的同 code：恢复并更新，避免唯一约束且列表可见
    existing_deleted = await session.execute(
        select(Form).where(Form.code == payload.code, Form.is_deleted == True)
    )
    deleted_form = existing_deleted.scalars().first()
    if deleted_form is not None:
        deleted_form.is_deleted = False
        deleted_form.deleted_at = None
        deleted_form.name = payload.name
        deleted_form.enabled = payload.enabled
        deleted_form.fields = fields_data
        await session.flush()
        await session.refresh(deleted_form)
        return deleted_form

    form = Form(
        name=payload.name,
        code=payload.code,
        enabled=payload.enabled,
        fields=fields_data,
    )
    session.add(form)
    await session.flush()
    await session.refresh(form)
    return form


async def update_form(
    session: AsyncSession,
    user: CurrentUser,
    form_id: int,
    payload: FormUpdate,
) -> Form:
    """更新表单（白名单）。仅 ADMIN、SUB_ADMIN 可操作。"""
    assert_can_manage_system_resource(user)
    form = await get_form_by_id(session, form_id)
    if form is None:
        raise BusinessError(code="NOT_FOUND", message="表单不存在")
    if payload.name is not None:
        form.name = payload.name
    if payload.enabled is not None:
        form.enabled = payload.enabled
    if payload.fields is not None:
        form.fields = _normalize_fields([f.model_dump() for f in payload.fields])
    await session.flush()
    await session.refresh(form)
    return form
