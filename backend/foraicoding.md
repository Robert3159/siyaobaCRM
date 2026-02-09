FastAPI + Prisma 后端项目统一规则书

本规则书是唯一且全局生效的后端开发规范
任何人编写的代码 必须遵守本规则书

一、规则书使用原则
1.1 适用对象

FastAPI 后端项目

使用 Python Prisma Client

1.2 优先级规则

优先级从高到低：

本规则书

项目现有代码结构

FastAPI 官方推荐

Prisma 官方推荐

任何与规则书冲突的代码必须修改，而不是修改规则书的理解

二、 全局代码规范
2.1 Python 风格（等价于 ESLint / Prettier 的地位）
必须遵守

Python >= 3.13

使用 ruff / black / isort 统一格式

行宽：88

禁止随意 try/except 吞异常

所有函数、类必须有 明确输入输出类型

def get_user_by_id(user_id: int) -> User:
    ...

2.2 FastAPI 编码约定

❌ 禁止在 router 中写业务逻辑

❌ 禁止在 router 中直接访问 Prisma

✅ router 只负责：

参数校验

Depends 注入

调用 service

@router.get("/users/{id}")
async def get_user(
    id: int,
    user=Depends(get_current_user),
):
    return await user_service.get_user(id, user)

2.3 Prisma 使用规则

只能通过 Python Prisma Client 访问数据库

禁止写原生 SQL

禁止绕过 Service 层直接 CRUD

所有查询必须显式 where

await prisma.user.find_first(
    where={"id": user_id}
)

2.4 错误处理规范

禁止返回裸字符串

统一抛出业务异常

raise BusinessError(code="PERMISSION_DENIED", message="无权访问")

三、 项目分层结构
app/
├── main.py
├── routers/        # 仅 HTTP 层
├── services/       # 核心业务 + 权限校验
├── guards/         # 权限 / 数据范围判断
├── schemas/        # Pydantic DTO
├── models/         # Prisma Model（只读引用）
└── core/           # JWT / Config / Exception

四、 身份 & 请求上下文
4.1 CurrentUser 定义（强制字段）
class CurrentUser(BaseModel):
    id: int
    role: str
    department_id: int | None
    team_id: int | None
    is_admin: bool


CurrentUser 必须通过 Depends 注入

禁止手动构造

4.2 JWT 规则（板块可扩展）

JWT 仅用于：

身份确认

基础角色信息

禁止在 JWT 中存权限判断结果

五、 角色 & 权限系统
5.1 角色枚举（固定，不可随意新增）
ADMIN
SUB_ADMIN
QGS_DIRECTOR
QGS_LEADER
QGS_MEMBER
HGS_DIRECTOR
HGS_LEADER
HGS_MEMBER

5.2 角色层级（用于比较）
DIRECTOR > LEADER > MEMBER
ADMIN > SUB_ADMIN


同层级不可越权

不同部门不可天然互通

5.3 权限判断基本原则

权限 =
身份角色 + 组织归属 + 数据归属

六、 数据可见性规则（行级权限）
6.1 可见性范围枚举
SELF
TEAM
DEPARTMENT
ALL

6.2 不同角色的数据范围
角色	数据范围
MEMBER	SELF
LEADER	TEAM
DIRECTOR	DEPARTMENT
ADMIN	ALL
SUB_ADMIN	部分 ALL
6.3 所有 Prisma 查询必须套用 Scope Filter
where = build_scope_filter(
    user=current_user,
    resource="promotion_data"
)

七、 Guard 设计规范
7.1 Guard 只能做三件事

读取 CurrentUser

判断是否允许

返回布尔 / 抛异常

7.2 Guard 禁止访问 HTTP 对象

❌ request
❌ response
❌ header

八、 Service 层强制约定

Service 必须显式接收 CurrentUser

Service 内部必须调用 Guard

Service 是权限最终裁决层

九、 Router 层约定

Router 只声明：

URL

HTTP Method

Depends

Router 不得出现：

if user.role

if user.id

十、 数据事务规则（Transaction）
10.1 事务使用的强制条件

以下任意情况 必须使用 Prisma Transaction：

一次请求中：

≥ 2 次写操作（create / update / delete）

写操作 + 审计日志

写操作 + 权限 / 角色变更

批量写入 / 批量更新

涉及“状态流转”（如 pending → approved）

10.2 事务使用位置约束

✅ 事务 只能 出现在 Service 层

❌ Router 禁止使用事务

❌ Guard 禁止使用事务

❌ 单个 CRUD helper 禁止自行开启事务

10.3 Prisma Transaction 规范
async with prisma.tx() as tx:
    await tx.user.update(...)
    await tx.audit_log.create(...)


transaction 内 禁止 await 外部 IO

transaction 内禁止调用 Guard

transaction 失败必须整体回滚

10.4 禁止行为

❌ 多个写操作不包事务

❌ 在 transaction 内 try/except 吞异常

❌ 在 router 中开启 transaction

十一、 写操作权限规则（Create / Update / Delete 专用）

⚠️ 可见 ≠ 可改 ≠ 可删
本规则优先级 高于数据可见性规则

11.1 写权限必须单独判断

任何写操作 必须 显式调用写权限 Guard，例如：

assert_can_update(user, target)
assert_can_delete(user, target)


禁止复用「查询权限」判断写操作。

11.2 更新权限基本原则

MEMBER：

❌ 不能更新他人数据

LEADER：

✅ 可更新 TEAM 内 MEMBER

❌ 不能更新同级 LEADER

DIRECTOR：

✅ 可更新部门内所有非 DIRECTOR

ADMIN：

✅ 可更新所有

SUB_ADMIN：

⚠️ 仅限被授权模块

11.3 删除权限（更严格）

默认：禁止物理删除

MEMBER：❌

LEADER：❌

DIRECTOR：⚠️ 仅限业务数据

ADMIN：✅

删除操作必须：

二次确认（逻辑层）

写入审计日志

11.4 批量操作特殊规则

批量 update / delete：

必须逐条校验权限

禁止“只校验一次”

十二、 受保护字段规则（Critical）

12.1 受保护字段定义

以下字段 禁止由前端直接控制：

id

owner_id

created_by

department_id

team_id

role

permission

is_admin

created_at

updated_at

（具体表可追加）

12.2 更新数据的唯一合法方式

❌ 绝对禁止

await prisma.user.update(
    where={"id": id},
    data=payload.dict()
)


✅ 唯一允许

data = {
    "name": payload.name,
    "email": payload.email,
}
await prisma.user.update(
    where={"id": id},
    data=data
)

12.3 强制约束

不得 将 DTO / Schema 原样传给 Prisma

必须 明确写出字段映射

新增字段必须同步更新白名单

十三、 删除规则（软删除 / 硬删除）
13.1 默认删除策略

全项目默认使用软删除

软删除字段统一为：

is_deleted: boolean
deleted_at: datetime | null

13.2 查询时的强制规则

所有查询 必须默认过滤

where={"is_deleted": False}


Scope Filter 必须包含软删除条件

13.3 硬删除规则

仅 ADMIN 可执行

仅限以下场景：

测试数据

明确标记为可硬删的表

必须写审计日志

十四、 审计日志触发规则（何时记录）

本板块只定义 “什么时候必须记”，不定义实现

14.1 必须记录的操作

登录 / 登出

角色变更

权限变更

删除操作（软 / 硬）

批量操作

数据导出

管理员操作

14.2 审计日志最小字段集

operator_id

action

target_type

target_id

timestamp

success / failure