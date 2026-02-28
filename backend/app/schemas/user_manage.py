"""User management DTOs."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserListItem(BaseModel):
    """User list item."""

    id: int
    user: str
    alias: str | None
    email: str
    role: str
    department_id: int | None
    team_id: int | None
    managed_team_ids: list[int] = Field(default_factory=list)
    manager_id: int | None = None
    manager_name: str | None = None
    managed_user_ids: list[int] = Field(default_factory=list)
    managed_user_names: list[str] = Field(default_factory=list)
    department_name: str | None = None
    team_name: str | None = None
    managed_team_names: list[str] = Field(default_factory=list)
    is_admin: bool
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated user list."""

    items: list[UserListItem]
    total: int


class UserListParams(BaseModel):
    """User list query params."""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)
    keyword: str | None = None
    role: str | None = None


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    department_id: int = Field(..., ge=1)


class UserOptionItem(BaseModel):
    id: int
    user: str
    alias: str | None = None
    role: str


class UserUpdateByAdmin(BaseModel):
    """Admin updates user assignment and status."""

    role: str | None = None
    department_id: int | None = None
    team_id: int | None = None
    managed_team_ids: list[int] | None = None
    manager_id: int | None = None
    managed_user_ids: list[int] | None = None
    is_admin: bool | None = None
    enabled: bool | None = None


class UserProfileResponse(BaseModel):
    id: int
    user: str
    alias: str | None
    email: str
    role: str
    avatar: str | None = None
    department_id: int | None
    team_id: int | None
    managed_team_ids: list[int] = Field(default_factory=list)
    manager_id: int | None = None
    manager_name: str | None = None
    managed_user_ids: list[int] = Field(default_factory=list)
    managed_user_names: list[str] = Field(default_factory=list)
    department_name: str | None = None
    team_name: str | None = None
    managed_team_names: list[str] = Field(default_factory=list)
    is_admin: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


class UserProfileUpdate(BaseModel):
    user: str = Field(..., min_length=4, max_length=32)
    alias: str | None = Field(default=None, max_length=64)
    email: EmailStr
    avatar: str | None = Field(default=None, max_length=5_000_000)
