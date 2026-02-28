"""客户 DTO：列表、响应（本期仅只读列表/详情）。"""

from datetime import datetime

from pydantic import BaseModel, Field


class CustomerResponse(BaseModel):
    """单条客户响应。"""

    id: int
    name: str
    contact: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    """分页列表：items + total。"""

    items: list[CustomerResponse]
    total: int


class CustomerListParams(BaseModel):
    """列表查询参数。"""

    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=100, description="每页条数")
    name: str | None = None
    contact: str | None = None
