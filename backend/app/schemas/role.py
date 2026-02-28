"""Role management DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class RoleItem(BaseModel):
    role: str
    label: str


class PermissionOption(BaseModel):
    code: str
    label: str


class RoleMenuItem(BaseModel):
    id: int
    menu_type: int
    menu_name: str
    route_name: str
    route_path: str
    parent_id: int | None
    children: list["RoleMenuItem"] = Field(default_factory=list)


class RolePermissionsResponse(BaseModel):
    role: str
    permissions: list[str]


class RolePermissionsUpdate(BaseModel):
    permissions: list[str] = Field(default_factory=list, max_length=500)


class RoleDetailResponse(BaseModel):
    role: str
    label: str
    permissions: list[str]
    home_route: str | None = None
    available_home_routes: list[str] = Field(default_factory=list)
    menu_tree: list[RoleMenuItem] = Field(default_factory=list)
    updated_at: datetime | None = None


class RoleUpdateRequest(BaseModel):
    permissions: list[str] = Field(default_factory=list, max_length=500)
    home_route: str | None = Field(default=None, max_length=64)

    @field_validator("home_route")
    @classmethod
    def normalize_home_route(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

