"""
订单模块模型定义
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Order(Base):
    """订单表"""
    __tablename__ = "order_form"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    order_no: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 允许NULL，用于复合唯一键
    player_id: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    player_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    server: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)  # 提高精度，支持虚拟货币
    order_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    qgs__author: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # 前端GS
    hgs_maintainer: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # 后端GS
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # 原始订单JSON
    fail_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 导入失败原因

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        # 唯一约束：order_no 存在时唯一
        UniqueConstraint('order_no', name='uq_order_no'),
        # 复合唯一键：无 order_no 时使用组合唯一
        UniqueConstraint('project_id', 'player_id', 'order_time', 'amount', name='uq_order_combo'),
        # 性能索引
        Index('idx_project_time', 'project_id', 'order_time'),
        Index('idx_gs_author', 'qgs__author'),
        Index('idx_gs_maintainer', 'hgs_maintainer'),
        # 复合索引：优化常见查询模式
        Index('idx_order_is_deleted_project', 'is_deleted', 'project_id'),
        Index('idx_order_is_deleted_created', 'is_deleted', 'created_at'),
    )


class OrderFieldMapping(Base):
    """订单字段映射表"""
    __tablename__ = "order_field_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_field: Mapped[str] = mapped_column(String(255), nullable=False)
    system_field: Mapped[str] = mapped_column(String(255), nullable=False)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('project_id', 'file_field', name='uq_project_file_field'),
    )


class OrderImportLog(Base):
    """订单导入日志表"""
    __tablename__ = "order_import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_details: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # 失败详情 [{"row": 1, "error": "重复订单"}, ...]
    import_user: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='pending')  # pending/success/failed
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # 整体错误信息

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_project_created', 'project_id', 'created_at'),
    )


class OrderSystemField(Base):
    """系统标准字段定义"""
    __tablename__ = "order_system_field"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_field: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # player_id, server, amount 等
    field_label: Mapped[str] = mapped_column(String(100), nullable=False)  # 玩家ID, 区服, 充值金额
    field_type: Mapped[str] = mapped_column(String(50), nullable=False)  # string, number, datetime
    aliases: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # ["user_id", "uid", "玩家ID"] 等别名

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
