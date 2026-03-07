# 玩家列表数据显示问题修复总结

## 问题描述
玩家列表数据未按照角色层级正确显示，导致上级角色无法看到下级提交的数据。

## 根本原因
1. **数据完整性问题**：Player 表和 User 表的 `department_id` 和 `team_id` 字段存在 NULL 值
2. **权限范围配置问题**：SUB_ADMIN 角色被配置为 DEPARTMENT 范围，但其 `department_id` 为 NULL
3. **数据不一致问题**：Player 记录的 `team_id` 与提交者当前的 `team_id` 不一致（用户调岗后历史数据未更新）

## 修复内容

### 1. 修复历史数据
**`fix_player_scope.py`** - 填充空值
- 从 Team 表获取 `department_id`，填充 User 表的空值
- 从 User 表获取 `department_id` 和 `team_id`，填充 Player 表的空值
- 修复了 8 个用户和 12 条 Player 记录

**`fix_team_mismatch.py`** - 同步用户调岗
- 将 Player 记录的 `department_id` 和 `team_id` 更新为提交者当前的值
- 修复了 4 条记录（User 3 和 User 9 从 Team 1 调到 Team 5 后的历史数据）

### 2. 修复权限范围逻辑 (`backend/app/core/scope.py`)
**修改前**：
```python
if role == Role.SUB_ADMIN:
    return DataScope.DEPARTMENT  # 需要 department_id，但 SUB_ADMIN 通常没有
```

**修改后**：
```python
if role in (Role.ADMIN, Role.SUB_ADMIN):
    return DataScope.ALL  # SUB_ADMIN 也应该看到所有数据
```

## 验证结果

### 角色层级数据可见范围（修复后）：
- ✅ **ADMIN**: 可见所有 16 条记录
- ✅ **SUB_ADMIN**: 可见所有 16 条记录（修复前：0 条）
- ✅ **QGS_DIRECTOR** (Dept 1): 可见部门内 12 条记录
- ✅ **QGS_LEADER** (Team 5): 可见团队内 12 条记录（修复前：8 条，缺少 4 条调岗用户的历史数据）
- ✅ **QGS_MEMBER** (User 3): 可见自己的 4 条记录
- ✅ **QGS_MEMBER** (User 12): 可见自己的 7 条记录
- ✅ **HGS_DIRECTOR** (Dept 2): 可见部门内 0 条记录（该部门暂无数据）
- ✅ **HGS_LEADER** (Team 7): 可见团队内 0 条记录（该团队暂无数据）
- ✅ **HGS_MEMBER**: 只能看到自己提交的记录

### 层级关系验证：
```
ADMIN/SUB_ADMIN (ALL)
    └── DIRECTOR (DEPARTMENT)
            └── LEADER (TEAM)
                    └── MEMBER (SELF)
```

## 工具脚本

### 1. `check_player_scope.py` - 检查数据完整性
查看 Player 和 User 表的 `department_id` 和 `team_id` 字段

### 2. `fix_player_scope.py` - 修复空值数据
自动填充缺失的 `department_id` 和 `team_id`

### 3. `fix_team_mismatch.py` - 修复数据不一致
将 Player 的 `department_id` 和 `team_id` 同步为提交者当前的值

### 4. `analyze_qgs_leader.py` - 分析特定角色的数据可见性
详细分析 QGS_LEADER 能看到和看不到的数据及原因

### 5. `verify_scope.py` - 验证权限范围
测试所有角色能看到的数据范围是否正确

## 后续建议

1. **数据库约束**：考虑为 User 表添加约束，确保非 ADMIN/SUB_ADMIN 角色必须有 `department_id` 和 `team_id`
2. **前端验证**：在用户注册/编辑时，前端应验证必填字段
3. **定期检查**：定期运行 `check_player_scope.py` 检查数据完整性

## 修改的文件
- ✅ `backend/app/core/scope.py` - 修复 SUB_ADMIN 权限范围
- ✅ `backend/fix_player_scope.py` - 填充空值数据（新增）
- ✅ `backend/fix_team_mismatch.py` - 同步用户调岗数据（新增）
- ✅ `backend/check_player_scope.py` - 数据检查脚本（新增）
- ✅ `backend/analyze_qgs_leader.py` - 数据可见性分析脚本（新增）
- ✅ `backend/verify_scope.py` - 权限验证脚本（新增）
