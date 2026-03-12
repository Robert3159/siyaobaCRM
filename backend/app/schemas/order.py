"""
订单模块 Schema 定义
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OrderResponse(BaseModel):
    """订单响应"""
    id: int
    project_id: int
    project_name: Optional[str] = None
    order_no: Optional[str] = None
    player_id: str
    player_name: Optional[str] = None
    server: Optional[str] = None
    amount: float
    order_time: Optional[datetime] = None
    qgs__author: Optional[int] = None
    qgs__author_name: Optional[str] = None
    hgs_maintainer: Optional[int] = None
    hgs_maintainer_name: Optional[str] = None
    raw_data: Optional[dict] = None
    fail_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """订单列表响应"""
    items: list[OrderResponse]
    total: int


class OrderFetchParams(BaseModel):
    """订单查询参数"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    project_id: Optional[int] = None
    player_id: Optional[str] = None
    qgs__author: Optional[int] = None
    hgs_maintainer: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    sort_field: Optional[str] = Field(default=None, pattern="^(order_time|amount|created_at)$")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")


class FieldMappingResponse(BaseModel):
    """字段映射响应"""
    id: int
    project_id: int
    file_field: str
    system_field: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FieldMappingCreate(BaseModel):
    """字段映射创建"""
    project_id: int
    file_field: str
    system_field: str


class FieldMappingCreateBatch(BaseModel):
    """批量创建字段映射"""
    mappings: list[FieldMappingCreate]


class ImportLogResponse(BaseModel):
    """导入日志响应"""
    id: int
    project_id: int
    project_name: Optional[str] = None
    filename: Optional[str] = None
    total_rows: int
    success_rows: int
    fail_rows: int
    fail_details: Optional[list] = None
    import_user: Optional[int] = None
    import_user_name: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ImportLogListResponse(BaseModel):
    """导入日志列表响应"""
    items: list[ImportLogResponse]
    total: int


class SystemFieldResponse(BaseModel):
    """系统字段定义响应"""
    system_field: str
    field_label: str
    field_type: str
    aliases: Optional[list[str]] = None

    class Config:
        from_attributes = True


class FileParseResponse(BaseModel):
    """文件解析响应"""
    headers: list[str]
    preview_data: list[dict]
    suggested_mapping: dict[str, str]
    total_rows: int


class ImportPayload(BaseModel):
    """导入请求"""
    project_id: int
    field_mapping: dict[str, str] = Field(default_factory=dict)


class ImportResult(BaseModel):
    """导入结果"""
    success: bool
    total_rows: int
    success_rows: int
    fail_rows: int
    log_id: int
    fail_details: Optional[list[dict]] = None
