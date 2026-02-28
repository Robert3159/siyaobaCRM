"""玩家/提交记录 DTO：提交内容为 JSON，列表返回带 content。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PlayerSubmit(BaseModel):
    """qgs_submit 提交：project_id 必填，其余为表单内容（与 player_form 字段对应）。"""

    project_id: int
    content: dict[str, Any] = Field(default_factory=dict)


class PlayerUpdate(BaseModel):
    """编辑玩家记录：支持修改 project_id 与 content。"""

    project_id: int | None = None
    content: dict[str, Any] | None = None


class PlayerResponse(BaseModel):
    """单条玩家记录（含 content JSON）。"""

    id: int
    project_id: int
    content: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlayerListResponse(BaseModel):
    """玩家列表分页；后端只控制数据行范围，列可见性由前端控制。"""

    items: list[PlayerResponse]
    total: int


class PlayerListParams(BaseModel):
    """列表查询。"""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)
    project_id: int | None = None
