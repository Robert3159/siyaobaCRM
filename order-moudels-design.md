# CRM 订单模块设计文档

## 模块路径

# hgs/order

订单模块用于管理从外部文件导入的订单数据，并用于统计 GS 业绩。

订单来源为上级后台导出的订单文件，不同项目字段格式可能不同，因此系统需要支持：

- 多格式文件导入
- 字段动态映射
- 玩家归属匹配
- 项目数据隔离
- 导入日志记录

---

# 一、支持导入文件格式

订单导入需要支持以下格式：
- .csv
- .xlsx
- .xls

系统需要自动识别文件类型并解析。

---

# 二、订单表结构（order_form）

订单统一存储在 `order_form` 表

| 字段 | 说明 |
|----|----|
| id | 主键 |
| project_id | 项目ID |
| order_no | 订单号 |
| player_id | 玩家ID |
| player_name | 玩家名字 |
| server | 区服 |
| amount | 充值金额 |
| order_time | 充值时间 |
| qgs__author | 前端GS |
| hgs_maintainer | 后端GS |
| raw_data | 原始订单JSON |
| created_at | 创建时间 |

说明：

- `project_id` 用于区分不同项目订单 （字段已存在于玩家列表，可直接调用）
- `qgs__author`、`hgs_maintainer` 为冗余字段，用于加快统计 （字段已存在于玩家列表，可直接调用）
- `raw_data` 用于保存未映射字段

---

# 三、字段动态映射

由于不同项目订单字段名称不同，需要支持字段映射功能。例如：

## 项目A订单字段
玩家ID  
区服  
充值金额  

## 项目B订单字段
user_id  
server  
amount  

## 系统统一字段
player_id  
server  
amount  

导入时需要支持：
- 自动匹配字段
- 手动选择映射字段

示例：
| 文件字段 | 系统字段 |
|------|------|
| 玩家ID | player_id |
| 区服 | server |
| 充值金额 | amount |

---

# 四、字段映射配置表

需要新增表：order_field_mapping

字段结构：
| 字段 | 说明 |
|----|----|
| id | 主键 |
| project_id | 项目ID |
| file_field | 文件字段名 |
| system_field | 系统字段名 |
| created_at | 创建时间 |

作用：保存每个项目的字段映射规则。

例如：
| project_id | file_field | system_field |
|---|---|---|
| 1 | 玩家ID | player_id |
| 1 | 区服 | server |
| 1 | 充值金额 | amount |

同一项目再次导入时可以自动匹配字段。

---

# 五、订单原始字段保存

订单文件中未映射的字段需要保留。

例如订单文件包含：
订单号  
玩家ID  
区服  
充值金额  
渠道  
货币  
礼包ID  

未映射字段：
渠道  
货币  
礼包ID  

需要保存到：
raw_data (JSON)

示例：{
"渠道": "Google",
"货币": "USD",
"礼包ID": "A100"
}

这样可以避免丢失原始数据。

---

# 六、玩家归属匹配

导入订单后，需要根据 player_id 查询：

player_form.fld_69f9b1e5c01d (玩家ID)

匹配玩家归属信息。

需要获取：
- qgs__author
- hgs_maintainer

并写入订单表。

匹配逻辑：
order.player_id  
↓  
player_form.fld_69f9b1e5c01d  
↓  
获取 qgs__author / hgs_maintainer  

如果未找到玩家：
qgs__author = null
hgs_maintainer = null

---

# 七、订单导入流程

导入流程如下：
上传订单文件  
↓  
解析文件表头  
↓  
自动匹配字段  
↓  
用户手动确认字段映射  
↓  
预览前10条订单数据  
↓  
确认导入  
↓  
写入 order_form  

---

# 八、订单导入预览

导入前需要展示：前10条订单数据

用于确认：
- 字段映射是否正确
- 金额字段是否正确
- 时间字段是否正确

确认后才执行导入。

---

# 九、重复订单控制

需要防止重复导入。

使用：order_no作为唯一值。

数据库增加：unique(order_no)

如果订单没有订单号, 使用组合唯一：project_id + player_id + order_time + amount

---

# 十、订单导入日志表

需要新增导入日志表：order_import_logs

字段结构：
| 字段 | 说明 |
|----|----|
| id | 主键 |
| project_id | 项目 |
| filename | 导入文件 |
| total_rows | 总记录数 |
| success_rows | 成功数量 |
| fail_rows | 失败数量 |
| import_user | 导入用户 |
| status | 状态 |
| created_at | 创建时间 |

示例：
| 文件 | 总条数 | 成功 | 失败 |
|----|----|----|----|
| order_0308.xlsx | 2000 | 1980 | 20 |

---

# 十一、订单列表页面（hgs/order）

页面路径：./hgs/order

列表需要显示字段：
- 订单号
- 项目
- 玩家ID
- 玩家名字
- 区服
- 充值金额
- 充值时间
- 前端GS（qgs__author）
- 后端GS（hgs_maintainer）
- 创建时间

---

# 十二、订单列表功能

需要支持筛选：
- 项目
- 玩家ID
- 前端GS
- 后端GS
- 时间范围

支持排序：
- 充值时间
- 充值金额
- 创建时间

---

# 十三、导入订单按钮

订单列表页面顶部需要提供 "导入订单" 按钮。

点击进入订单导入流程。

---

# 十四、按钮权限控制

导入订单按钮仅对以下角色可见：

- admin
- subadmin

其他角色不可见。

---

# 十五、数据库索引建议

建议增加索引：
player_id  
order_time  
qgs__author  
hgs_maintainer  
project_id  

这样可以提升订单统计和查询性能。

---

# 十六、模块功能总结

订单模块需要实现：
- 订单文件导入
- 多格式文件解析
- 字段动态映射
- 字段映射规则保存
- 订单数据预览
- 玩家归属匹配
- 项目数据隔离
- 原始数据保存
- 重复订单控制
- 订单导入日志
- 订单列表查询
