"""
SQLAlchemy 模型与数据库会话。

- 所有数据库访问必须通过 Service 层封装；
- Router 层禁止直接使用 Session / 执行原始 SQL。
"""

from app.models.base import (
    Base,
    Customer,
    Department,
    Form,
    Menu,
    Player,
    Project,
    RolePermission,
    SystemRole,
    Team,
    User,
)

__all__ = [
    "Base",
    "User",
    "Department",
    "Team",
    "Customer",
    "Project",
    "Form",
    "Menu",
    "Player",
    "RolePermission",
    "SystemRole",
]
