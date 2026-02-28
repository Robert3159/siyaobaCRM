"""Menu management DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MenuItem(BaseModel):
    id: int
    menu_type: int
    menu_name: str
    icon: str | None = None
    route_name: str
    route_path: str
    status: bool
    hide_in_menu: bool
    order: int
    parent_id: int | None
    children: list["MenuItem"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MenuCreate(BaseModel):
    menu_type: int = Field(..., ge=1, le=3)
    menu_name: str = Field(..., min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=64)
    route_name: str = Field(..., min_length=1, max_length=64)
    route_path: str = Field(..., min_length=1, max_length=128)
    status: bool = True
    hide_in_menu: bool = False
    order: int = Field(1, ge=1, le=9999)
    parent_id: int | None = Field(default=None, ge=1)

    @field_validator("route_path")
    @classmethod
    def validate_route_path(cls, value: str) -> str:
        route_path = value.strip()
        if not route_path.startswith("/"):
            raise ValueError("route_path must start with '/'")
        return route_path


class MenuUpdate(BaseModel):
    menu_name: str | None = Field(default=None, min_length=1, max_length=64)
    icon: str | None = Field(default=None, max_length=64)
    route_name: str | None = Field(default=None, min_length=1, max_length=64)
    route_path: str | None = Field(default=None, min_length=1, max_length=128)
    status: bool | None = None
    hide_in_menu: bool | None = None
    order: int | None = Field(default=None, ge=1, le=9999)

    @field_validator("route_path")
    @classmethod
    def validate_route_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        route_path = value.strip()
        if not route_path.startswith("/"):
            raise ValueError("route_path must start with '/'")
        return route_path


class MenuBatchDelete(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=500)
