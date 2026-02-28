<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { NButton, NTag } from 'naive-ui';
import type { TreeOption } from 'naive-ui';
import { fetchMenuList } from '@/service/api/menu';
import { fetchPermissionOptions, fetchRoleDetail, fetchRoleList, updateRole } from '@/service/api/role';

defineOptions({
  name: 'SystemRole'
});

interface RoleTreeOption extends TreeOption {
  key: string;
  label: string;
  routeName: string;
  routePath: string;
  menuId: number;
  children?: RoleTreeOption[];
}

const loading = ref(false);
const roleList = ref<Api.Role.RoleItem[]>([]);
const permissionOptions = ref<Api.Role.PermissionOption[]>([]);
const allMenus = ref<Api.Menu.Item[]>([]);
const permissionLabelMap = computed(() => {
  const map = new Map<string, string>();
  permissionOptions.value.forEach(option => {
    map.set(option.code, option.label);
  });
  return map;
});

const columns: NaiveUI.DataTableBaseColumn<Api.Role.RoleItem>[] = [
  { title: '角色', key: 'label', width: 160 },
  { title: '角色标识', key: 'role', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: row =>
      row.role !== 'PENDING_MEMBER'
        ? h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'primary',
              onClick: () => openRoleModal(row)
            },
            { default: () => '编辑权限与首页' }
          )
        : null
  }
];

const modalVisible = ref(false);
const modalLoading = ref(false);
const currentRole = ref<Api.Role.RoleItem | null>(null);
const checkedPermissions = ref<string[]>([]);
const selectedHomeRoute = ref<string | null>(null);

const activeMenus = computed(() => {
  const flattened: Api.Menu.Item[] = [];

  function walk(nodes: Api.Menu.Item[]) {
    for (const node of nodes) {
      if (node.status) {
        flattened.push(node);
        if (node.children?.length) {
          walk(node.children);
        }
      }
    }
  }

  walk(allMenus.value);
  return flattened;
});

const menuById = computed(() => {
  const map = new Map<number, Api.Menu.Item>();
  activeMenus.value.forEach(menu => {
    map.set(menu.id, menu);
  });
  return map;
});

const activeChildrenMap = computed(() => {
  const map = new Map<number, number[]>();
  for (const menu of activeMenus.value) {
    if (menu.parent_id !== null) {
      const children = map.get(menu.parent_id) || [];
      children.push(menu.id);
      map.set(menu.parent_id, children);
    }
  }
  return map;
});

function getMenuDisplayName(menu: Api.Menu.Item) {
  return permissionLabelMap.value.get(menu.route_name) || menu.menu_name || menu.route_name;
}

const authorizedMenuIds = computed(() => {
  const permissionSet = new Set(checkedPermissions.value);
  const ids = new Set<number>();
  for (const menu of activeMenus.value) {
    if (permissionSet.has(menu.route_name)) {
      ids.add(menu.id);
    }
  }
  return ids;
});

const includedMenuIds = computed(() => {
  const ids = new Set<number>();
  for (const menuId of authorizedMenuIds.value) {
    ids.add(menuId);
    let current = menuById.value.get(menuId);
    while (current && current.parent_id !== null) {
      ids.add(current.parent_id);
      current = menuById.value.get(current.parent_id);
    }
  }
  return ids;
});

const homeRouteCandidates = computed(() => {
  const candidates: Array<{ routeName: string; menuName: string; routePath: string }> = [];
  const seen = new Set<string>();

  function walk(nodes: Api.Menu.Item[]) {
    for (const menu of nodes) {
      if (menu.status && includedMenuIds.value.has(menu.id)) {
        const isLeaf = (activeChildrenMap.value.get(menu.id)?.length || 0) === 0;
        const isAuthorized = authorizedMenuIds.value.has(menu.id);
        if (isAuthorized && (menu.menu_type === 3 || isLeaf) && !seen.has(menu.route_name)) {
          seen.add(menu.route_name);
          candidates.push({
            routeName: menu.route_name,
            menuName: getMenuDisplayName(menu),
            routePath: menu.route_path
          });
        }

        if (menu.children?.length) {
          walk(menu.children);
        }
      }
    }
  }

  walk(allMenus.value);
  return candidates;
});

const candidateRouteNameSet = computed(() => new Set(homeRouteCandidates.value.map(item => item.routeName)));
const homeRouteLabelMap = computed(() => {
  const map = new Map<string, string>();
  homeRouteCandidates.value.forEach(item => {
    map.set(item.routeName, item.menuName);
  });
  return map;
});
const routeLabelMap = computed(() => {
  const map = new Map<string, string>();
  for (const menu of activeMenus.value) {
    map.set(menu.route_name, getMenuDisplayName(menu));
  }
  return map;
});
const selectedHomeRouteLabel = computed(() => {
  if (!selectedHomeRoute.value) {
    return '未配置';
  }
  return (
    homeRouteLabelMap.value.get(selectedHomeRoute.value) ||
    routeLabelMap.value.get(selectedHomeRoute.value) ||
    selectedHomeRoute.value
  );
});

const roleAccessibleMenuTree = computed<RoleTreeOption[]>(() => {
  function toTree(nodes: Api.Menu.Item[]): RoleTreeOption[] {
    const result: RoleTreeOption[] = [];
    for (const menu of nodes) {
      if (menu.status && includedMenuIds.value.has(menu.id)) {
        const children = menu.children?.length ? toTree(menu.children) : [];
        if (menu.hide_in_menu) {
          // 使用条件判断替代 continue
          if (children.length) {
            result.push(...children);
          }
        } else {
          result.push({
            key: menu.route_name,
            label: getMenuDisplayName(menu),
            routeName: menu.route_name,
            routePath: menu.route_path,
            menuId: menu.id,
            children
          });
        }
      }
    }
    return result;
  }

  return toTree(allMenus.value);
});

const selectedTreeKeys = computed(() => (selectedHomeRoute.value ? [selectedHomeRoute.value] : []));

watch(
  () => homeRouteCandidates.value,
  candidates => {
    if (!selectedHomeRoute.value) return;
    const valid = candidates.some(item => item.routeName === selectedHomeRoute.value);
    if (!valid) {
      selectedHomeRoute.value = null;
    }
  },
  { immediate: true, deep: true }
);

function renderTreeLabel({ option }: { option: TreeOption }) {
  const treeOption = option as RoleTreeOption;
  const isCurrentHome = treeOption.routeName === selectedHomeRoute.value;
  const selectable = candidateRouteNameSet.value.has(treeOption.routeName);

  return h('div', { class: 'flex items-center gap-8px' }, [
    h('span', treeOption.label),
    selectable ? h(NTag, { type: 'info', size: 'small', bordered: false }, { default: () => '可设首页' }) : null,
    isCurrentHome ? h(NTag, { type: 'success', size: 'small', bordered: false }, { default: () => '当前首页' }) : null
  ]);
}

function handleTreeSelect(keys: Array<string | number>) {
  const routeName = String(keys[0] || '');
  if (!routeName) return;
  if (!candidateRouteNameSet.value.has(routeName)) return;
  selectedHomeRoute.value = routeName;
}

async function loadRoles() {
  loading.value = true;
  try {
    const { data, error } = await fetchRoleList();
    roleList.value = !error && Array.isArray(data) ? data : [];
  } catch {
    roleList.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadPermissionOptions() {
  try {
    const { data, error } = await fetchPermissionOptions();
    permissionOptions.value = !error && Array.isArray(data) ? data : [];
  } catch {
    permissionOptions.value = [];
  }
}

async function loadMenus() {
  try {
    const { data, error } = await fetchMenuList();
    allMenus.value = !error && Array.isArray(data) ? data : [];
  } catch {
    allMenus.value = [];
  }
}

async function openRoleModal(role: Api.Role.RoleItem) {
  currentRole.value = role;
  modalVisible.value = true;
  if (!allMenus.value.length) {
    await loadMenus();
  }

  try {
    const { data, error } = await fetchRoleDetail(role.role);
    if (error || !data) {
      checkedPermissions.value = [];
      selectedHomeRoute.value = null;
      return;
    }
    checkedPermissions.value = Array.isArray(data.permissions) ? [...data.permissions] : [];
    selectedHomeRoute.value = data.home_route || null;
  } catch {
    checkedPermissions.value = [];
    selectedHomeRoute.value = null;
  }
}

async function submitRoleConfig() {
  if (!currentRole.value) return;
  modalLoading.value = true;
  try {
    const { error } = await updateRole(currentRole.value.role, {
      permissions: checkedPermissions.value,
      home_route: selectedHomeRoute.value
    });
    if (error) return;
    window.$message?.success('角色配置已保存');
    modalVisible.value = false;
  } finally {
    modalLoading.value = false;
  }
}

function getRoleRowKey(row: Api.Role.RoleItem) {
  return row.role;
}

onMounted(() => {
  loadRoles();
  loadPermissionOptions();
  loadMenus();
});
</script>

<template>
  <div class="min-h-500px">
    <NCard title="角色管理" :bordered="false">
      <NDataTable :columns="columns" :data="roleList" :loading="loading" :row-key="getRoleRowKey" />
    </NCard>

    <NModal
      v-model:show="modalVisible"
      :title="currentRole ? `角色配置 - ${currentRole.label}` : '角色配置'"
      preset="card"
      class="w-980px"
    >
      <NGrid :cols="2" :x-gap="16">
        <NGi>
          <NCard size="small" title="权限">
            <div class="max-h-420px overflow-y-auto pr-4px">
              <NCheckboxGroup v-model:value="checkedPermissions">
                <NSpace vertical class="py-2">
                  <NCheckbox v-for="opt in permissionOptions" :key="opt.code" :value="opt.code">
                    {{ opt.label }}
                  </NCheckbox>
                </NSpace>
              </NCheckboxGroup>
            </div>
          </NCard>
        </NGi>

        <NGi>
          <NCard size="small" title="首页配置">
            <NSpace justify="space-between" align="center" class="mb-12px">
              <NText depth="3">仅可选择该角色有权限访问的菜单路由</NText>
              <NButton text type="warning" @click="selectedHomeRoute = null">清空首页</NButton>
            </NSpace>

            <NAlert type="info" :show-icon="false" class="mb-12px">
              当前首页：
              <strong>{{ selectedHomeRouteLabel }}</strong>
            </NAlert>

            <NTree
              v-if="roleAccessibleMenuTree.length > 0"
              key-field="key"
              block-line
              default-expand-all
              :data="roleAccessibleMenuTree"
              :selected-keys="selectedTreeKeys"
              selectable
              :render-label="renderTreeLabel"
              @update:selected-keys="handleTreeSelect"
            />
            <NEmpty v-else description="该角色暂无可访问菜单，请先分配权限" />
          </NCard>
        </NGi>
      </NGrid>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="modalVisible = false">取消</NButton>
          <NButton type="primary" :loading="modalLoading" @click="submitRoleConfig">保存</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped></style>
