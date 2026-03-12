<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import { NButton, NDataTable, NDrawer, NDrawerContent, NSpace, NSpin, NTag } from 'naive-ui';
import type { DataTableBaseColumn } from 'naive-ui';
import { fetchImportLogDetail, fetchImportLogs } from '@/service/api/order';
import { formatUtc8DateTime } from '@/utils/datetime';

interface Props {
  show?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  show: false
});

const emit = defineEmits<{
  (e: 'update:show', show: boolean): void;
}>();

const loading = ref(false);
const tableData = ref<Api.Order.ImportLog[]>([]);
const total = ref(0);
const pagination = reactive({
  page: 1,
  pageSize: 20
});

const detailLoading = ref(false);
const detailVisible = ref(false);
const currentLog = ref<Api.Order.ImportLog | null>(null);

const columns: DataTableBaseColumn<Api.Order.ImportLog>[] = [
  {
    title: 'ID',
    key: 'id',
    width: 60
  },
  {
    title: '文件名',
    key: 'filename',
    width: 200,
    ellipsis: { tooltip: true }
  },
  {
    title: '项目',
    key: 'project_name',
    width: 120
  },
  {
    title: '总行数',
    key: 'total_rows',
    width: 80
  },
  {
    title: '成功',
    key: 'success_rows',
    width: 70,
    render: row => h(NTag, { type: 'success', size: 'small' }, { default: () => row.success_rows })
  },
  {
    title: '失败',
    key: 'fail_rows',
    width: 70,
    render: row =>
      row.fail_rows > 0
        ? h(NTag, { type: 'error', size: 'small' }, { default: () => row.fail_rows })
        : h('span', null, '0')
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: row => {
      const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'info'; label: string }> = {
        pending: { type: 'info', label: '待处理' },
        processing: { type: 'warning', label: '处理中' },
        success: { type: 'success', label: '成功' },
        completed: { type: 'warning', label: '部分成功' },
        failed: { type: 'error', label: '失败' }
      };
      const config = statusMap[row.status] || { type: 'info', label: row.status };
      return h(NTag, { type: config.type, size: 'small' }, { default: () => config.label });
    }
  },
  {
    title: '导入人',
    key: 'import_user_name',
    width: 100
  },
  {
    title: '导入时间',
    key: 'created_at',
    width: 160,
    render: row => formatUtc8DateTime(row.created_at)
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: row =>
      row.fail_rows > 0
        ? h(NButton, { size: 'small', type: 'primary', onClick: () => viewDetail(row) }, { default: () => '查看详情' })
        : h('span', { style: { color: '#999' } }, '-')
  }
];

async function loadData() {
  loading.value = true;
  try {
    const res = await fetchImportLogs({
      page: pagination.page,
      page_size: pagination.pageSize
    });
    tableData.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function viewDetail(log: Api.Order.ImportLog) {
  detailLoading.value = true;
  detailVisible.value = true;
  try {
    const res = await fetchImportLogDetail(log.id);
    currentLog.value = res.data;
  } finally {
    detailLoading.value = false;
  }
}

function handleClose() {
  emit('update:show', false);
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

defineExpose({
  loadData
});

onMounted(() => {
  loadData();
});
</script>

<template>
  <NDrawer
    :show="props.show"
    :width="500"
    placement="right"
    @update:show="emit('update:show', $event)"
    @close="handleClose"
  >
    <NDrawerContent title="导入日志" closable>
      <div class="import-log-content">
        <NSpin :show="loading">
          <NDataTable
            :loading="loading"
            :columns="columns"
            :data="tableData"
            :row-key="row => row.id"
            :pagination="{
              page: pagination.page,
              pageSize: pagination.pageSize,
              pageSizes: [10, 20, 50],
              showSizePicker: true,
              showQuickJumper: true,
              'onUpdate:page': handlePageChange,
              'onUpdate:pageSize': handlePageSizeChange
            }"
            :bordered="false"
            striped
            size="small"
          />
        </NSpin>
      </div>

      <!-- 详情抽屉 -->
      <NDrawer :show="detailVisible" :width="600" placement="right" @update:show="detailVisible = $event">
        <NDrawerContent title="导入失败详情" closable>
          <NSpin :show="detailLoading">
            <template v-if="currentLog">
              <div class="log-detail">
                <div class="detail-header">
                  <div class="detail-item">
                    <span class="label">文件名：</span>
                    <span class="value">{{ currentLog.filename }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">导入时间：</span>
                    <span class="value">{{ formatUtc8DateTime(currentLog.created_at) }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="label">导入结果：</span>
                    <NSpace>
                      <NTag type="success">成功 {{ currentLog.success_rows }}</NTag>
                      <NTag type="error">失败 {{ currentLog.fail_rows }}</NTag>
                    </NSpace>
                  </div>
                  <div v-if="currentLog.error_message" class="detail-item">
                    <span class="label">错误信息：</span>
                    <span class="value error">{{ currentLog.error_message }}</span>
                  </div>
                </div>

                <div v-if="currentLog.fail_details" class="fail-details">
                  <h4>失败详情</h4>
                  <NDataTable
                    :columns="[
                      { title: '行号', key: 'row', width: 60 },
                      { title: '错误原因', key: 'error', ellipsis: { tooltip: true } },
                      {
                        title: '数据',
                        key: 'data',
                        width: 200,
                        ellipsis: { tooltip: true },
                        render: (row: any) => JSON.stringify(row.data).substring(0, 50) + '...'
                      }
                    ]"
                    :data="currentLog.fail_details as any"
                    :bordered="false"
                    size="small"
                    :max-height="400"
                  />
                </div>
              </div>
            </template>
          </NSpin>
        </NDrawerContent>
      </NDrawer>
    </NDrawerContent>
  </NDrawer>
</template>

<style scoped>
.import-log-content {
  min-height: 400px;
}

.detail-header {
  margin-bottom: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.detail-item {
  margin-bottom: 12px;
}

.detail-item .label {
  font-weight: 500;
  color: #666;
  margin-right: 8px;
}

.detail-item .value.error {
  color: #f56c6c;
}

.fail-details h4 {
  margin-bottom: 12px;
  color: #333;
}
</style>
