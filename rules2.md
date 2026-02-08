# CRM 权限模型设计（RBAC + 数据权限 + 字段权限）

> 本文是 **规则文件的延伸与落地**，用于明确：
>
> * 权限如何拆分
> * 权限如何存储
> * 权限如何在 NestJS 中校验
> * AI 在生成权限相关代码时必须遵守的模型

---

## 一、权限设计目标（先统一思想）

你的 CRM 权限目标不是“能不能访问”，而是：

> **谁，在什么场景下，对哪一条数据，能做什么，能看到哪些字段**

因此权限模型必须同时满足：

* 可配置（不能写死）
* 可扩展（以后加部门 / 加页面不炸）
* 可审计（能回答“为什么他能看到/改这个”）

---

## 二、权限整体拆分（四维模型）

所有权限 **必须同时经过以下四类判断**：

```text
页面权限（Page）
  ↓
行为权限（Action）
  ↓
数据范围权限（Scope）
  ↓
字段权限（Field）
```

缺任何一层，都不允许执行。

---

## 三、权限类型一：页面权限（Page Permission）

### 3.1 定义

页面权限用于：

* 控制菜单是否可见
* 控制路由是否可访问

### 3.2 页面权限标识（与你前端变量名保持一致）

```text
dashboard
submitclue
playerlist
ordermanage
usermanage
rolemanage
projectmanage
formmanage
operationlogs
profile
```

### 3.3 存储建议

```text
PermissionPage
- id
- code        # dashboard / playerlist
- name        # 页面名称
- description
```

---

## 四、权限类型二：行为权限（Action Permission）

### 4.1 定义

行为权限控制：

> “在这个页面 / 资源上，能不能做某个动作”

### 4.2 标准行为集合（统一语义）

```text
view
create
edit
delete
claim        # 认领
transfer     # 流转
export
import
assign       # 分配
```

> ⚠️ 禁止随意发明新 action，必须评审后增加

### 4.3 示例

```text
playerlist:view
playerlist:edit
playerlist:claim
```

---

## 五、权限类型三：数据范围权限（Scope Permission）【核心】

### 5.1 为什么这是你系统的核心

主管 / 组长 / 组员的 **本质区别不是能不能进页面，而是“能看到谁的数据”**。

### 5.2 标准数据范围枚举

```ts
SELF        // 仅自己
GROUP       // 本组
DEPARTMENT  // 本部门
ALL         // 全部
```

### 5.3 作用方式

数据范围权限 **不单独生效**，必须与 Action 组合：

```text
playerlist:view + scope:GROUP
```

### 5.4 技术实现原则

* Scope 必须在 **Service 层** 转换为查询条件
* Repository 不感知 scope 语义

---

## 六、权限类型四：字段权限（Field Permission）【高风险区】

### 6.1 定义

字段权限控制：

> “这条数据的哪些字段，对我可见 / 可编辑”

### 6.2 字段权限行为

```text
read
write
hidden
```

### 6.3 示例

```text
player.phone:read
player.phone:hidden
player.remark:write
```

### 6.4 强制规则

* 字段权限 **必须由后端裁剪数据**
* 前端隐藏不算权限控制

---

## 七、角色的真实定位（非常重要）

### 7.1 角色不是权限判断条件

> **代码中禁止出现：**

```ts
if (user.role === 'admin')
```

### 7.2 角色的唯一作用

* 作为一组 **默认权限模板**
* 新用户创建时批量赋权

### 7.3 角色拆分建议（逻辑模型）

```text
系统角色：admin / subadmin
部门角色：spread / gs
职级角色：manager / leader / agent
```

最终用户权限 = 多角色权限合并 + 用户自定义覆盖

---

## 八、用户权限合成规则（必须统一）

### 8.1 权限来源优先级

```text
用户自定义权限 > 角色权限
```

### 8.2 合并原则

* allow > deny
* 字段权限：hidden > read > write

---

## 九、NestJS 中的权限校验落点

### 9.1 Controller 层（声明）

```ts
@RequirePermission({
  page: 'playerlist',
  action: 'edit'
})
```

Controller **只声明，不判断**。

---

### 9.2 Guard 层（粗校验）

* 是否有 page + action 权限
* 是否已登录

---

### 9.3 Service 层（精校验）

* 数据 scope 转换为 where 条件
* 是否允许对这条数据执行该 action

---

## 十、WebSocket 权限模型

### 10.1 推送原则

```text
谁“理论上能在页面看到这条数据”，谁才可能收到推送
```

### 10.2 禁止行为

* 不经权限判断直接广播
* 推送包含字段权限外的数据

---

## 十一、必须提前预留的扩展点

* 字段权限与表单配置绑定
* scope 后期支持“跨组但非全量”
* 权限变更后实时生效（Redis / Cache）

---

## 十二、AI 编码强制约束（权限相关）

AI 在生成权限相关代码时：

1. 必须说明：

   * 使用了哪几类权限
   * 校验发生在哪一层

2. 禁止：

   * 在 Controller / Repository 写权限判断
   * 写死角色判断

3. 所有权限校验必须可追踪、可解释。

---

> **本权限模型是整个 CRM 的“安全边界”**
> 后续所有模块（player / order / dashboard）都必须基于本模型实现。
