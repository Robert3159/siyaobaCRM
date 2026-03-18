<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NCard, NDataTable, NDatePicker, NEmpty, NPagination, NSpace, NSpin } from 'naive-ui';
import { type StatisticsPreset, formatCurrency, formatNumber, getTableColumns } from '@/constants/statistics';

interface Props {
  preset: StatisticsPreset;
  columns?: Array<{ key: string; title: string; sorter?: boolean }>;
  data: Api.Statistics.QgsDailyStatisticsItem[] | Api.Statistics.HgsDailyStatisticsItem[];
  loading?: boolean;
  total: number;
  page: number;
  pageSize: number;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  columns: () => []
});

const emit = defineEmits<{
  (e: 'pageChange', page: number): void;
  (e: 'pageSizeChange', pageSize: number): void;
  (e: 'sortChange', sortField: string, sortOrder: 'asc' | 'desc'): void;
  (e: 'filterChange', startDate?: number, endDate?: number): void;
  (e: 'export'): void;
  (e: 'update:page', page: number): void;
  (e: 'update:pageSize', pageSize: number): void;
}>();

// 获取列配置 - 转换为可变数组
const tableColumns = computed(() => {
  const cols = props.columns || getTableColumns(props.preset);
  return cols.map(col => ({ ...col }));
});

// 获取汇总数据
const summary = computed(() => {
  if (!props.data.length) return null;

  if (props.preset === 'qgs') {
    const data = props.data as Api.Statistics.QgsDailyStatisticsItem[];
    return {
      total_new_registrations: data.reduce((sum, item) => sum + item.new_registrations, 0),
      total_paying_users: data.reduce((sum, item) => sum + item.paying_users, 0),
      total_amount: data.reduce((sum, item) => sum + item.total_amount, 0)
    };
  }
  const data = props.data as Api.Statistics.HgsDailyStatisticsItem[];
  return {
    total_connected_users: data.reduce((sum, item) => sum + item.connected_users, 0),
    total_new_paying_users: data.reduce((sum, item) => sum + item.new_paying_users, 0),
    total_amount: data.reduce((sum, item) => sum + item.total_amount, 0)
  };
});

// 处理分页变化
function handlePageChange(page: number) {
  emit('update:page', page);
  emit('pageChange', page);
}

function handlePageSizeChange(pageSize: number) {
  emit('update:pageSize', pageSize);
  emit('pageSizeChange', pageSize);
}

// 处理排序变化
function handleSorterChange(sorter: { columnKey: string; order: 'ascend' | 'descend' } | null) {
  if (!sorter) {
    emit('sortChange', 'date', 'desc');
    return;
  }
  const sortOrder = sorter.order === 'ascend' ? 'asc' : 'desc';
  emit('sortChange', sorter.columnKey, sortOrder);
}

// 日期筛选
const dateRange = defineModel<[number, number] | null>('dateRange', { default: null });

function handleDateRangeChange(values: [number, number] | null) {
  if (values && values[0] && values[1]) {
    emit('filterChange', values[0], values[1]);
    return;
  }
  emit('filterChange');
}

// 导出功能
function handleExport() {
  emit('export');
}
</script>

<template>
  <NCard title="数据明细" :bordered="false" class="statistics-table-card">
    <!-- 筛选和操作栏 -->
    <NSpace justify="space-between" align="center" class="table-toolbar">
      <NSpace align="center">
        <NDatePicker v-model:value="dateRange" type="daterange" clearable @update:value="handleDateRangeChange" />
      </NSpace>
      <NButton type="primary" @click="handleExport">导出数据</NButton>
    </NSpace>

    <!-- 表格 -->
    <NSpin :show="loading">
      <NEmpty v-if="!data.length && !loading" description="暂无数据" />
      <template v-else>
        <NDataTable
          :columns="tableColumns"
          :data="data"
          :loading="loading"
          :pagination="false"
          :row-key="(row: any) => row.date"
          @update:sorter="handleSorterChange"
        />

        <!-- 汇总行 -->
        <div v-if="summary" class="table-summary">
          <span class="summary-label">合计：</span>
          <template v-if="preset === 'qgs'">
            <span class="summary-item">新增注册: {{ formatNumber(summary.total_new_registrations || 0) }}</span>
            <span class="summary-item">付费人数: {{ formatNumber(summary.total_paying_users || 0) }}</span>
            <span class="summary-item">付费金额: {{ formatCurrency(summary.total_amount || 0) }}</span>
          </template>
          <template v-else>
            <span class="summary-item">对接数量: {{ formatNumber(summary.total_connected_users || 0) }}</span>
            <span class="summary-item">新增付费: {{ formatNumber(summary.total_new_paying_users || 0) }}</span>
            <span class="summary-item">付费金额: {{ formatCurrency(summary.total_amount || 0) }}</span>
          </template>
        </div>

        <!-- 分页 -->
        <div class="table-pagination">
          <NPagination
            :page="page"
            :page-size="pageSize"
            :item-count="total"
            :page-sizes="[10, 20, 50, 100]"
            show-size-picker
            @update:page="handlePageChange"
            @update:page-size="handlePageSizeChange"
          />
        </div>
      </template>
    </NSpin>
  </NCard>
</template>

<style scoped>
.statistics-table-card {
  width: 100%;
}

.table-toolbar {
  margin-bottom: 16px;
}

.table-summary {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-top: 16px;
  font-weight: 500;
}

.summary-label {
  font-weight: 600;
  color: #303133;
}

.summary-item {
  color: #606266;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
