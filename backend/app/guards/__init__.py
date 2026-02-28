"""
权限与数据范围判断（规则书 guards 层）。

- write_guard：写操作权限 assert_can_update / assert_can_delete。
"""

from app.guards.write_guard import (
    assert_can_delete,
    assert_can_manage_system_resource,
    assert_can_update,
)
__all__ = [
    "assert_can_update",
    "assert_can_delete",
    "assert_can_manage_system_resource",
]
