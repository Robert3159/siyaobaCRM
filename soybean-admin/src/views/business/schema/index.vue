<script setup lang="ts">
import { h, onMounted, reactive, ref, watch } from 'vue';
import { NButton, NSpace, NTag } from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { createSchema, fetchSchema, fetchSchemaList, updateSchema } from '@/service/api/schema';

type SchemaFieldOptionItem = {
  label: string;
  color?: string;
};

type SchemaFieldFormItem = Api.Schema.FormFieldDef & {
  optionItems: SchemaFieldOptionItem[];
};

const loading = ref(false);
const tableData = ref<Api.Schema.Item[]>([]);
const total = ref(0);
const pagination = reactive({ page: 1, pageSize: 20 });
const searchName = ref('');
const searchEnabled = ref<string | null>(null);

const modalVisible = ref(false);
const modalLoading = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);
const pageOptions = [
  { label: 'qgs/list', value: 'qgs/list' },
  { label: 'hgs/list', value: 'hgs/list' },
  { label: 'qgs/submit', value: 'qgs/submit' }
];
const roleOptions = [
  { label: '超级管理员', value: 'ADMIN' },
  { label: '子管理员', value: 'SUB_ADMIN' },
  { label: '前端主管', value: 'QGS_DIRECTOR' },
  { label: '前端组长', value: 'QGS_LEADER' },
  { label: '前端成员', value: 'QGS_MEMBER' },
  { label: '后端主管', value: 'HGS_DIRECTOR' },
  { label: '后端组长', value: 'HGS_LEADER' },
  { label: '后端成员', value: 'HGS_MEMBER' }
];
const roleValueSet = new Set(roleOptions.map(option => option.value));
const formModel = reactive<{
  name: string;
  code: string;
  enabled: boolean;
  fields: SchemaFieldFormItem[];
}>({
  name: '',
  code: '',
  enabled: true,
  fields: []
});

const fieldTypeOptions = [
  { label: '单行文本', value: 'single_line_text' },
  { label: '多行文本', value: 'multi_line_text' },
  { label: '单选框', value: 'radio' },
  { label: '多选框', value: 'checkbox' },
  { label: '下拉列表', value: 'select' },
  { label: '下拉多选', value: 'select_multiple' },
  { label: '数字', value: 'number' },
  { label: '日期时间', value: 'datetime' },
  { label: '上传附件', value: 'upload_attachment' },
  { label: '上传图片', value: 'upload_image' }
];

const optionTypeSet = new Set(['radio', 'checkbox', 'select', 'select_multiple']);
const PLAYER_SCHEMA_CODE = 'player_form';
const playerBuiltInFieldTemplates: Array<{
  key: string;
  label: string;
  type: Api.Schema.FormFieldType;
  visible_pages: string[];
}> = [
  { key: 'project_id', label: '项目', type: 'project', visible_pages: ['qgs/list', 'hgs/list', 'qgs/submit'] },
  { key: 'created_at', label: '提交时间', type: 'datetime', visible_pages: ['qgs/list', 'hgs/list'] },
  { key: 'actions', label: '操作', type: 'single_line_text', visible_pages: ['qgs/list', 'hgs/list'] },
  {
    key: 'qgs_author',
    label: '前端GS',
    type: 'single_line_text',
    visible_pages: ['qgs/list', 'hgs/list', 'qgs/submit']
  },
  {
    key: 'hgs_maintainer',
    label: '后端GS',
    type: 'single_line_text',
    visible_pages: ['qgs/list', 'hgs/list', 'qgs/submit']
  }
];
const playerBuiltInTypeMap = new Map(
  playerBuiltInFieldTemplates.map(field => [field.key.trim().toLowerCase(), field.type] as const)
);
const optionColorSwatches = [
  '#000000',
  '#7f7f7f',
  '#880015',
  '#ed1c24',
  '#ff7f27',
  '#fff200',
  '#22b14c',
  '#00a2e8',
  '#3f48cc',
  '#a349a4',
  '#ffffff',
  '#c3c3c3',
  '#b97a57',
  '#ffaec9',
  '#ffc90e',
  '#efe4b0',
  '#b5e61d',
  '#99d9ea',
  '#7092be',
  '#c8bfe7'
];

function normalizeVisiblePages(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  const seen = new Set<string>();
  const pages: string[] = [];
  value.forEach(item => {
    const page = String(item || '')
      .trim()
      .toLowerCase();
    if (!page || seen.has(page)) return;
    seen.add(page);
    pages.push(page);
  });
  return pages;
}

function normalizeRoles(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  const seen = new Set<string>();
  const roles: string[] = [];
  value.forEach(item => {
    const role = String(item || '')
      .trim()
      .toUpperCase();
    if (!role || seen.has(role) || !roleValueSet.has(role)) return;
    seen.add(role);
    roles.push(role);
  });
  return roles;
}

function normalizeFieldRolePermissions(
  editableValue: unknown,
  readonlyValue: unknown,
  priority: 'editable' | 'readonly' = 'readonly'
) {
  const editableRoles = normalizeRoles(editableValue);
  const readonlyRoles = normalizeRoles(readonlyValue);

  if (priority === 'editable') {
    const editableSet = new Set(editableRoles);
    return {
      editableRoles,
      readonlyRoles: readonlyRoles.filter(role => !editableSet.has(role))
    };
  }

  const readonlySet = new Set(readonlyRoles);
  return {
    editableRoles: editableRoles.filter(role => !readonlySet.has(role)),
    readonlyRoles
  };
}

function normalizeFieldType(type?: string): Api.Schema.FormFieldDef['type'] {
  const val = (type || '').trim().toLowerCase();
  if (['single_line_text', 'string', 'text', 'input'].includes(val)) return 'single_line_text';
  if (['multi_line_text', 'textarea', 'multiline'].includes(val)) return 'multi_line_text';
  if (val === 'radio') return 'radio';
  if (val === 'checkbox') return 'checkbox';
  if (val === 'select') return 'select';
  if (['select_multiple', 'multi_select', 'select_multi'].includes(val)) return 'select_multiple';
  if (['number', 'int', 'float', 'decimal'].includes(val)) return 'number';
  if (['datetime', 'date', 'date-time', 'date_time', 'date_time_picker', 'datetime_picker'].includes(val)) {
    return 'datetime';
  }
  if (['upload_attachment', 'upload_file', 'attachment', 'file'].includes(val)) return 'upload_attachment';
  if (['upload_image', 'image_upload', 'image'].includes(val)) return 'upload_image';
  if (['color', 'colour', 'color_picker', 'colour_picker'].includes(val)) return 'color';
  if (val === 'project') return 'project';
  return 'single_line_text';
}

function requiresOptions(type?: string) {
  return optionTypeSet.has(normalizeFieldType(type));
}

function normalizeFieldKey(key?: string) {
  return (key || '').trim().toLowerCase();
}

function normalizeBuiltInFieldKey(key?: string) {
  const normalized = normalizeFieldKey(key);
  return normalized === 'projectid' ? 'project_id' : normalized;
}

function isPlayerSchemaCode(code?: string) {
  return (code || '').trim().toLowerCase() === PLAYER_SCHEMA_CODE;
}

function getBuiltInFieldType(key?: string): Api.Schema.FormFieldType | undefined {
  return playerBuiltInTypeMap.get(normalizeBuiltInFieldKey(key));
}

function isFieldTypeLocked(field: Pick<Api.Schema.FormFieldDef, 'key'>) {
  if (!isPlayerSchemaCode(formModel.code)) return false;
  return Boolean(getBuiltInFieldType(field.key));
}

function normalizeFieldFormItem(field: Api.Schema.FormFieldDef): SchemaFieldFormItem {
  const rolePermissions = normalizeFieldRolePermissions(field.editable_roles, field.readonly_roles, 'readonly');
  const normalizedType = getBuiltInFieldType(field.key) || normalizeFieldType(field.type);
  return {
    key: field.key,
    label: field.label,
    type: normalizedType,
    required: field.required ?? false,
    options: field.options,
    optionItems: optionsToOptionItems(Array.isArray(field.options) ? field.options : []),
    order: field.order ?? 0,
    visible_pages: normalizeVisiblePages(field.visible_pages),
    visible_roles: normalizeRoles(field.visible_roles),
    editable_roles: rolePermissions.editableRoles,
    readonly_roles: rolePermissions.readonlyRoles
  };
}

function ensurePlayerBuiltInFields(fields: SchemaFieldFormItem[]) {
  if (!isPlayerSchemaCode(formModel.code)) return fields;

  const nextFields: SchemaFieldFormItem[] = fields.map(field => {
    const rolePermissions = normalizeFieldRolePermissions(field.editable_roles, field.readonly_roles, 'readonly');
    return {
      ...field,
      optionItems: [...(field.optionItems || [])],
      visible_roles: normalizeRoles(field.visible_roles),
      editable_roles: rolePermissions.editableRoles,
      readonly_roles: rolePermissions.readonlyRoles
    };
  });
  const keyMap = new Map(nextFields.map(field => [normalizeBuiltInFieldKey(field.key), field] as const));
  const maxOrder = nextFields.reduce((max, field, index) => Math.max(max, field.order ?? index), -1);
  let nextOrder = maxOrder + 1;

  playerBuiltInFieldTemplates.forEach(template => {
    const normalizedKey = normalizeBuiltInFieldKey(template.key);
    const existing = keyMap.get(normalizedKey);
    if (existing) {
      if (!existing.label?.trim()) {
        existing.label = template.label;
      }
      existing.type = template.type;
      if (!Array.isArray(existing.visible_pages)) {
        existing.visible_pages = [...template.visible_pages];
      }
      return;
    }

    const builtInField: SchemaFieldFormItem = {
      key: template.key,
      label: template.label,
      type: template.type,
      required: false,
      optionItems: [],
      visible_pages: [...template.visible_pages],
      visible_roles: [],
      editable_roles: [],
      readonly_roles: [],
      order: nextOrder
    };
    nextFields.push(builtInField);
    keyMap.set(normalizedKey, builtInField);
    nextOrder += 1;
  });

  return nextFields.sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
}

function normalizeOptionItem(item: unknown): SchemaFieldOptionItem | null {
  if (item === null || item === undefined) return null;

  if (typeof item === 'object') {
    const option = item as Record<string, unknown>;
    const label = option.label ?? option.name ?? option.value ?? option.id ?? option.key;
    const color = typeof option.color === 'string' ? option.color.trim() : '';
    if (!label) return null;
    const next: SchemaFieldOptionItem = { label: String(label).trim() };
    if (color) next.color = color;
    return next.label ? next : null;
  }

  const label = String(item).trim();
  return label ? { label } : null;
}

function optionsToOptionItems(options?: unknown[]): SchemaFieldOptionItem[] {
  if (!Array.isArray(options)) return [];
  return options.map(normalizeOptionItem).filter((item): item is SchemaFieldOptionItem => Boolean(item));
}

function optionItemsToOptions(items?: SchemaFieldOptionItem[]): unknown[] {
  if (!Array.isArray(items)) return [];
  return items
    .map(item => {
      const label = item.label.trim();
      if (!label) return null;
      const color = item.color?.trim();
      if (!color) return label;
      return {
        label,
        value: label,
        color
      };
    })
    .filter((item): item is string | { label: string; value: string; color: string } => Boolean(item));
}

function onFieldTypeChange(field: SchemaFieldFormItem, value: string | null) {
  if (isFieldTypeLocked(field)) {
    field.type = getBuiltInFieldType(field.key) || field.type;
    return;
  }

  field.type = normalizeFieldType(value || undefined);
  if (requiresOptions(field.type) && field.optionItems.length === 0) {
    field.optionItems.push({ label: '' });
  }
}

function addOption(fieldIndex: number) {
  formModel.fields[fieldIndex].optionItems.push({ label: '' });
}

function removeOption(fieldIndex: number, optionIndex: number) {
  formModel.fields[fieldIndex].optionItems.splice(optionIndex, 1);
}

function setOptionColor(option: SchemaFieldOptionItem, value: string | null) {
  option.color = value?.trim() || undefined;
}

function setFieldEditableRoles(field: SchemaFieldFormItem, value: string[] | null) {
  const rolePermissions = normalizeFieldRolePermissions(value, field.readonly_roles, 'editable');
  field.editable_roles = rolePermissions.editableRoles;
  field.readonly_roles = rolePermissions.readonlyRoles;
}

function setFieldReadonlyRoles(field: SchemaFieldFormItem, value: string[] | null) {
  const rolePermissions = normalizeFieldRolePermissions(field.editable_roles, value, 'readonly');
  field.editable_roles = rolePermissions.editableRoles;
  field.readonly_roles = rolePermissions.readonlyRoles;
}

const columns: NaiveUI.DataTableBaseColumn<Api.Schema.Item>[] = [
  { title: '表单名称', key: 'name', width: 160 },
  { title: 'Code', key: 'code', width: 120 },
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
    width: 200,
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

function getEnabledParam(): boolean | undefined {
  if (searchEnabled.value === 'true') return true;
  if (searchEnabled.value === 'false') return false;
  return undefined;
}

async function loadData() {
  loading.value = true;
  try {
    const { data, error } = await fetchSchemaList({
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
  formModel.code = '';
  formModel.enabled = true;
  formModel.fields = [];
  modalVisible.value = true;
}

async function openEdit(row: Api.Schema.Item) {
  isEdit.value = true;
  editId.value = row.id;
  const { data, error } = await fetchSchema(row.id);
  if (error || !data) return;
  formModel.name = data.name;
  formModel.code = data.code;
  formModel.enabled = data.enabled;
  const normalizedFields = (data.fields || []).map(field => normalizeFieldFormItem(field));
  const orderedFields = normalizedFields.sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  formModel.fields = ensurePlayerBuiltInFields(orderedFields);
  modalVisible.value = true;
}

watch(
  () => [modalVisible.value, formModel.code] as const,
  ([visible]) => {
    if (!visible) return;
    formModel.fields = ensurePlayerBuiltInFields(formModel.fields);
  }
);

function getNextFieldOrder() {
  const orders = formModel.fields.map(field => field.order ?? 0);
  return (orders.length ? Math.max(...orders) : -1) + 1;
}

function addField() {
  formModel.fields.push({
    label: '',
    type: 'single_line_text',
    required: false,
    optionItems: [],
    visible_pages: [],
    visible_roles: [],
    editable_roles: [],
    readonly_roles: [],
    order: getNextFieldOrder()
  });
}

function removeField(index: number) {
  formModel.fields.splice(index, 1);
}

function buildSubmitFields() {
  const fields: Api.Schema.FormFieldDef[] = [];
  formModel.fields = ensurePlayerBuiltInFields(formModel.fields);
  for (const [i, f] of formModel.fields.entries()) {
    const label = f.label.trim();
    if (!label) {
      window.$message?.warning(`第 ${i + 1} 个字段的名称不能为空`);
      return null;
    }

    const normalizedType = getBuiltInFieldType(f.key) || normalizeFieldType(f.type);
    const options = requiresOptions(normalizedType) ? optionItemsToOptions(f.optionItems) : undefined;
    const visiblePages = normalizeVisiblePages(f.visible_pages);
    if (requiresOptions(normalizedType) && (!options || options.length === 0)) {
      window.$message?.warning(`第 ${i + 1} 个字段至少需要一个选项`);
      return null;
    }

    const visibleRoles = normalizeRoles(f.visible_roles);
    const rolePermissions = normalizeFieldRolePermissions(f.editable_roles, f.readonly_roles, 'readonly');
    fields.push({
      key: f.key?.trim() || undefined,
      label,
      type: normalizedType,
      required: f.required ?? false,
      options,
      visible_pages: visiblePages.length > 0 ? visiblePages : undefined,
      visible_roles: visibleRoles.length > 0 ? visibleRoles : undefined,
      editable_roles: rolePermissions.editableRoles.length > 0 ? rolePermissions.editableRoles : undefined,
      readonly_roles: rolePermissions.readonlyRoles.length > 0 ? rolePermissions.readonlyRoles : undefined,
      order: i
    });
  }

  return fields;
}

async function submitModal() {
  if (!formModel.name.trim()) {
    window.$message?.warning('请输入表单名称');
    return;
  }
  if (!formModel.code.trim()) {
    window.$message?.warning('请输入表单 Code');
    return;
  }

  const fields = buildSubmitFields();
  if (!fields) return;

  modalLoading.value = true;
  try {
    if (isEdit.value && editId.value !== null) {
      const { error } = await updateSchema(editId.value, {
        name: formModel.name.trim(),
        enabled: formModel.enabled,
        fields
      });
      if (error) return;
      window.$message?.success('更新成功');
    } else {
      const { error } = await createSchema({
        name: formModel.name.trim(),
        code: formModel.code.trim(),
        enabled: formModel.enabled,
        fields
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

function toggleEnabled(row: Api.Schema.Item) {
  updateSchema(row.id, { enabled: !row.enabled }).then(({ error }) => {
    if (error) return;
    window.$message?.success(row.enabled ? '已停用' : '已启用');
    loadData();
  });
}

function onSearch() {
  pagination.page = 1;
  loadData();
}

function getSchemaRowKey(row: Api.Schema.Item) {
  return row.id;
}

onMounted(async () => {
  await loadData();
});
</script>

<template>
  <div class="min-h-500px">
    <NCard title="表单管理" :bordered="false">
      <template #header-extra>
        <NSpace>
          <NInput v-model:value="searchName" placeholder="表单名称" clearable class="w-160px" @keyup.enter="onSearch" />
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
          <NButton type="primary" @click="openCreate">新建表单</NButton>
        </NSpace>
      </template>

      <NDataTable :columns="columns" :data="tableData" :loading="loading" :row-key="getSchemaRowKey" />

      <div class="flex justify-end pt-4">
        <NPagination
          v-model:page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :item-count="total"
          :page-sizes="[10, 20, 50]"
          show-size-picker
          @update:page="loadData"
          @update:page-size="
            () => {
              pagination.page = 1;
              loadData();
            }
          "
        />
      </div>
    </NCard>

    <NModal v-model:show="modalVisible" :title="isEdit ? '编辑表单' : '新建表单'" preset="card" class="w-760px">
      <div class="schema-modal-body">
        <NForm :model="formModel" label-placement="left" label-width="90">
          <NFormItem label="表单名称" required>
            <NInput v-model:value="formModel.name" placeholder="名称" :disabled="isEdit" />
          </NFormItem>
          <NFormItem label="Code" required>
            <NInput v-model:value="formModel.code" placeholder="如: player_form" :disabled="isEdit" />
          </NFormItem>
          <NFormItem label="启用">
            <NSwitch v-model:value="formModel.enabled" />
          </NFormItem>
          <NFormItem label="字段管理">
            <div class="w-full space-y-2">
              <NButton size="small" @click="addField">添加字段</NButton>
              <div class="text-12px text-[#999]">字段 ID 由后端自动生成，无需手动填写。</div>
              <div class="text-12px text-[#999]">拖动左侧图标，可调整字段顺序。</div>
              <div class="text-12px text-[#999]">页面可见留空时，表示 qgs/list、hgs/list、qgs/submit 全部可见。</div>
              <div class="text-12px text-[#999]">可编辑角色和只读角色互斥，后选择的一项优先。</div>
              <VueDraggable v-model="formModel.fields" :animation="180" handle=".field-drag-handle" class="field-list">
                <div v-for="(f, index) in formModel.fields" :key="f.key || `field-${index}`" class="field-card">
                  <div class="field-main">
                    <icon-mdi-drag class="field-drag-handle" />
                    <NInput v-model:value="f.label" placeholder="字段名称" size="small" class="w-180px" />
                    <NSelect
                      :value="f.type"
                      :options="fieldTypeOptions"
                      :disabled="isFieldTypeLocked(f)"
                      size="small"
                      class="w-140px"
                      @update:value="value => onFieldTypeChange(f, value)"
                    />
                    <NCheckbox v-model:checked="f.required">必填</NCheckbox>
                    <NSelect
                      v-model:value="f.visible_pages"
                      :options="pageOptions"
                      size="small"
                      class="w-220px"
                      multiple
                      clearable
                      filterable
                      max-tag-count="responsive"
                      placeholder="全部页面可见"
                    />
                    <NSelect
                      v-model:value="f.visible_roles"
                      :options="roleOptions"
                      size="small"
                      class="w-220px"
                      multiple
                      clearable
                      filterable
                      max-tag-count="responsive"
                      placeholder="全部角色可见"
                    />
                    <NSelect
                      :value="f.editable_roles"
                      :options="roleOptions"
                      size="small"
                      class="w-220px"
                      multiple
                      clearable
                      filterable
                      max-tag-count="responsive"
                      placeholder="全部角色可编辑"
                      @update:value="value => setFieldEditableRoles(f, value)"
                    />
                    <NSelect
                      :value="f.readonly_roles"
                      :options="roleOptions"
                      size="small"
                      class="w-220px"
                      multiple
                      clearable
                      filterable
                      max-tag-count="responsive"
                      placeholder="无只读角色"
                      @update:value="value => setFieldReadonlyRoles(f, value)"
                    />
                    <NButton
                      size="small"
                      quaternary
                      type="error"
                      :disabled="isFieldTypeLocked(f)"
                      @click="removeField(index)"
                    >
                      删除
                    </NButton>
                  </div>

                  <div v-if="requiresOptions(f.type)" class="option-editor">
                    <div class="mb-2 text-12px text-[#666]">选项配置（每个选项可单独设置颜色）</div>
                    <div v-for="(option, optionIndex) in f.optionItems" :key="optionIndex" class="option-row">
                      <NInput
                        v-model:value="option.label"
                        size="small"
                        placeholder="选项名称"
                        class="min-w-180px flex-1"
                      />
                      <NColorPicker
                        :value="option.color"
                        clearable
                        :show-alpha="false"
                        :show-preview="false"
                        :modes="['hex']"
                        :swatches="optionColorSwatches"
                        class="option-color-picker"
                        @update:value="value => setOptionColor(option, value)"
                      />
                      <NButton size="small" tertiary type="error" @click="removeOption(index, optionIndex)">
                        删除
                      </NButton>
                    </div>
                    <NButton size="tiny" tertiary @click="addOption(index)">新增选项</NButton>
                  </div>
                </div>
              </VueDraggable>
            </div>
          </NFormItem>
        </NForm>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="modalVisible = false">取消</NButton>
          <NButton type="primary" :loading="modalLoading" @click="submitModal">确定</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.schema-modal-body {
  max-height: calc(90vh - 180px);
  overflow-y: auto;
  padding-right: 4px;
}

.field-card {
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  padding: 10px;
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.field-drag-handle {
  cursor: move;
  flex-shrink: 0;
  color: var(--n-text-color-3);
}

.option-editor {
  margin-top: 8px;
  border-top: 1px dashed var(--n-border-color);
  padding-top: 8px;
}

.option-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.option-color-picker {
  width: 40px;
}

.option-color-picker :deep(.n-color-picker-trigger__value) {
  display: none;
}

.option-color-picker :deep(.n-color-picker-trigger) {
  width: 32px;
  min-width: 32px;
  padding: 0;
}
</style>
