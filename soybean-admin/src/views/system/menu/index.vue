<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { NButton, NPopconfirm, NTag } from 'naive-ui';
import type { FormInst, SelectOption } from 'naive-ui';
import type { ElegantConstRoute } from '@elegant-router/types';
import mdiCollection from '@iconify/json/json/mdi.json';
import { router } from '@/router';
import { batchDeleteMenus, createMenu, deleteMenu, fetchMenuList, updateMenu } from '@/service/api/menu';
import { useRouteStore } from '@/store/modules/route';
import { useSvgIcon } from '@/hooks/common/icon';
import SvgIcon from '@/components/custom/svg-icon.vue';
import { $t } from '@/locales';
import { createStaticRoutes } from '@/router/routes';

defineOptions({
  name: 'SystemMenu'
});

type MenuType = Api.Menu.MenuType;
type MenuItem = Api.Menu.Item;
type OperateType = 'add' | 'addChild' | 'edit';

interface MenuFormModel {
  menu_type: MenuType;
  menu_name: string;
  icon: string;
  route_name: string;
  route_path: string;
  status: boolean;
  hide_in_menu: boolean;
  order: number;
}

const menuTypeLabelMap: Record<MenuType, string> = {
  1: 'Top Menu',
  2: 'Sub Menu',
  3: 'Page'
};

const menuTypeTagMap: Record<MenuType, NaiveUI.ThemeColor> = {
  1: 'info',
  2: 'default',
  3: 'primary'
};

const menuTypeOptions = [
  { label: 'Top Menu', value: 1 },
  { label: 'Sub Menu', value: 2 },
  { label: 'Page', value: 3 }
];

const MDI_ICON_LIMIT = 200;
const mdiIconKeys = Object.keys((mdiCollection as { icons: Record<string, unknown> }).icons || {}).sort();
const mdiIcons = mdiIconKeys.map(key => `mdi:${key}`);
const iconKeyword = ref('');
const formModel = reactive<MenuFormModel>(createDefaultFormModel(1));
const routeStore = useRouteStore();
const { SvgIconVNode } = useSvgIcon();

const mdiIconOptions = computed<SelectOption[]>(() => {
  const keyword = iconKeyword.value.trim().toLowerCase();

  const matched = keyword ? mdiIcons.filter(icon => icon.includes(keyword)) : mdiIcons;

  const selected = formModel.icon.trim();
  const withSelected = selected && !matched.includes(selected) ? [selected, ...matched] : matched;

  return withSelected.slice(0, MDI_ICON_LIMIT).map(icon => ({
    label: icon,
    value: icon
  }));
});

const tableData = ref<MenuItem[]>([]);
const loading = ref(false);
const checkedRowKeys = ref<Array<string | number>>([]);

const modalVisible = ref(false);
const modalLoading = ref(false);
const formRef = ref<FormInst | null>(null);
const operateType = ref<OperateType>('add');
const editingId = ref<number | null>(null);
const parentId = ref<number | null>(null);
const hasTriedAutoSync = ref(false);

const formRules: Record<'menu_name' | 'route_name' | 'route_path' | 'order', App.Global.FormRule[]> = {
  menu_name: [{ required: true, message: 'Please enter menu name', trigger: ['blur', 'input'] }],
  route_name: [{ required: true, message: 'Please enter route name', trigger: ['blur', 'input'] }],
  route_path: [
    { required: true, message: 'Please enter route path', trigger: ['blur', 'input'] },
    {
      validator: (_rule, value) => String(value || '').startsWith('/'),
      message: 'Route path must start with /',
      trigger: ['blur', 'input']
    }
  ],
  order: [{ type: 'number', required: true, message: 'Please enter order', trigger: ['blur', 'change'] }]
};

const modalTitle = computed(() => {
  if (operateType.value === 'edit') return 'Edit Menu';
  if (operateType.value === 'addChild') return 'Add Child Menu';
  return 'Add Top Menu';
});

const parentName = computed(() => {
  if (!parentId.value) return '-';
  return findById(tableData.value, parentId.value)?.menu_name || '-';
});

const columns: NaiveUI.TableColumn<MenuItem>[] = [
  {
    type: 'selection',
    align: 'center',
    width: 48
  },
  {
    key: 'index',
    title: 'ID',
    width: 70,
    align: 'center',
    render: (row: MenuItem) => row.id
  },
  {
    key: 'menu_type',
    title: 'Type',
    width: 100,
    align: 'center',
    render: (row: MenuItem) =>
      h(
        NTag,
        {
          type: menuTypeTagMap[row.menu_type],
          bordered: false
        },
        { default: () => menuTypeLabelMap[row.menu_type] }
      )
  },
  {
    key: 'menu_name',
    title: 'Menu Name',
    minWidth: 140,
    render: (row: MenuItem) => getMenuNameLabel(row)
  },
  {
    key: 'icon',
    title: 'Icon',
    width: 180,
    align: 'center',
    render: (row: MenuItem) =>
      row.icon
        ? h('div', { class: 'flex items-center justify-center gap-8px' }, [
            h(SvgIcon, { icon: row.icon, class: 'text-icon' }),
            h('span', row.icon)
          ])
        : '-'
  },
  {
    key: 'route_name',
    title: 'Route Name',
    minWidth: 140
  },
  {
    key: 'route_path',
    title: 'Route Path',
    minWidth: 180
  },
  {
    key: 'status',
    title: 'Enabled',
    width: 96,
    align: 'center',
    render: (row: MenuItem) =>
      h(
        NTag,
        { type: row.status ? 'success' : 'error', bordered: false },
        { default: () => (row.status ? 'Yes' : 'No') }
      )
  },
  {
    key: 'hide_in_menu',
    title: 'Hide in Menu',
    width: 110,
    align: 'center',
    render: (row: MenuItem) =>
      h(
        NTag,
        { type: row.hide_in_menu ? 'warning' : 'default', bordered: false },
        { default: () => (row.hide_in_menu ? 'Yes' : 'No') }
      )
  },
  {
    key: 'order',
    title: 'Order',
    width: 72,
    align: 'center'
  },
  {
    key: 'actions',
    title: 'Actions',
    width: 260,
    align: 'center',
    fixed: 'right',
    render: (row: MenuItem) => {
      const nodes: any[] = [];

      if (row.menu_type < 3) {
        nodes.push(
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              ghost: true,
              onClick: () => openAddChildModal(row)
            },
            { default: () => (row.menu_type === 1 ? 'Add Sub Menu' : 'Add Page') }
          )
        );
      }

      nodes.push(
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            ghost: true,
            onClick: () => openEditModal(row)
          },
          { default: () => 'Edit' }
        )
      );

      nodes.push(
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row.id) },
          {
            default: () => 'Delete this menu?',
            trigger: () =>
              h(
                NButton,
                {
                  size: 'small',
                  type: 'error',
                  ghost: true
                },
                { default: () => 'Delete' }
              )
          }
        )
      );

      return h('div', { class: 'flex justify-end gap-8px' }, nodes);
    }
  }
];

function createDefaultFormModel(menuType: MenuType): MenuFormModel {
  return {
    menu_type: menuType,
    menu_name: '',
    icon: '',
    route_name: '',
    route_path: '',
    status: true,
    hide_in_menu: false,
    order: 1
  };
}

function resetFormModel(model: MenuFormModel) {
  Object.assign(formModel, model);
}

function findById(data: MenuItem[], id: number): MenuItem | null {
  for (const item of data) {
    if (item.id === id) return item;
    if (item.children?.length) {
      const child = findById(item.children, id);
      if (child) return child;
    }
  }
  return null;
}

function normalizeCheckedIds(keys: Array<string | number>) {
  return keys
    .map(key => (typeof key === 'number' ? key : Number(key)))
    .filter((id): id is number => Number.isFinite(id));
}

function handleIconSearch(keyword: string) {
  iconKeyword.value = keyword;
}

function renderIconOption(option: SelectOption) {
  const icon = String(option.value || '');
  return h('div', { class: 'flex items-center gap-8px' }, [h(SvgIcon, { icon, class: 'text-icon' }), h('span', icon)]);
}

function toMenuRoutes(routes: ElegantConstRoute[]) {
  return routes.filter(route => !route.meta?.hideInMenu);
}

function sortRoutes(routes: ElegantConstRoute[]) {
  return [...routes].sort((a, b) => {
    const orderA = Number(a.meta?.order ?? Number.MAX_SAFE_INTEGER);
    const orderB = Number(b.meta?.order ?? Number.MAX_SAFE_INTEGER);
    if (orderA !== orderB) return orderA - orderB;
    return String(a.name).localeCompare(String(b.name));
  });
}

function getRouteTitle(route: ElegantConstRoute) {
  const i18nKey = route.meta?.i18nKey;
  if (typeof i18nKey === 'string' && i18nKey.trim()) {
    const translated = $t(i18nKey as App.I18n.I18nKey);
    if (translated && translated !== i18nKey) return translated.trim();
  }

  const title = route.meta?.title;
  if (typeof title === 'string' && title.trim()) return title.trim();
  return String(route.name);
}

function getMenuNameLabel(menu: MenuItem) {
  const i18nKey = `route.${menu.route_name}` as App.I18n.I18nKey;
  const translated = $t(i18nKey);

  if (translated && translated !== i18nKey) {
    return translated;
  }

  return menu.menu_name;
}

function toRuntimeMenu(menu: MenuItem): App.Global.Menu | null {
  if (!menu.status || menu.hide_in_menu) {
    return null;
  }

  const children = (menu.children || []).map(toRuntimeMenu).filter((item): item is App.Global.Menu => Boolean(item));
  const hasRoute = router.hasRoute(menu.route_name);

  if (!hasRoute && children.length === 0) {
    return null;
  }

  const i18nKey = `route.${menu.route_name}` as App.I18n.I18nKey;
  const translated = $t(i18nKey);
  const hasTranslated = translated && translated !== i18nKey;

  const runtimeMenu: App.Global.Menu = {
    key: menu.route_name,
    label: hasTranslated ? translated : menu.menu_name,
    i18nKey: hasTranslated ? i18nKey : null,
    routeKey: menu.route_name as App.Global.RouteKey,
    routePath: menu.route_path as App.Global.RoutePath,
    icon: SvgIconVNode({ icon: menu.icon || import.meta.env.VITE_MENU_ICON, fontSize: 20 })
  };

  if (children.length) {
    runtimeMenu.children = children;
  }

  return runtimeMenu;
}

function syncRuntimeMenus(data: MenuItem[]) {
  routeStore.menus = data.map(toRuntimeMenu).filter((item): item is App.Global.Menu => Boolean(item));
}

async function createMenuByRoute(route: ElegantConstRoute, parent: number | null, level: MenuType) {
  const menuName = getRouteTitle(route);
  const routeName = String(route.name);
  const routePath = String(route.path || '/');

  const { data, error } = await createMenu({
    menu_type: level,
    menu_name: menuName,
    icon: typeof route.meta?.icon === 'string' ? route.meta.icon : null,
    route_name: routeName,
    route_path: routePath,
    status: true,
    hide_in_menu: Boolean(route.meta?.hideInMenu),
    order: Number(route.meta?.order ?? 1),
    parent_id: parent
  });

  if (error || !data || level >= 3) return;

  const children = sortRoutes(toMenuRoutes((route.children || []) as ElegantConstRoute[]));
  if (!children.length) return;

  const nextLevel = (level + 1) as MenuType;
  await children.reduce<Promise<void>>(async (prev, child) => {
    await prev;
    await createMenuByRoute(child, data.id, nextLevel > 3 ? 3 : nextLevel);
  }, Promise.resolve());
}

async function autoSyncMenusFromRoutes() {
  const { authRoutes } = createStaticRoutes();
  const roots = sortRoutes(toMenuRoutes(authRoutes as ElegantConstRoute[]));
  if (!roots.length) return false;

  await roots.reduce<Promise<void>>(async (prev, root) => {
    await prev;
    await createMenuByRoute(root, null, 1);
  }, Promise.resolve());

  return true;
}

async function loadData() {
  loading.value = true;
  try {
    const { data, error } = await fetchMenuList();

    if (!error && Array.isArray(data) && data.length > 0) {
      tableData.value = data;
      syncRuntimeMenus(data);
      return;
    }

    if (!error && Array.isArray(data) && data.length === 0 && !hasTriedAutoSync.value) {
      hasTriedAutoSync.value = true;
      window.$message?.info('Menu is empty, syncing existing system routes...');
      await autoSyncMenusFromRoutes();

      const { data: syncedData, error: syncError } = await fetchMenuList();
      tableData.value = !syncError && Array.isArray(syncedData) ? syncedData : [];
      syncRuntimeMenus(tableData.value);
      if (tableData.value.length) {
        window.$message?.success('Menu synced from routes');
      }
      return;
    }

    tableData.value = [];
    syncRuntimeMenus([]);
  } catch {
    tableData.value = [];
    syncRuntimeMenus([]);
  } finally {
    loading.value = false;
  }
}

function openAddModal() {
  operateType.value = 'add';
  editingId.value = null;
  parentId.value = null;
  iconKeyword.value = '';
  resetFormModel(createDefaultFormModel(1));
  modalVisible.value = true;
}

function openAddChildModal(parent: MenuItem) {
  if (parent.menu_type >= 3) return;

  const nextType = (parent.menu_type + 1) as MenuType;
  operateType.value = 'addChild';
  editingId.value = null;
  parentId.value = parent.id;
  iconKeyword.value = '';
  resetFormModel({
    ...createDefaultFormModel(nextType),
    route_path: parent.route_path === '/' ? '/new-page' : `${parent.route_path}/new-page`
  });
  modalVisible.value = true;
}

function openEditModal(row: MenuItem) {
  operateType.value = 'edit';
  editingId.value = row.id;
  parentId.value = row.parent_id;
  iconKeyword.value = '';
  resetFormModel({
    menu_type: row.menu_type,
    menu_name: row.menu_name,
    icon: row.icon || '',
    route_name: row.route_name,
    route_path: row.route_path,
    status: row.status,
    hide_in_menu: row.hide_in_menu,
    order: row.order
  });
  modalVisible.value = true;
}

async function submitForm() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  modalLoading.value = true;
  try {
    if (operateType.value === 'edit' && editingId.value !== null) {
      const { error } = await updateMenu(editingId.value, {
        menu_name: formModel.menu_name.trim(),
        icon: formModel.icon.trim() || null,
        route_name: formModel.route_name.trim(),
        route_path: formModel.route_path.trim(),
        status: formModel.status,
        hide_in_menu: formModel.hide_in_menu,
        order: formModel.order
      });

      if (error) return;

      window.$message?.success('Menu updated');
      modalVisible.value = false;
      await loadData();
      return;
    }

    const { error } = await createMenu({
      menu_type: formModel.menu_type,
      menu_name: formModel.menu_name.trim(),
      icon: formModel.icon.trim() || null,
      route_name: formModel.route_name.trim(),
      route_path: formModel.route_path.trim(),
      status: formModel.status,
      hide_in_menu: formModel.hide_in_menu,
      order: formModel.order,
      parent_id: operateType.value === 'addChild' ? parentId.value : null
    });

    if (error) return;

    window.$message?.success('Menu created');
    modalVisible.value = false;
    await loadData();
  } finally {
    modalLoading.value = false;
  }
}

async function handleDelete(id: number) {
  const { error } = await deleteMenu(id);
  if (error) return;

  checkedRowKeys.value = checkedRowKeys.value.filter(key => key !== id);
  window.$message?.success('Menu deleted');
  await loadData();
}

async function handleBatchDelete() {
  const ids = normalizeCheckedIds(checkedRowKeys.value);
  if (!ids.length) return;

  const { error } = await batchDeleteMenus(ids);
  if (error) return;

  checkedRowKeys.value = [];
  window.$message?.success(`Deleted ${ids.length} menu items`);
  await loadData();
}

async function handleRefresh() {
  await loadData();
  window.$message?.success('Menu refreshed');
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="min-h-500px">
    <NCard title="Menu List" :bordered="false">
      <template #header-extra>
        <NSpace align="center">
          <NButton type="primary" ghost @click="openAddModal">+ Add</NButton>
          <NPopconfirm @positive-click="handleBatchDelete">
            <template #trigger>
              <NButton type="error" ghost :disabled="checkedRowKeys.length === 0">Batch Delete</NButton>
            </template>
            Delete selected menu items?
          </NPopconfirm>
          <NButton @click="handleRefresh">Refresh</NButton>
        </NSpace>
      </template>

      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :row-key="row => row.id"
        :single-line="false"
      />
    </NCard>

    <NModal v-model:show="modalVisible" :title="modalTitle" preset="card" class="w-560px">
      <NForm ref="formRef" :model="formModel" :rules="formRules" label-placement="left" label-width="90">
        <NAlert
          v-if="operateType === 'addChild'"
          class="mb-16px"
          type="info"
          :show-icon="false"
          :title="`Parent: ${parentName}`"
        />

        <NFormItem label="Menu Type">
          <NSelect v-model:value="formModel.menu_type" :options="menuTypeOptions" disabled />
        </NFormItem>

        <NFormItem label="Menu Name" path="menu_name">
          <NInput v-model:value="formModel.menu_name" placeholder="Enter menu name" maxlength="64" />
        </NFormItem>

        <NFormItem label="Icon">
          <NSelect
            v-model:value="formModel.icon"
            clearable
            filterable
            placeholder="Select MDI icon"
            :options="mdiIconOptions"
            :render-label="renderIconOption"
            @search="handleIconSearch"
          />
        </NFormItem>

        <NFormItem label="Route Name" path="route_name">
          <NInput v-model:value="formModel.route_name" placeholder="Enter route name" maxlength="64" />
        </NFormItem>

        <NFormItem label="Route Path" path="route_path">
          <NInput v-model:value="formModel.route_path" placeholder="Enter route path starting with /" maxlength="128" />
        </NFormItem>

        <NFormItem label="Enabled">
          <NSwitch v-model:value="formModel.status" />
        </NFormItem>

        <NFormItem label="Hide in Menu">
          <NSwitch v-model:value="formModel.hide_in_menu" />
        </NFormItem>

        <NFormItem label="Order" path="order">
          <NInputNumber v-model:value="formModel.order" :min="1" class="w-full" />
        </NFormItem>
      </NForm>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="modalVisible = false">Cancel</NButton>
          <NButton type="primary" :loading="modalLoading" @click="submitForm">Save</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped></style>
