<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue';
import { NButton, NTag } from 'naive-ui';
import {
  createDepartment,
  createTeam,
  fetchDepartmentList,
  fetchTeamList,
  fetchUserList,
  fetchUserOptions,
  updateUser
} from '@/service/api/user';
import { fetchRoleList } from '@/service/api/role';
import OrganizationChart from '@/components/business/organization-chart.vue';

const loading = ref(false);
const tableData = ref<Api.User.UserItem[]>([]);
const total = ref(0);

const pagination = reactive({
  page: 1,
  pageSize: 20
});

const searchKeyword = ref('');
const searchRole = ref<string | undefined>(undefined);

const ROLE_LABEL_FALLBACK: Record<string, string> = {
  ADMIN: '超级管理员',
  SUB_ADMIN: '子管理员',
  QGS_DIRECTOR: '前端主管',
  QGS_LEADER: '前端组长',
  QGS_MEMBER: '前端成员',
  HGS_DIRECTOR: '后端主管',
  HGS_LEADER: '后端组长',
  HGS_MEMBER: '后端成员',
  PENDING_MEMBER: '待审核成员'
};

const roleLabelMap = ref<Record<string, string>>({ ...ROLE_LABEL_FALLBACK });
const roleOptions = ref<{ label: string; value: string }[]>([]);
const departmentOptions = ref<Api.User.DepartmentItem[]>([]);
const teamOptions = ref<Api.User.TeamItem[]>([]);
const userOptions = ref<Api.User.UserOption[]>([]);

const modalVisible = ref(false);
const modalLoading = ref(false);
const currentUser = ref<Api.User.UserItem | null>(null);
const suppressOrgWatch = ref(false);

const createDepartmentVisible = ref(false);
const createDepartmentLoading = ref(false);
const createDepartmentName = ref('');

const createTeamVisible = ref(false);
const createTeamLoading = ref(false);
const createTeamModel = reactive<{
  name: string;
  department_id: number | null;
}>({
  name: '',
  department_id: null
});

const formModel = reactive<{
  role: string | null;
  department_id: number | null;
  team_id: number | null;
  managed_team_ids: number[];
  manager_id: number | null;
  managed_user_ids: number[];
  is_admin: boolean;
  enabled: boolean;
}>({
  role: null,
  department_id: null,
  team_id: null,
  managed_team_ids: [],
  manager_id: null,
  managed_user_ids: [],
  is_admin: false,
  enabled: true
});

const orgChartVisible = ref(false);
const orgChartUsers = ref<Api.User.UserItem[]>([]);

async function showOrgChart() {
  try {
    const { data, error } = await fetchUserList({ page: 1, page_size: 1000 });
    if (!error && Array.isArray(data?.items)) {
      orgChartUsers.value = data.items;
      orgChartVisible.value = true;
    }
  } catch {
    window.$message?.error('加载组织架构失败');
  }
}

function isDirectorRole(role: string | null | undefined) {
  return role === 'QGS_DIRECTOR' || role === 'HGS_DIRECTOR';
}

function getDepartmentFromRole(role: string | null): string {
  if (!role) return '未设置';
  if (role.startsWith('QGS_')) return 'QGS';
  if (role.startsWith('HGS_')) return 'HGS';
  return '未知';
}

function getDepartmentIdFromRole(role: string): number | null {
  if (role.startsWith('QGS_')) return 1;
  if (role.startsWith('HGS_')) return 2;
  return null;
}

const isDirectorFormRole = computed(() => isDirectorRole(formModel.role));

function getManageableRoles(role: string | null | undefined): string[] {
  if (role === 'ADMIN') {
    return [
      'SUB_ADMIN',
      'QGS_DIRECTOR',
      'QGS_LEADER',
      'QGS_MEMBER',
      'HGS_DIRECTOR',
      'HGS_LEADER',
      'HGS_MEMBER',
      'PENDING_MEMBER'
    ];
  }
  if (role === 'SUB_ADMIN') {
    return ['QGS_DIRECTOR', 'QGS_LEADER', 'QGS_MEMBER', 'HGS_DIRECTOR', 'HGS_LEADER', 'HGS_MEMBER', 'PENDING_MEMBER'];
  }
  if (role === 'QGS_DIRECTOR') return ['QGS_LEADER', 'QGS_MEMBER', 'PENDING_MEMBER'];
  if (role === 'QGS_LEADER') return ['QGS_MEMBER', 'PENDING_MEMBER'];
  if (role === 'HGS_DIRECTOR') return ['HGS_LEADER', 'HGS_MEMBER', 'PENDING_MEMBER'];
  if (role === 'HGS_LEADER') return ['HGS_MEMBER', 'PENDING_MEMBER'];
  return [];
}

function canManageRole(managerRole: string | null | undefined, targetRole: string | null | undefined) {
  if (!managerRole || !targetRole) return false;
  return getManageableRoles(managerRole).includes(targetRole);
}

function getUserOptionLabel(item: Api.User.UserOption) {
  return item.alias?.trim() ? `${item.alias} (${item.user})` : item.user;
}

const isManagerFormRole = computed(() => getManageableRoles(formModel.role).length > 0);

const managerSelectOptions = computed(() => {
  const targetRole = formModel.role || 'PENDING_MEMBER';
  const currentId = currentUser.value?.id;
  return userOptions.value
    .filter(item => item.id !== currentId && canManageRole(item.role, targetRole))
    .map(item => ({
      label: `${getUserOptionLabel(item)} · ${getRoleLabel(item.role)}`,
      value: item.id
    }));
});

function getRoleLabel(role: string | null | undefined) {
  if (!role) return '-';
  return roleLabelMap.value[role] || role;
}

function getRoleTagColor(role: string | null | undefined) {
  if (!role) return { color: '#f3f4f6', textColor: '#6b7280', borderColor: '#e5e7eb' };
  if (role.includes('ADMIN')) return { color: '#fff7ed', textColor: '#c2410c', borderColor: '#fed7aa' };
  if (role.startsWith('QGS')) return { color: '#eff6ff', textColor: '#1d4ed8', borderColor: '#bfdbfe' };
  if (role.startsWith('HGS')) return { color: '#f5f3ff', textColor: '#6d28d9', borderColor: '#ddd6fe' };
  if (role === 'PENDING_MEMBER') return { color: '#f3f4f6', textColor: '#6b7280', borderColor: '#e5e7eb' };
  return { color: '#eef2ff', textColor: '#4338ca', borderColor: '#c7d2fe' };
}

function getOrgTagColor(kind: 'department' | 'team') {
  if (kind === 'department') return { color: '#ecfeff', textColor: '#0e7490', borderColor: '#a5f3fc' };
  return { color: '#faf5ff', textColor: '#7e22ce', borderColor: '#e9d5ff' };
}

function getUnassignedTagColor() {
  return { color: '#f9fafb', textColor: '#6b7280', borderColor: '#e5e7eb' };
}

function getTeamDisplayText(row: Api.User.UserItem) {
  return row.team_name ?? (row.team_id === null ? '未分配' : '-');
}

function getTeamTagColor(row: Api.User.UserItem) {
  return row.team_id === null ? getUnassignedTagColor() : getOrgTagColor('team');
}

function getManagerDisplayText(row: Api.User.UserItem) {
  return row.manager_name ?? (row.manager_id ? `#${row.manager_id}` : '未设置');
}

const columns: NaiveUI.DataTableBaseColumn<Api.User.UserItem>[] = [
  { title: '用户名', key: 'user', width: 120 },
  { title: '花名', key: 'alias', width: 100, render: row => row.alias || '-' },
  { title: '邮箱', key: 'email', width: 180 },
  {
    title: '角色',
    key: 'role',
    width: 130,
    render: row =>
      h(
        NTag,
        {
          bordered: false,
          color: getRoleTagColor(row.role)
        },
        { default: () => getRoleLabel(row.role) }
      )
  },
  {
    title: '部门',
    key: 'department_name',
    width: 130,
    render: row =>
      h(
        NTag,
        {
          bordered: false,
          color: row.department_id === null ? getUnassignedTagColor() : getOrgTagColor('department')
        },
        { default: () => row.department_name ?? (row.department_id === null ? '未分配' : '-') }
      )
  },
  {
    title: '团队',
    key: 'team_name',
    width: 220,
    render: row =>
      h(
        NTag,
        {
          bordered: false,
          color: getTeamTagColor(row)
        },
        { default: () => getTeamDisplayText(row) }
      )
  },
  {
    title: '直属上级',
    key: 'manager_name',
    width: 180,
    render: row =>
      h(
        NTag,
        {
          bordered: false,
          color: row.manager_id ? getOrgTagColor('department') : getUnassignedTagColor()
        },
        { default: () => getManagerDisplayText(row) }
      )
  },
  {
    title: '启用/停用',
    key: 'enabled',
    width: 100,
    render: row =>
      h(
        NTag,
        {
          type: row.enabled !== false ? 'success' : 'error',
          bordered: false
        },
        { default: () => (row.enabled !== false ? '启用' : '停用') }
      )
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    fixed: 'right',
    render: row =>
      h(
        NButton,
        {
          size: 'small',
          quaternary: true,
          type: 'primary',
          onClick: () => openAssignModal(row)
        },
        { default: () => '操作' }
      )
  }
];

async function loadData() {
  loading.value = true;
  try {
    const { data, error } = await fetchUserList({
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchKeyword.value || undefined,
      role: searchRole.value
    });
    tableData.value = !error && Array.isArray(data?.items) ? data.items : [];
    total.value = !error && typeof data?.total === 'number' ? data.total : 0;
  } catch {
    tableData.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

async function loadRoleOptions() {
  try {
    const { data, error } = await fetchRoleList();
    roleOptions.value = !error && Array.isArray(data) ? data.map(r => ({ label: r.label, value: r.role })) : [];
    if (!error && Array.isArray(data)) {
      roleLabelMap.value = {
        ...ROLE_LABEL_FALLBACK,
        ...Object.fromEntries(data.map(item => [item.role, item.label]))
      };
    }
  } catch {
    roleOptions.value = [];
    roleLabelMap.value = { ...ROLE_LABEL_FALLBACK };
  }
}

async function loadDepartmentOptions() {
  try {
    const { data, error } = await fetchDepartmentList();
    departmentOptions.value = !error && Array.isArray(data) ? data : [];
  } catch {
    departmentOptions.value = [];
  }
}

async function loadTeamOptions(departmentId?: number | null) {
  try {
    const { data, error } = await fetchTeamList(departmentId);
    teamOptions.value = !error && Array.isArray(data) ? data : [];
  } catch {
    teamOptions.value = [];
  }
}

async function loadUserOptions() {
  try {
    const { data, error } = await fetchUserOptions();
    userOptions.value = !error && Array.isArray(data) ? data : [];
  } catch {
    userOptions.value = [];
  }
}

function openCreateTeamModal() {
  createTeamModel.name = '';
  createTeamModel.department_id = formModel.department_id ?? null;
  createTeamVisible.value = true;
}

async function submitCreateDepartment() {
  const name = createDepartmentName.value.trim();
  if (!name) {
    window.$message?.warning('请输入部门名称');
    return;
  }
  createDepartmentLoading.value = true;
  try {
    const { data, error } = await createDepartment({ name });
    if (error || !data) return;
    await loadDepartmentOptions();
    formModel.department_id = data.id;
    formModel.team_id = null;
    formModel.managed_team_ids = [];
    await loadTeamOptions(data.id);
    createDepartmentVisible.value = false;
    window.$message?.success('部门已新增');
  } finally {
    createDepartmentLoading.value = false;
  }
}

async function submitCreateTeam() {
  const name = createTeamModel.name.trim();
  if (!name) {
    window.$message?.warning('请输入团队名称');
    return;
  }
  if (!createTeamModel.department_id) {
    window.$message?.warning('请选择所属部门');
    return;
  }
  createTeamLoading.value = true;
  try {
    const { data, error } = await createTeam({
      name,
      department_id: createTeamModel.department_id
    });
    if (error || !data) return;

    formModel.department_id = data.department_id;
    await loadTeamOptions(data.department_id);

    if (isDirectorFormRole.value) {
      if (!formModel.managed_team_ids.includes(data.id)) {
        formModel.managed_team_ids = [...formModel.managed_team_ids, data.id];
      }
      formModel.team_id = null;
    } else {
      formModel.team_id = data.id;
      formModel.managed_team_ids = [];
    }

    createTeamVisible.value = false;
    window.$message?.success('团队已新增');
  } finally {
    createTeamLoading.value = false;
  }
}

function openAssignModal(row: Api.User.UserItem) {
  suppressOrgWatch.value = true;

  currentUser.value = row;
  formModel.role = row.role;
  formModel.department_id = row.department_id ?? null;
  formModel.team_id = row.team_id ?? null;
  formModel.managed_team_ids = [];
  formModel.manager_id = row.manager_id ?? null;
  formModel.managed_user_ids = Array.isArray(row.managed_user_ids) ? [...row.managed_user_ids] : [];
  formModel.is_admin = row.is_admin;
  formModel.enabled = row.enabled !== false;

  modalVisible.value = true;
  const deptId = row.role ? getDepartmentIdFromRole(row.role) : null;
  loadTeamOptions(deptId).finally(() => {
    suppressOrgWatch.value = false;
  });
}

watch(
  () => formModel.role,
  role => {
    if (suppressOrgWatch.value) return;

    formModel.team_id = null;
    formModel.managed_team_ids = [];

    const deptId = role ? getDepartmentIdFromRole(role) : null;
    if (deptId) {
      loadTeamOptions(deptId);
    }

    const currentManager = userOptions.value.find(item => item.id === formModel.manager_id);
    const normalizedRole = role || 'PENDING_MEMBER';
    if (!currentManager || !canManageRole(currentManager.role, normalizedRole)) {
      formModel.manager_id = null;
    }

    const manageableRoleSet = new Set(getManageableRoles(role));
    if (manageableRoleSet.size === 0) {
      formModel.managed_user_ids = [];
    } else {
      formModel.managed_user_ids = formModel.managed_user_ids.filter(managedUserId => {
        const managedUser = userOptions.value.find(item => item.id === managedUserId);
        return Boolean(managedUser && manageableRoleSet.has(managedUser.role));
      });
    }
  }
);

watch(
  () => formModel.manager_id,
  managerId => {
    if (managerId === null) return;
    formModel.managed_user_ids = formModel.managed_user_ids.filter(userId => userId !== managerId);
  }
);

async function submitAssign() {
  if (!currentUser.value) return;

  modalLoading.value = true;
  try {
    const { error } = await updateUser(currentUser.value.id, {
      role: formModel.role ?? null,
      department_id: null,
      team_id: formModel.team_id,
      managed_team_ids: [],
      manager_id: formModel.manager_id,
      managed_user_ids: isManagerFormRole.value
        ? formModel.managed_user_ids.filter(userId => userId !== formModel.manager_id)
        : [],
      is_admin: formModel.is_admin,
      enabled: formModel.enabled
    });

    if (error) return;

    window.$message?.success('已保存');
    modalVisible.value = false;
    await Promise.all([loadData(), loadUserOptions()]);
  } finally {
    modalLoading.value = false;
  }
}

function onSearch() {
  pagination.page = 1;
  loadData();
}

function onPageChange(page: number) {
  pagination.page = page;
  loadData();
}

function onPageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize;
  pagination.page = 1;
  loadData();
}

function getUserRowKey(row: Api.User.UserItem) {
  return row.id;
}

onMounted(() => {
  loadData();
  loadRoleOptions();
  loadDepartmentOptions();
  loadUserOptions();
});
</script>

<template>
  <div class="min-h-500px">
    <NCard title="用户管理" :bordered="false">
      <template #header-extra>
        <NSpace align="center">
          <NInput
            v-model:value="searchKeyword"
            placeholder="用户名/花名/邮箱"
            clearable
            class="w-180px"
            @keyup.enter="onSearch"
          />
          <NSelect v-model:value="searchRole" placeholder="角色" clearable :options="roleOptions" class="w-140px" />
          <NButton type="primary" @click="onSearch">查询</NButton>
          <NButton @click="showOrgChart">组织架构</NButton>
        </NSpace>
      </template>

      <NDataTable :columns="columns" :data="tableData" :loading="loading" :row-key="getUserRowKey" />

      <div class="flex justify-end pt-4">
        <NPagination
          v-model:page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :item-count="total"
          :page-sizes="[10, 20, 50]"
          show-size-picker
          @update:page="onPageChange"
          @update:page-size="onPageSizeChange"
        />
      </div>
    </NCard>

    <NModal
      v-model:show="modalVisible"
      :title="currentUser ? `操作 - ${currentUser.user}` : '操作'"
      preset="card"
      class="w-420px"
    >
      <NForm :model="formModel" label-placement="left" label-width="80">
        <NFormItem label="角色">
          <NSelect v-model:value="formModel.role" :options="roleOptions" placeholder="选择角色" clearable />
        </NFormItem>

        <NFormItem label="部门">
          <NInput :value="getDepartmentFromRole(formModel.role)" readonly placeholder="根据角色自动设置" />
          <div class="mt-1 text-xs text-gray-400"></div>
        </NFormItem>

        <NFormItem label="团队">
          <NSelect
            v-model:value="formModel.team_id"
            :options="teamOptions.map(t => ({ label: t.name, value: t.id }))"
            :placeholder="isDirectorFormRole ? '选择管理的团队（可选）' : '选择团队（可留空待分配）'"
            clearable
          >
            <template #action>
              <div class="flex justify-end py-1">
                <NButton text type="primary" size="small" @click.stop="openCreateTeamModal">+ 新增团队</NButton>
              </div>
            </template>
          </NSelect>
          <div v-if="isDirectorFormRole" class="mt-1 text-xs text-gray-400"></div>
        </NFormItem>

        <NFormItem label="直属上级">
          <NSelect
            v-model:value="formModel.manager_id"
            :options="managerSelectOptions"
            placeholder="选择直属上级（按角色层级过滤）"
            clearable
          />
        </NFormItem>

        <NFormItem label="启用/停用">
          <NSwitch v-model:value="formModel.enabled" />
        </NFormItem>
      </NForm>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="modalVisible = false">取消</NButton>
          <NButton type="primary" :loading="modalLoading" @click="submitAssign">保存</NButton>
        </NSpace>
      </template>
    </NModal>

    <NModal v-model:show="createDepartmentVisible" title="新增部门" preset="card" class="w-420px">
      <NForm label-placement="left" label-width="80">
        <NFormItem label="部门名称">
          <NInput v-model:value="createDepartmentName" placeholder="请输入部门名称" maxlength="64" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="createDepartmentVisible = false">取消</NButton>
          <NButton type="primary" :loading="createDepartmentLoading" @click="submitCreateDepartment">确定</NButton>
        </NSpace>
      </template>
    </NModal>

    <NModal v-model:show="createTeamVisible" title="新增团队" preset="card" class="w-420px">
      <NForm :model="createTeamModel" label-placement="left" label-width="80">
        <NFormItem label="所属部门">
          <NSelect
            v-model:value="createTeamModel.department_id"
            :options="departmentOptions.map(d => ({ label: d.name, value: d.id }))"
            placeholder="请选择部门"
          />
        </NFormItem>

        <NFormItem label="团队名称">
          <NInput v-model:value="createTeamModel.name" placeholder="请输入团队名称" maxlength="64" />
        </NFormItem>
      </NForm>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="createTeamVisible = false">取消</NButton>
          <NButton type="primary" :loading="createTeamLoading" @click="submitCreateTeam">确定</NButton>
        </NSpace>
      </template>
    </NModal>

    <NModal v-model:show="orgChartVisible" title="组织架构图" preset="card" class="w-90vw">
      <OrganizationChart :users="orgChartUsers" />
    </NModal>
  </div>
</template>

<style scoped></style>
