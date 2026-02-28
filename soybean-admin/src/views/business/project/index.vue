<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import { NButton, NSpace, NTag } from 'naive-ui';
import { createProject, fetchProjectList, updateProject } from '@/service/api/project';

const loading = ref(false);
const tableData = ref<Api.Project.Item[]>([]);
const total = ref(0);
const pagination = reactive({
  page: 1,
  pageSize: 20
});
const searchName = ref('');
const searchEnabled = ref<string | null>(null);

const modalVisible = ref(false);
const modalLoading = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);
const formModel = reactive<{
  name: string;
  date: number | null;
  remark: string;
}>({
  name: '',
  date: null,
  remark: ''
});

const columns: NaiveUI.DataTableBaseColumn<Api.Project.Item>[] = [
  { title: '项目名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '项目ID', key: 'project_no', width: 140 },
  {
    title: '创建日期',
    key: 'date',
    width: 120,
    render: row => (row.date ? new Date(row.date).toLocaleDateString() : '-')
  },
  { title: '备注', key: 'remark', ellipsis: { tooltip: true }, render: row => row.remark || '-' },
  {
    title: '状态',
    key: 'enabled',
    width: 80,
    render: row =>
      h(
        NTag,
        { type: row.enabled ? 'success' : 'error', size: 'small' },
        { default: () => (row.enabled ? '启用' : '停用') }
      )
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    fixed: 'right',
    render: row =>
      h(NSpace, null, {
        default: () => [
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(row) },
            { default: () => '编辑' }
          ),
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: row.enabled ? 'warning' : 'primary',
              onClick: () => toggleEnabled(row)
            },
            { default: () => (row.enabled ? '停用' : '启用') }
          )
        ]
      })
  }
];

async function loadData() {
  loading.value = true;
  try {
    const { data, error } = await fetchProjectList({
      page: pagination.page,
      page_size: pagination.pageSize,
      name: searchName.value || undefined,
      enabled: getEnabledParam()
    });
    tableData.value = !error && Array.isArray(data?.items) ? data.items : [];
    total.value = !error && typeof data?.total === 'number' ? data.total : 0;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  isEdit.value = false;
  editId.value = null;
  formModel.name = '';
  formModel.date = null;
  formModel.remark = '';
  modalVisible.value = true;
}

function openEdit(row: Api.Project.Item) {
  isEdit.value = true;
  editId.value = row.id;
  formModel.name = row.name;
  formModel.date = row.date ? new Date(row.date).getTime() : null;
  formModel.remark = row.remark || '';
  modalVisible.value = true;
}

async function submitModal() {
  if (!formModel.name.trim()) {
    window.$message?.warning('请输入项目名称');
    return;
  }
  modalLoading.value = true;
  try {
    if (isEdit.value && editId.value !== null) {
      const { error } = await updateProject(editId.value, {
        name: formModel.name.trim(),
        date: formModel.date ? new Date(formModel.date).toISOString() : null,
        remark: formModel.remark.trim() || null,
        enabled: undefined
      });
      if (error) return;
      window.$message?.success('更新成功');
    } else {
      const { error } = await createProject({
        name: formModel.name.trim(),
        date: formModel.date ? new Date(formModel.date).toISOString() : null,
        remark: formModel.remark.trim() || null
      });
      if (error) return;
      window.$message?.success('创建成功');
    }
    modalVisible.value = false;
    await loadData();
  } finally {
    modalLoading.value = false;
  }
}

async function toggleEnabled(row: Api.Project.Item) {
  try {
    const { error } = await updateProject(row.id, { enabled: !row.enabled });
    if (error) return;
    window.$message?.success(row.enabled ? '已停用' : '已启用');
    await loadData();
  } catch {
    // error shown by request interceptor
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

function getProjectRowKey(row: Api.Project.Item) {
  return row.id;
}

function getEnabledParam(): boolean | undefined {
  if (searchEnabled.value === 'true') return true;
  if (searchEnabled.value === 'false') return false;
  return undefined;
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="min-h-500px">
    <NCard title="项目管理" :bordered="false">
      <template #header-extra>
        <NSpace>
          <NInput v-model:value="searchName" placeholder="项目名称" clearable class="w-160px" @keyup.enter="onSearch" />
          <NSelect
            v-model:value="searchEnabled"
            placeholder="状态"
            clearable
            :options="[
              { label: '启用', value: 'true' },
              { label: '停用', value: 'false' }
            ]"
            class="w-100px"
          />
          <NButton type="primary" @click="onSearch">查询</NButton>
          <NButton type="primary" @click="openCreate">新建项目</NButton>
        </NSpace>
      </template>

      <NDataTable :columns="columns" :data="tableData" :loading="loading" :row-key="getProjectRowKey" />

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

    <NModal v-model:show="modalVisible" :title="isEdit ? '编辑项目' : '新建项目'" preset="card" class="w-480px">
      <NForm :model="formModel" label-placement="left" label-width="80">
        <NFormItem label="项目名称" required>
          <NInput v-model:value="formModel.name" placeholder="请输入项目名称" />
        </NFormItem>
        <NFormItem label="日期">
          <NDatePicker v-model:value="formModel.date" type="date" clearable class="w-full" />
        </NFormItem>
        <NFormItem label="备注">
          <NInput v-model:value="formModel.remark" type="textarea" placeholder="备注" :rows="3" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="modalVisible = false">取消</NButton>
          <NButton type="primary" :loading="modalLoading" @click="submitModal">确定</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped></style>
