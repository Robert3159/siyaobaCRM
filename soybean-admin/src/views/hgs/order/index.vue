<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { NButton, NDataTable, NDatePicker, NInput, NSelect, NSpace, NTag } from 'naive-ui';
import type { DataTableBaseColumn } from 'naive-ui';
import { fetchOrderList } from '@/service/api/order';
import { fetchProjectList } from '@/service/api/project';
import { fetchUserList } from '@/service/api/user';
import { useAuthStore } from '@/store/modules/auth';
import { formatUtc8DateTime } from '@/utils/datetime';
import OrderImportModal from './components/OrderImportModal.vue';
import ImportLogDrawer from './components/ImportLogDrawer.vue';

const authStore = useAuthStore();

// 权限检查：仅 ADMIN 或 SUB_ADMIN 可见导入按钮
const canImport = computed(() => {
  const roles = authStore.userInfo?.roles;
  return roles?.includes('ADMIN') || roles?.includes('SUB_ADMIN');
});

// 弹窗控制
const importModalVisible = ref(false);
const importLogDrawerVisible = ref(false);

const loading = ref(false);
const tableData = ref<Api.Order.Item[]>([]);
const total = ref(0);
const pagination = reactive({
  page: 1,
  pageSize: 50
});

// 筛选条件
const searchParams = reactive({
  project_id: null as number | null,
  player_id: '',
  qgs__author: null as number | null,
  hgs_maintainer: null as number | null,
  start_time: null as number | null,
  end_time: null as number | null,
  sort_field: 'created_at' as 'order_time' | 'amount' | 'created_at',
  sort_order: 'desc' as 'asc' | 'desc'
});

// 修复: 添加计算属性用于日期范围双向绑定
const dateRange = computed<[number, number] | null>({
  get: () => {
    if (searchParams.start_time && searchParams.end_time) {
      return [searchParams.start_time, searchParams.end_time] as [number, number];
    }
    return null;
  },
  set: (val: [number, number] | null) => {
    if (val) {
      searchParams.start_time = val[0];
      searchParams.end_time = val[1];
    } else {
      searchParams.start_time = null;
      searchParams.end_time = null;
    }
  }
});

// 选项数据
const projectOptions = ref<{ label: string; value: number }[]>([]);
const qgsOptions = ref<{ label: string; value: number }[]>([]); // 前端GS选项
const hgsOptions = ref<{ label: string; value: number }[]>([]); // 后端GS选项

const columns: DataTableBaseColumn<Api.Order.Item>[] = [
  {
    title: 'ID',
    key: 'id',
    width: 70
  },
  {
    title: '项目',
    key: 'project_name',
    width: 120,
    ellipsis: { tooltip: true }
  },
  {
    title: '订单号',
    key: 'order_no',
    width: 180,
    ellipsis: { tooltip: true }
  },
  {
    title: '玩家ID',
    key: 'player_id',
    width: 150,
    ellipsis: { tooltip: true }
  },
  {
    title: '玩家名字',
    key: 'player_name',
    width: 120,
    ellipsis: { tooltip: true }
  },
  {
    title: '区服',
    key: 'server',
    width: 100
  },
  {
    title: '充值金额',
    key: 'amount',
    width: 100,
    sorter: (a, b) => a.amount - b.amount
  },
  {
    title: '充值时间',
    key: 'order_time',
    width: 160,
    sorter: (a, b) => {
      const timeA = a.order_time ? new Date(a.order_time).getTime() : 0;
      const timeB = b.order_time ? new Date(b.order_time).getTime() : 0;
      return timeA - timeB;
    },
    render: (row: Api.Order.Item) => (row.order_time ? formatUtc8DateTime(row.order_time) : '-')
  },
  {
    title: '前端GS',
    key: 'qgs__author_name',
    width: 100
  },
  {
    title: '后端GS',
    key: 'hgs_maintainer_name',
    width: 100
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 160,
    sorter: (a, b) => {
      const timeA = new Date(a.created_at).getTime();
      const timeB = new Date(b.created_at).getTime();
      return timeA - timeB;
    },
    render: row => formatUtc8DateTime(row.created_at)
  },
  {
    title: '失败原因',
    key: 'fail_reason',
    width: 150,
    ellipsis: { tooltip: true },
    render: row =>
      row.fail_reason ? h(NTag, { type: 'error', size: 'small' }, { default: () => row.fail_reason }) : '-'
  }
];

async function loadData() {
  loading.value = true;
  try {
    const params: Api.Order.FetchParams = {
      page: pagination.page,
      page_size: pagination.pageSize,
      sort_field: searchParams.sort_field,
      sort_order: searchParams.sort_order
    };

    if (searchParams.project_id) {
      params.project_id = searchParams.project_id;
    }
    if (searchParams.player_id) {
      params.player_id = searchParams.player_id;
    }
    if (searchParams.qgs__author) {
      params.qgs__author = searchParams.qgs__author;
    }
    if (searchParams.hgs_maintainer) {
      params.hgs_maintainer = searchParams.hgs_maintainer;
    }
    if (searchParams.start_time) {
      params.start_time = new Date(searchParams.start_time).toISOString();
    }
    if (searchParams.end_time) {
      params.end_time = new Date(searchParams.end_time).toISOString();
    }

    const res = await fetchOrderList(params);
    tableData.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function loadProjectOptions() {
  const { data, error } = await fetchProjectList({ page: 1, page_size: 100 });
  projectOptions.value =
    !error && Array.isArray(data?.items) ? data.items.map(p => ({ label: p.name, value: p.id })) : [];
}

async function loadGSOptions() {
  // 获取所有用户，分别过滤前端GS和后端GS
  const { data, error } = await fetchUserList({ page: 1, page_size: 100 });
  const items = !error && Array.isArray(data?.items) ? data.items : [];

  // 前端GS：显示所有前端相关角色，使用alias作为显示名称
  const qgsRoles = ['ADMIN', 'SUB_ADMIN', 'QGS_DIRECTOR', 'QGS_LEADER', 'QGS_MEMBER'];
  qgsOptions.value = items.filter(u => qgsRoles.includes(u.role)).map(u => ({ label: u.alias || u.user, value: u.id }));

  // 后端GS：显示所有后端相关角色，使用alias作为显示名称
  const hgsRoles = ['ADMIN', 'SUB_ADMIN', 'HGS_DIRECTOR', 'HGS_LEADER', 'HGS_MEMBER'];
  hgsOptions.value = items.filter(u => hgsRoles.includes(u.role)).map(u => ({ label: u.alias || u.user, value: u.id }));
}

function handleSearch() {
  pagination.page = 1;
  loadData();
}

function handleReset() {
  searchParams.project_id = null;
  searchParams.player_id = '';
  searchParams.qgs__author = null;
  searchParams.hgs_maintainer = null;
  searchParams.start_time = null;
  searchParams.end_time = null;
  pagination.page = 1;
  loadData();
}

function handlePageChange(page: number) {
  pagination.page = page;
  loadData();
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize;
  pagination.page = 1;
  loadData();
}

function handleImportSuccess() {
  // 导入成功后刷新列表
  loadData();
}

onMounted(() => {
  loadData();
  loadProjectOptions();
  loadGSOptions();
});
</script>

<template>
  <div class="order-list-container">
    <NCard title="订单列表" :bordered="false">
      <!-- 工具栏 -->
      <div class="toolbar">
        <NSpace>
          <NButton v-if="canImport" type="primary" @click="importModalVisible = true">导入订单</NButton>
          <NButton @click="importLogDrawerVisible = true">导入日志</NButton>
        </NSpace>
      </div>

      <!-- 筛选条件 -->
      <div class="filter-section">
        <NSpace align="center" :size="16">
          <div class="filter-item">
            <span class="filter-label">项目：</span>
            <NSelect
              v-model:value="searchParams.project_id"
              :options="projectOptions"
              placeholder="请选择项目"
              clearable
              class="w-180px"
              @update:value="handleSearch"
            />
          </div>
          <div class="filter-item">
            <span class="filter-label">玩家ID：</span>
            <NInput
              v-model:value="searchParams.player_id"
              placeholder="请输入玩家ID"
              clearable
              class="w-150px"
              @keyup.enter="handleSearch"
            />
          </div>
          <div class="filter-item">
            <span class="filter-label">前端GS：</span>
            <NSelect
              v-model:value="searchParams.qgs__author"
              :options="qgsOptions"
              placeholder="请选择"
              clearable
              class="w-120px"
              @update:value="handleSearch"
            />
          </div>
          <div class="filter-item">
            <span class="filter-label">后端GS：</span>
            <NSelect
              v-model:value="searchParams.hgs_maintainer"
              :options="hgsOptions"
              placeholder="请选择"
              clearable
              class="w-120px"
              @update:value="handleSearch"
            />
          </div>
          <div class="filter-item">
            <span class="filter-label">时间范围：</span>
            <NDatePicker
              v-model:value="dateRange"
              type="daterange"
              clearable
              class="w-280px"
              @update:value="handleSearch"
            />
          </div>
          <NButton type="primary" @click="handleSearch">搜索</NButton>
          <NButton @click="handleReset">重置</NButton>
        </NSpace>
      </div>

      <!-- 数据表格 -->
      <NDataTable
        :loading="loading"
        :columns="columns"
        :data="tableData"
        :row-key="row => row.id"
        :pagination="{
          page: pagination.page,
          pageSize: pagination.pageSize,
          pageSizes: [20, 50, 100],
          showSizePicker: true,
          showQuickJumper: true,
          'onUpdate:page': handlePageChange,
          'onUpdate:pageSize': handlePageSizeChange
        }"
        :scroll-x="1400"
        :bordered="false"
        striped
      />
    </NCard>

    <!-- 导入弹窗 -->
    <OrderImportModal v-model:show="importModalVisible" @success="handleImportSuccess" />
    <!-- 导入日志抽屉 -->
    <ImportLogDrawer v-model:show="importLogDrawerVisible" />
  </div>
</template>

<style scoped>
.order-list-container {
  padding: 16px;
}

.toolbar {
  margin-bottom: 16px;
}

.filter-section {
  margin-bottom: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.filter-item {
  display: flex;
  align-items: center;
}

.filter-label {
  white-space: nowrap;
  font-size: 14px;
  color: #666;
}

/* 替换内联样式 */
.w-180px {
  width: 180px;
}

.w-150px {
  width: 150px;
}

.w-120px {
  width: 120px;
}

.w-280px {
  width: 280px;
}
</style>
