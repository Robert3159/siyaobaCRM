"""
Service 层：
- 显式接收 CurrentUser
- 内部调用 Guard 做权限与范围判断
- 使用 AsyncSession / SQLAlchemy 完成数据库读写

当前仅提供占位，后续随业务扩展具体 Service。
"""

