# CRM 项目 AI 编程规则文件（NestJS）

> 本文件用于 **约束 AI（以及人类开发者）在本项目中的编码行为**，确保代码长期可维护、权限安全、结构一致。
> 适用于：ChatGPT / Cursor / Copilot / Claude 等 AI 编程工具。

---

## 一、项目目标与架构原则

### 1.1 项目目标

* 构建一个 **公司内部使用的 CRM 系统**
* 核心业务：**游戏推广数据提交 → 认领 → 跟进 → 流转 → 统计 → 预警**
* 核心难点：

  * 强权限控制（角色 / 数据 / 字段 / 行为）
  * 实时通知（WebSocket）
  * 可审计、可回溯

### 1.2 架构基本原则（强制）

* 单体 NestJS 后端（非微服务）
* 模块化、领域驱动（按业务域拆 Module）
* **业务复杂度优先于性能优化**
* 所有权限规则必须可配置，不可硬编码

---

## 二、技术栈与硬性约束

### 2.1 技术栈

* Node.js >= 18
* NestJS
* TypeScript（strict = true）
* ORM：Prisma
* 数据库：PostgreSQL
* 缓存 / 消息：Redis
* WebSocket：NestJS Gateway
* 鉴权：JWT + RBAC

### 2.2 硬性约束（禁止项）

* ❌ 禁止在 Controller 中直接访问 ORM
* ❌ 禁止跨 Module 直接访问 Repository
* ❌ 禁止在 Service 中返回 ORM Entity
* ❌ 禁止在代码中写死角色判断（如 if role === 'admin'）
* ❌ 禁止生成未使用的 DTO / Entity / Service

---

## 三、目录结构规范（必须遵守）

```text
src/
├─ modules/                # 所有业务模块
│  ├─ user/
│  ├─ auth/
│  ├─ role/
│  ├─ permission/
│  ├─ project/
│  ├─ form/
│  ├─ player/
│  ├─ order/
│  ├─ dashboard/
│  ├─ websocket/
│  └─ operation-log/
│
├─ common/                 # 全局通用能力
│  ├─ decorators/
│  ├─ guards/
│  ├─ interceptors/
│  ├─ filters/
│  ├─ enums/
│  ├─ utils/
│  └─ constants/
│
├─ prisma/                 # Prisma schema & migrations
├─ config/                 # 配置文件
└─ main.ts
```

* 一个业务域 = 一个 Module
* Module 之间只能通过 **Service** 交互

---

## 四、模块设计规范（最重要）

### 4.1 模块内部结构

```text
player/
├─ player.module.ts
├─ player.controller.ts
├─ player.service.ts
├─ player.repository.ts
├─ dto/
│  ├─ create-player.dto.ts
│  ├─ update-player.dto.ts
│  └─ query-player.dto.ts
└─ player.types.ts
```

### 4.2 各层职责边界（强制）

#### Controller

* 只做：

  * 参数接收
  * DTO 校验
  * 调用 Service
  * 返回 Response DTO

#### Service

* 只做：

  * 业务逻辑
  * 权限校验
  * 状态流转
* 不允许写任何 HTTP 相关逻辑

#### Repository

* 只做：

  * 数据库 CRUD
  * 查询封装
* 不允许写业务判断

---

## 五、权限模型与规则（核心）

### 5.1 权限类型

权限必须拆分为以下四类：

1. 页面权限（page）
2. 行为权限（action）
3. 数据范围权限（scope）
4. 字段权限（field）

### 5.2 角色说明（不可写死逻辑）

```text
admin
subadmin
spreadmanager
spreadleader
spreadagent
gsmanager
gsleader
gsagent
pendinguser
```

* 角色只是权限的 **默认载体**
* 所有用户权限必须支持 override

### 5.3 权限校验规则

* Controller 只声明「需要什么权限」
* 实际权限判断在 Guard / Service 中完成
* 权限来源顺序：

```text
用户自定义权限 > 角色预设权限
```

---

## 六、数据与 DTO 规范

### 6.1 DTO 使用规则

* 所有接口必须使用 DTO
* DTO 必须：

  * 明确字段可选性
  * 明确字段用途

### 6.2 Entity / Model 使用规则

* ORM Entity 只能存在于 Repository 层
* Service / Controller 禁止直接暴露 Entity

---

## 七、WebSocket 规则

### 7.1 使用场景

* 新表单提交
* 表单被认领
* 分配给用户
* 流失预警

### 7.2 强制规则

* WebSocket 推送必须经过权限过滤
* 禁止广播敏感字段

---

## 八、日志与审计规则

### 8.1 日志类型

1. 系统日志（登录、配置）
2. 业务日志（表单、订单、流转）

### 8.2 强制记录场景

* 数据创建 / 修改 / 删除
* 状态流转
* 权限变更

---

## 九、AI 编程行为规则（非常重要）

AI 在本项目中必须遵守以下规则：

1. 新增功能前，必须说明：

   * 涉及模块
   * 涉及权限点
   * 数据模型变化

2. 禁止：

   * 大规模重构未说明原因
   * 修改公共接口不做兼容

3. 所有生成代码必须：

   * 可读
   * 可维护
   * 可扩展

4. 如果需求不明确，必须先提出澄清问题，而不是假设。

---

## 十、规则优先级

```text
安全 & 权限 > 架构规范 > 代码风格 > 性能优化
```

当规则与需求冲突时，必须优先保证：

* 数据安全
* 权限正确
* 行为可审计

---

> 本规则文件是 **项目的一部分**，任何代码都必须服从本规则。
> 后续所有模块开发，均以此为最高准则。
