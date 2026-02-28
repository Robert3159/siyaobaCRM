"""
backend.app 包初始化。

该包下按规则书分层：
- routers: 仅 HTTP 路由层
- services: 核心业务逻辑
- guards: 权限/范围判断
- schemas: Pydantic DTO
- models: SQLAlchemy 声明式模型
- core: 配置 / 安全 / 异常 / 通用依赖
"""

