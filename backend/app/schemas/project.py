"""项目管理 DTO：列表、创建、更新、响应。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """新建项目（项目 ID 由后端生成）。"""

    name: str = Field(..., min_length=1, max_length=255)
    date: datetime | None = None
    remark: str | None = None


class ProjectUpdate(BaseModel):
    """更新项目（白名单字段）。"""

    name: str | None = Field(None, min_length=1, max_length=255)
    date: datetime | None = None
    remark: str | None = None
    enabled: bool | None = None


class ProjectResponse(BaseModel):
    """单条项目响应。"""

    id: int
    project_no: str
    name: str
    date: datetime | None
    remark: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """分页列表：items + total。"""

    items: list[ProjectResponse]
    total: int


class ProjectListParams(BaseModel):
    """列表查询参数。"""

    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=100, description="每页条数")
    name: str | None = None
    enabled: bool | None = None
