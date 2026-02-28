"""表单管理 DTO：fields 为 JSON 数组，每项含 key、label、type、required、options、order。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

FIELD_TYPE_ALIASES = {
    "single_line_text": "single_line_text",
    "string": "single_line_text",
    "text": "single_line_text",
    "input": "single_line_text",
    "multi_line_text": "multi_line_text",
    "textarea": "multi_line_text",
    "multiline": "multi_line_text",
    "radio": "radio",
    "checkbox": "checkbox",
    "select": "select",
    "select_multiple": "select_multiple",
    "multi_select": "select_multiple",
    "select_multi": "select_multiple",
    "number": "number",
    "int": "number",
    "float": "number",
    "decimal": "number",
    "datetime": "datetime",
    "date-time": "datetime",
    "date_time": "datetime",
    "date_time_picker": "datetime",
    "datetime_picker": "datetime",
    "date": "datetime",
    "upload_attachment": "upload_attachment",
    "attachment": "upload_attachment",
    "upload_file": "upload_attachment",
    "file": "upload_attachment",
    "upload_image": "upload_image",
    "image_upload": "upload_image",
    "image": "upload_image",
    "color": "color",
    "colour": "color",
    "color_picker": "color",
    "colour_picker": "color",
    # 兼容历史数据，不在前端新增类型中暴露
    "project": "project",
}

OPTION_FIELD_TYPES = {"radio", "checkbox", "select", "select_multiple"}
VISIBLE_PAGE_KEYS = {"qgs/list", "hgs/list", "qgs/submit"}
ALLOWED_ROLES = {
    "ADMIN",
    "SUB_ADMIN",
    "QGS_DIRECTOR",
    "QGS_LEADER",
    "QGS_MEMBER",
    "HGS_DIRECTOR",
    "HGS_LEADER",
    "HGS_MEMBER",
}


def _normalize_roles(value: Any, field_name: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")

    normalized_roles: list[str] = []
    seen: set[str] = set()
    for item in value:
        role = str(item or "").strip().upper()
        if not role or role in seen:
            continue
        if role not in ALLOWED_ROLES:
            raise ValueError(f"无效角色: {role}")
        seen.add(role)
        normalized_roles.append(role)

    return normalized_roles or None


# 字段定义：key, label, type, required, options?, order?
class FormFieldDef(BaseModel):
    key: str | None = Field(default=None, min_length=1)
    label: str = Field(..., min_length=1)
    type: str = Field("single_line_text")
    required: bool = False
    options: list[Any] | None = None
    order: int = Field(0, ge=0)
    visible_pages: list[str] | None = None
    visible_roles: list[str] | None = None
    editable_roles: list[str] | None = None
    readonly_roles: list[str] | None = None

    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, value: Any) -> str | None:
        if value is None:
            return None
        key = str(value).strip()
        return key or None

    @field_validator("label", mode="before")
    @classmethod
    def normalize_label(cls, value: Any) -> str:
        label = str(value).strip()
        if not label:
            raise ValueError("字段名称不能为空")
        return label

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: Any) -> str:
        raw = str(value or "").strip().lower()
        normalized = FIELD_TYPE_ALIASES.get(raw)
        if not normalized:
            allowed = ", ".join(sorted(set(FIELD_TYPE_ALIASES.values())))
            raise ValueError(f"不支持的字段类型: {value}，可选: {allowed}")
        return normalized

    @field_validator("visible_pages", mode="before")
    @classmethod
    def normalize_visible_pages(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("visible_pages must be a list")

        normalized_pages: list[str] = []
        seen: set[str] = set()
        for item in value:
            page_key = str(item or "").strip().lower()
            if not page_key:
                continue
            if page_key in seen:
                continue
            if page_key not in VISIBLE_PAGE_KEYS:
                allowed = ", ".join(sorted(VISIBLE_PAGE_KEYS))
                raise ValueError(f"无效页面: {page_key}，可选: {allowed}")
            seen.add(page_key)
            normalized_pages.append(page_key)

        return normalized_pages or None

    @field_validator("visible_roles", mode="before")
    @classmethod
    def normalize_visible_roles(cls, value: Any) -> list[str] | None:
        return _normalize_roles(value, "visible_roles")

    @field_validator("editable_roles", mode="before")
    @classmethod
    def normalize_editable_roles(cls, value: Any) -> list[str] | None:
        return _normalize_roles(value, "editable_roles")

    @field_validator("readonly_roles", mode="before")
    @classmethod
    def normalize_readonly_roles(cls, value: Any) -> list[str] | None:
        return _normalize_roles(value, "readonly_roles")

    @model_validator(mode="after")
    def validate_options(self) -> "FormFieldDef":
        if self.options is not None:
            normalized_options: list[Any] = []
            for item in self.options:
                if item is None:
                    continue
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        normalized_options.append(text)
                else:
                    normalized_options.append(item)
            self.options = normalized_options or None

        if self.type in OPTION_FIELD_TYPES and not self.options:
            raise ValueError("该字段类型必须提供至少一个选项")

        if self.type not in OPTION_FIELD_TYPES:
            self.options = None

        if self.editable_roles and self.readonly_roles:
            overlap = sorted(set(self.editable_roles) & set(self.readonly_roles))
            if overlap:
                overlap_text = ", ".join(overlap)
                raise ValueError(f"editable_roles 和 readonly_roles 存在重复角色: {overlap_text}")

        return self


class FormCreate(BaseModel):
    """新建表单。"""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=64)
    enabled: bool = True
    fields: list[FormFieldDef] = Field(default_factory=list)


class FormUpdate(BaseModel):
    """更新表单（白名单）。"""

    name: str | None = Field(None, min_length=1, max_length=255)
    enabled: bool | None = None
    fields: list[FormFieldDef] | None = None


class FormResponse(BaseModel):
    """单条表单响应。"""

    id: int
    name: str
    code: str
    enabled: bool
    fields: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FormListResponse(BaseModel):
    """表单列表（分页）。"""

    items: list[FormResponse]
    total: int
