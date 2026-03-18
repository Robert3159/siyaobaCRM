<script setup lang="ts">
import { computed, h, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import type { FormInst, FormItemRule, FormRules } from 'naive-ui';
import { fetchProjectList } from '@/service/api/project';
import { fetchSchemaByCode } from '@/service/api/schema';
import { submitPlayer } from '@/service/api/player';

interface DynamicField extends Api.Schema.FormFieldDef {
  key: string;
  default?: unknown;
  default_value?: unknown;
  placeholder?: string;
  help?: string;
  help_text?: string;
  multiple?: boolean;
}

interface UploadFieldValue {
  name: string;
  type: string;
  size: number;
  data_url: string;
}

type FieldOption = { label: string; value: string | number; color?: string };
type FormPrimitive = string | number | boolean;
type FormValue = FormPrimitive | FormPrimitive[] | UploadFieldValue[] | null | undefined;

const SCHEMA_CODE = 'player_form';
const SUBMIT_PAGE_KEY = 'qgs/submit';
const UPLOAD_MAX_COUNT = 10;

const formRef = ref<FormInst | null>(null);
const schema = ref<Api.Schema.Item | null>(null);
const projects = ref<Api.Project.Item[]>([]);
const loading = ref(true);
const submitLoading = ref(false);
const schemaWarning = ref('');
const formModel = reactive<Record<string, FormValue>>({});
const uploadInputRefs = ref<Record<string, HTMLInputElement | null>>({});
const activeUploadImageFieldKey = ref<string | null>(null);

function normalizeFieldType(type?: string) {
  const val = (type || 'single_line_text').toLowerCase();
  if (['single_line_text', 'string', 'text', 'input'].includes(val)) return 'string';
  if (['multi_line_text', 'textarea', 'multiline'].includes(val)) return 'textarea';
  if (val === 'int' || val === 'float' || val === 'decimal') return 'number';
  if (['datetime', 'date-time', 'date_time', 'date', 'date_time_picker', 'datetime_picker'].includes(val)) {
    return 'datetime';
  }
  if (['select_multiple', 'multi_select', 'select_multi'].includes(val)) return 'select_multiple';
  if (['upload_attachment', 'attachment', 'upload_file', 'file'].includes(val)) return 'upload_attachment';
  if (['upload_image', 'image_upload', 'image'].includes(val)) return 'upload_image';
  if (['color', 'colour', 'color_picker', 'colour_picker'].includes(val)) return 'color';
  if (val === 'boolean') return 'switch';
  return val;
}

function normalizeVisiblePages(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  const seen = new Set<string>();
  const normalized: string[] = [];
  value.forEach(item => {
    const pageKey = String(item || '')
      .trim()
      .toLowerCase();
    if (!pageKey || seen.has(pageKey)) return;
    seen.add(pageKey);
    normalized.push(pageKey);
  });
  return normalized;
}

function isFieldVisibleForPage(field: Api.Schema.FormFieldDef, pageKey: string) {
  const visiblePages = normalizeVisiblePages(field.visible_pages);
  if (visiblePages.length === 0) return true;
  return visiblePages.includes(pageKey);
}

const fields = computed<DynamicField[]>(() => {
  const list = Array.isArray(schema.value?.fields) ? (schema.value?.fields as Api.Schema.FormFieldDef[]) : [];
  return list
    .filter(
      (field): field is Api.Schema.FormFieldDef & { key: string } =>
        typeof field.key === 'string' && Boolean(field.key.trim()) && isFieldVisibleForPage(field, SUBMIT_PAGE_KEY)
    )
    .map(field => ({ ...field, key: field.key.trim() }))
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
});

function isProjectField(field: DynamicField) {
  const type = normalizeFieldType(field.type);
  const key = field.key.trim().toLowerCase();
  return type === 'project' || key === 'project' || key === 'project_id' || key === 'projectid';
}

const projectField = computed<DynamicField | null>(() => fields.value.find(isProjectField) || null);
const projectKey = computed(() => projectField.value?.key || 'project_id');
const projectLabel = computed(() => projectField.value?.label || 'Project');
const otherFields = computed(() => fields.value.filter(field => !isProjectField(field)));

const projectOptions = computed(() =>
  projects.value.map(project => ({
    label: project.name,
    value: project.id
  }))
);

function normalizeProjectId(value: unknown): number | undefined {
  if (typeof value === 'number') {
    return Number.isFinite(value) && value > 0 ? value : undefined;
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return undefined;
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
  }

  if (Array.isArray(value) && value.length === 1) {
    return normalizeProjectId(value[0]);
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return normalizeProjectId(record.value ?? record.id);
  }

  return undefined;
}

function resolveProjectIdFromModel(): number | undefined {
  const keys = new Set([projectKey.value, 'project', 'project_id', 'projectId', 'projectid']);
  for (const key of keys) {
    if (key in formModel) {
      const parsed = normalizeProjectId(formModel[key]);
      if (parsed) return parsed;
    }
  }
  return undefined;
}

const totalFieldCount = computed(() => 1 + otherFields.value.length);
const requiredFieldCount = computed(() => 1 + otherFields.value.filter(field => Boolean(field.required)).length);
const optionalFieldCount = computed(() => Math.max(totalFieldCount.value - requiredFieldCount.value, 0));

function hasFieldValue(field: DynamicField, value: unknown) {
  const type = normalizeFieldType(field.type);

  if (type === 'switch') return value !== null && value !== undefined;
  if (isUploadType(type)) return normalizeUploadValues(value).length > 0;
  if (type === 'number' || type === 'datetime') {
    return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  }
  if (type === 'checkbox' || type === 'select_multiple' || (type === 'select' && Boolean(field.multiple))) {
    return Array.isArray(value) && value.length > 0;
  }
  if (typeof value === 'string') return value.trim().length > 0;
  return value !== null && value !== undefined && value !== '';
}

const completionPercent = computed(() => {
  const total = totalFieldCount.value;
  if (!total) return 0;

  let completed = 0;

  if (resolveProjectIdFromModel()) {
    completed += 1;
  }

  otherFields.value.forEach(field => {
    if (hasFieldValue(field, formModel[field.key])) {
      completed += 1;
    }
  });

  return Math.round((completed / total) * 100);
});

function isFieldFullWidth(field: DynamicField) {
  const type = normalizeFieldType(field.type);
  return ['textarea', 'radio', 'checkbox', 'upload_image', 'upload_attachment'].includes(type);
}

function normalizeMultiValue(value: unknown): FormPrimitive[] {
  if (!Array.isArray(value)) return [];
  return value
    .map(item => {
      if (typeof item === 'number') return item;
      if (typeof item === 'boolean') return item;
      if (item === null || item === undefined) return null;
      return String(item);
    })
    .filter((item): item is FormPrimitive => item !== null);
}

function toNumberDefault(value: unknown): number | undefined {
  if (typeof value === 'number') return value;
  if (value === '' || value === null || value === undefined) return undefined;
  const num = Number(value);
  return Number.isFinite(num) ? num : undefined;
}

function toDateDefault(value: unknown): number | undefined {
  if (typeof value === 'number') return value;
  if (!value) return undefined;
  const timestamp = new Date(String(value)).getTime();
  return Number.isFinite(timestamp) ? timestamp : undefined;
}

function toBaseDefault(value: unknown): FormPrimitive | '' {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  if (value === null || value === undefined) return '';
  return String(value);
}

function normalizeUploadValue(value: unknown): UploadFieldValue | undefined {
  if (value === null || value === undefined) return undefined;

  if (typeof value === 'string') {
    const url = value.trim();
    if (!url) return undefined;
    return {
      name: 'uploaded-file',
      type: '',
      size: 0,
      data_url: url
    };
  }

  if (typeof value !== 'object') return undefined;
  const data = value as Record<string, unknown>;
  const dataUrl = data.data_url ?? data.url;
  if (typeof dataUrl !== 'string' || !dataUrl.trim()) return undefined;

  return {
    name: typeof data.name === 'string' && data.name.trim() ? data.name.trim() : 'uploaded-file',
    type: typeof data.type === 'string' ? data.type : '',
    size: typeof data.size === 'number' && Number.isFinite(data.size) ? data.size : 0,
    data_url: dataUrl.trim()
  };
}

function normalizeUploadValues(value: unknown): UploadFieldValue[] {
  if (value === null || value === undefined) return [];

  if (Array.isArray(value)) {
    return value
      .map(item => normalizeUploadValue(item))
      .filter((item): item is UploadFieldValue => Boolean(item))
      .slice(0, UPLOAD_MAX_COUNT);
  }

  const single = normalizeUploadValue(value);
  return single ? [single] : [];
}

function isUploadType(type: string) {
  return type === 'upload_attachment' || type === 'upload_image';
}

function toUploadDefault(value: unknown): UploadFieldValue[] {
  return normalizeUploadValues(value);
}

function getDefaultValue(field: DynamicField): FormValue {
  const type = normalizeFieldType(field.type);
  const rawDefault = field.default ?? field.default_value;

  if (type === 'checkbox') {
    return normalizeMultiValue(rawDefault);
  }

  if (type === 'select_multiple' || (type === 'select' && field.multiple)) {
    return normalizeMultiValue(rawDefault);
  }

  if (type === 'switch') {
    return typeof rawDefault === 'boolean' ? rawDefault : false;
  }

  if (type === 'number') return toNumberDefault(rawDefault);
  if (type === 'datetime') return toDateDefault(rawDefault);
  if (isUploadType(type)) return toUploadDefault(rawDefault);
  return toBaseDefault(rawDefault);
}

function initFormModel() {
  for (const key of Object.keys(formModel)) {
    Reflect.deleteProperty(formModel, key);
  }

  fields.value.forEach(field => {
    formModel[field.key] = getDefaultValue(field);
  });

  if (!(projectKey.value in formModel)) {
    formModel[projectKey.value] = undefined;
  }
}

function toSelectOptions(options: unknown): FieldOption[] {
  if (!Array.isArray(options)) return [];
  const result: FieldOption[] = [];

  for (const item of options) {
    if (item !== null && item !== undefined) {
      if (typeof item === 'object') {
        const option = item as Record<string, unknown>;
        const rawValue = option.value ?? option.id ?? option.key;
        if (rawValue !== undefined && rawValue !== null) {
          const rawLabel = option.label ?? option.name ?? rawValue;
          const color = typeof option.color === 'string' ? option.color.trim() : '';

          result.push({
            label: String(rawLabel),
            value: typeof rawValue === 'number' ? rawValue : String(rawValue),
            color: color || undefined
          });
        }
      } else if (typeof item === 'number') {
        result.push({ label: String(item), value: item });
      } else {
        result.push({ label: String(item), value: String(item) });
      }
    }
  }

  return result;
}

function getFieldPlaceholder(field: DynamicField) {
  if (field.placeholder) return field.placeholder;

  const type = normalizeFieldType(field.type);
  const prefix = [
    'select',
    'select_multiple',
    'radio',
    'checkbox',
    'project',
    'datetime',
    'color',
    'upload_attachment',
    'upload_image'
  ].includes(type)
    ? '请选择'
    : '请输入';

  return `${prefix}${field.label || field.key}`;
}

function getNumberValue(key: string) {
  const value = formModel[key];
  if (typeof value === 'number') return value;
  if (value === null || value === undefined || value === '') return undefined;
  const num = Number(value);
  return Number.isFinite(num) ? num : undefined;
}

function setNumberValue(key: string, value: number | null) {
  formModel[key] = value ?? undefined;
}

function getDateValue(key: string) {
  const value = formModel[key];
  if (typeof value === 'number') return value;
  if (value === null || value === undefined || value === '') return undefined;
  const timestamp = new Date(String(value)).getTime();
  return Number.isFinite(timestamp) ? timestamp : undefined;
}

function setDateValue(key: string, value: number | null) {
  formModel[key] = value ?? undefined;
}

function getStringValue(key: string) {
  const value = formModel[key];
  if (value === null || value === undefined) return '';
  return String(value);
}

function setStringValue(key: string, value: string | null) {
  formModel[key] = value ?? '';
}

function getColorValue(key: string): string | undefined {
  const value = formModel[key];
  if (typeof value !== 'string') return undefined;
  const color = value.trim();
  return color || undefined;
}

function setColorValue(key: string, value: string | null) {
  formModel[key] = value?.trim() || '';
}

function getProjectSelectValue(key: string): number | undefined {
  return normalizeProjectId(formModel[key]);
}

function setProjectSelectValue(key: string, value: unknown) {
  formModel[key] = normalizeProjectId(value);
}

function getSelectValue(key: string): string | number | Array<string | number> | undefined {
  const value = formModel[key];
  if (typeof value === 'string' || typeof value === 'number') return value;
  if (Array.isArray(value)) {
    return value.filter(item => typeof item === 'string' || typeof item === 'number') as Array<string | number>;
  }
  return undefined;
}

function setSelectValue(key: string, value: string | number | Array<string | number> | null) {
  if (Array.isArray(value)) {
    formModel[key] = value;
    return;
  }
  formModel[key] = value ?? undefined;
}

function getRadioValue(key: string): string | number | boolean | undefined {
  const value = formModel[key];
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value;
  return undefined;
}

function setRadioValue(key: string, value: string | number | boolean | null) {
  formModel[key] = value ?? undefined;
}

function getCheckboxValue(key: string): Array<string | number> {
  const value = formModel[key];
  if (!Array.isArray(value)) return [];
  return value.filter(item => typeof item === 'string' || typeof item === 'number') as Array<string | number>;
}

function setCheckboxValue(key: string, value: Array<string | number> | null) {
  formModel[key] = value ?? [];
}

function getSwitchValue(key: string): boolean {
  return Boolean(formModel[key]);
}

function setSwitchValue(key: string, value: string | number | boolean) {
  formModel[key] = Boolean(value);
}

function getUploadValues(key: string): UploadFieldValue[] {
  return normalizeUploadValues(formModel[key]);
}

function setUploadInputRef(key: string, el: HTMLInputElement | null) {
  uploadInputRefs.value[key] = el;
}

function setActiveUploadImageField(field: DynamicField) {
  activeUploadImageFieldKey.value = normalizeFieldType(field.type) === 'upload_image' ? field.key : null;
}

function clearUploadValue(key: string) {
  formModel[key] = [];
  if (uploadInputRefs.value[key]) {
    uploadInputRefs.value[key]!.value = '';
  }
}

function removeUploadValue(key: string, index: number) {
  const list = getUploadValues(key);
  if (index < 0 || index >= list.length) return;
  const next = list.slice();
  next.splice(index, 1);
  formModel[key] = next;
}

function pickUploadFile(field: DynamicField) {
  setActiveUploadImageField(field);
  const input = uploadInputRefs.value[field.key];
  if (!input) return;
  input.value = '';
  input.click();
}

function fileToDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('read-file-failed'));
    reader.readAsDataURL(file);
  });
}

function getClipboardImageFile(event: ClipboardEvent): File | null {
  const items = event.clipboardData?.items;
  if (!items) return null;

  for (const item of Array.from(items)) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const file = item.getAsFile();
      if (file) return file;
    }
  }

  return null;
}

async function toUploadFieldValue(field: DynamicField, file: File): Promise<UploadFieldValue | null> {
  const type = normalizeFieldType(field.type);
  const isImage = type === 'upload_image';

  if (isImage && !file.type.startsWith('image/')) {
    window.$message?.error('请上传图片类型文件');
    return null;
  }

  const maxSize = isImage ? 20 * 1024 * 1024 : 100 * 1024 * 1024;
  if (file.size > maxSize) {
    window.$message?.error(isImage ? '图片大小不能超过 20MB' : '附件大小不能超过 100MB');
    return null;
  }

  try {
    const dataUrl = await fileToDataUrl(file);
    return {
      name: file.name || (isImage ? 'pasted-image.png' : 'uploaded-file'),
      type: file.type,
      size: file.size,
      data_url: dataUrl
    };
  } catch {
    window.$message?.error('文件读取失败，请重试');
    return null;
  }
}

async function appendUploadFiles(field: DynamicField, files: File[]) {
  if (!files.length) return;

  const current = getUploadValues(field.key);
  if (current.length >= UPLOAD_MAX_COUNT) {
    window.$message?.warning(`最多可上传 ${UPLOAD_MAX_COUNT} 个文件`);
    return;
  }

  const remain = UPLOAD_MAX_COUNT - current.length;
  const selectedFiles = files.slice(0, remain);
  if (files.length > remain) {
    window.$message?.warning(`最多可上传 ${UPLOAD_MAX_COUNT} 个文件`);
  }

  const resolvedUploads = await Promise.all(selectedFiles.map(file => toUploadFieldValue(field, file)));
  const nextUploads = resolvedUploads.filter((item): item is UploadFieldValue => Boolean(item));
  const next = [...current, ...nextUploads];

  formModel[field.key] = next;
}

async function onUploadInputChange(field: DynamicField, event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  if (!files.length) {
    input.value = '';
    return;
  }

  await appendUploadFiles(field, files);
  input.value = '';
}

async function onUploadFieldPaste(field: DynamicField, event: Event) {
  const clipboardEvent = event as ClipboardEvent;
  setActiveUploadImageField(field);

  if (normalizeFieldType(field.type) !== 'upload_image') return;
  const file = getClipboardImageFile(clipboardEvent);
  if (!file) return;

  clipboardEvent.preventDefault();
  await appendUploadFiles(field, [file]);
}

async function onWindowPaste(event: ClipboardEvent) {
  const fieldKey = activeUploadImageFieldKey.value;
  if (!fieldKey) return;

  const field = fields.value.find(item => item.key === fieldKey);
  if (!field || normalizeFieldType(field.type) !== 'upload_image') return;

  const file = getClipboardImageFile(event);
  if (!file) return;

  event.preventDefault();
  await appendUploadFiles(field, [file]);
}

function getOptionTagStyle(option: FieldOption) {
  if (!option.color) return undefined;
  return {
    borderColor: option.color,
    color: option.color
  };
}

function renderSelectOptionLabel(option: FieldOption) {
  if (!option.color) return option.label;
  return h(
    'span',
    {
      class: 'field-option-tag',
      style: getOptionTagStyle(option)
    },
    option.label
  );
}

function buildRequiredRule(field: DynamicField): FormItemRule {
  const type = normalizeFieldType(field.type);
  const messagePrefix = [
    'select',
    'select_multiple',
    'radio',
    'checkbox',
    'datetime',
    'project',
    'switch',
    'color',
    'upload_attachment',
    'upload_image'
  ].includes(type)
    ? '请选择'
    : '请输入';

  return {
    required: true,
    message: `${messagePrefix}${field.label || field.key}`,
    trigger: ['blur', 'change']
  };
}

const formRules = computed<FormRules>(() => {
  const rules: FormRules = {};
  rules[projectKey.value] = [
    {
      required: true,
      trigger: ['blur', 'change'],
      validator: (_, value) => {
        return normalizeProjectId(value) || resolveProjectIdFromModel()
          ? true
          : new Error(`请选择${projectLabel.value}`);
      }
    }
  ];

  otherFields.value.forEach(field => {
    if (!field.required) return;
    rules[field.key] = [buildRequiredRule(field)];
  });

  return rules;
});

function formatDateTimeValue(value: unknown): string | undefined {
  if (value === null || value === undefined || value === '') return undefined;
  const date = new Date(Number(value));
  if (!Number.isFinite(date.getTime())) return undefined;

  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${y}-${m}-${d} ${hh}:${mm}:${ss}`;
}

function isEmptyFormValue(value: unknown): value is null | undefined | '' {
  return value === null || value === undefined || value === '';
}

function normalizeNumberSubmitValue(value: unknown): number | undefined {
  if (isEmptyFormValue(value)) return undefined;
  const num = Number(value);
  return Number.isFinite(num) ? num : undefined;
}

function normalizeColorSubmitValue(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const color = value.trim();
  return color || undefined;
}

function isMultiChoiceSubmitField(type: string, multiple?: boolean) {
  return type === 'checkbox' || type === 'select_multiple' || (type === 'select' && Boolean(multiple));
}

function normalizeMultiChoiceSubmitValue(value: unknown): Array<string | number | boolean> | undefined {
  if (!Array.isArray(value)) return undefined;
  const next = value.filter(item => item !== null && item !== undefined && item !== '');
  return next.length ? next : undefined;
}

function normalizeSubmitValue(field: DynamicField, value: unknown): unknown {
  const type = normalizeFieldType(field.type);

  if (type === 'switch') return Boolean(value);
  if (type === 'number') return normalizeNumberSubmitValue(value);
  if (type === 'datetime') return formatDateTimeValue(value);
  if (type === 'color') return normalizeColorSubmitValue(value);
  if (isUploadType(type)) {
    const list = normalizeUploadValues(value);
    return list.length > 0 ? list : undefined;
  }
  if (isMultiChoiceSubmitField(type, field.multiple)) return normalizeMultiChoiceSubmitValue(value);
  if (isEmptyFormValue(value)) return undefined;
  return value;
}

async function loadSchema() {
  schemaWarning.value = '';

  try {
    const { data, error } = await fetchSchemaByCode(SCHEMA_CODE);
    if (error || !data) {
      schema.value = null;
      schemaWarning.value = `未找到表单配置，请检查 schema code: ${SCHEMA_CODE}`;
      return;
    }

    schema.value = data;
    initFormModel();
  } catch {
    schema.value = null;
    schemaWarning.value = `加载表单配置失败，请稍后重试（schema code: ${SCHEMA_CODE}）`;
  }
}

async function loadProjects() {
  const { data, error } = await fetchProjectList({ page: 1, page_size: 100, enabled: true });
  projects.value = !error && Array.isArray(data?.items) ? data.items : [];
}

function resetForm() {
  initFormModel();
}

async function onSubmit() {
  const normalizedProjectId = resolveProjectIdFromModel();
  if (normalizedProjectId) {
    formModel[projectKey.value] = normalizedProjectId;
  }

  try {
    await formRef.value?.validate();
  } catch {
    return;
  }

  const projectId = resolveProjectIdFromModel();
  if (!projectId) {
    window.$message?.warning(`请选择${projectLabel.value}`);
    return;
  }

  formModel[projectKey.value] = projectId;

  const content: Record<string, unknown> = {};
  otherFields.value.forEach(field => {
    const normalized = normalizeSubmitValue(field, formModel[field.key]);
    if (normalized !== undefined) {
      content[field.key] = normalized;
    }
  });

  submitLoading.value = true;
  try {
    const { error } = await submitPlayer({ project_id: projectId, content });
    if (error) return;

    window.$message?.success('提交成功');
    resetForm();
  } finally {
    submitLoading.value = false;
  }
}

onMounted(async () => {
  window.addEventListener('paste', onWindowPaste);
  loading.value = true;
  try {
    await Promise.all([loadSchema(), loadProjects()]);
  } finally {
    loading.value = false;
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('paste', onWindowPaste);
});
</script>

<template>
  <div class="submit-page">
    <NCard :bordered="false" class="submit-card">
      <div class="submit-header">
        <div class="submit-header__title-wrap">
          <p class="submit-header__eyebrow">Player Form</p>
          <h2 class="submit-header__title">提交注册</h2>
          <p class="submit-header__desc"></p>
        </div>
        <div class="submit-header__stats">
          <div class="stat-pill">
            <span>选项总数</span>
            <strong>{{ totalFieldCount }}</strong>
          </div>
          <div class="stat-pill">
            <span>必填选项</span>
            <strong>{{ requiredFieldCount }}</strong>
          </div>
          <div class="stat-pill">
            <span>选填选项</span>
            <strong>{{ optionalFieldCount }}</strong>
          </div>
        </div>
      </div>

      <div class="progress-wrap">
        <div class="progress-caption">
          <span>填写进度</span>
          <strong>{{ completionPercent }}%</strong>
        </div>
        <NProgress :percentage="completionPercent" :height="8" />
      </div>

      <NSpin :show="loading">
        <NAlert v-if="schemaWarning" type="warning" :show-icon="true" :title="schemaWarning" class="mb-16px" />

        <template v-if="schema">
          <NForm ref="formRef" :model="formModel" :rules="formRules" label-placement="top" class="submit-form">
            <div class="form-grid">
              <NFormItem class="form-item form-item--full" :label="projectLabel" :path="projectKey" required>
                <NSelect
                  :value="getProjectSelectValue(projectKey)"
                  :placeholder="`请选择${projectLabel}`"
                  clearable
                  :options="projectOptions"
                  class="w-full"
                  @update:value="value => setProjectSelectValue(projectKey, value)"
                />
              </NFormItem>

              <template v-for="field in otherFields" :key="field.key">
                <NFormItem
                  class="form-item"
                  :class="{ 'form-item--full': isFieldFullWidth(field) }"
                  :label="field.label || field.key"
                  :path="field.key"
                  :required="Boolean(field.required)"
                >
                  <NInput
                    v-if="normalizeFieldType(field.type) === 'string'"
                    :value="getStringValue(field.key)"
                    :placeholder="getFieldPlaceholder(field)"
                    class="w-full"
                    @update:value="value => setStringValue(field.key, value)"
                  />

                  <NInput
                    v-else-if="normalizeFieldType(field.type) === 'textarea'"
                    type="textarea"
                    :value="getStringValue(field.key)"
                    :placeholder="getFieldPlaceholder(field)"
                    :autosize="{ minRows: 3, maxRows: 6 }"
                    class="w-full"
                    @update:value="value => setStringValue(field.key, value)"
                  />

                  <NInputNumber
                    v-else-if="normalizeFieldType(field.type) === 'number'"
                    :value="getNumberValue(field.key)"
                    :placeholder="getFieldPlaceholder(field)"
                    class="w-full"
                    clearable
                    @update:value="value => setNumberValue(field.key, value)"
                  />

                  <NDatePicker
                    v-else-if="normalizeFieldType(field.type) === 'datetime'"
                    type="datetime"
                    clearable
                    :value="getDateValue(field.key)"
                    class="w-full"
                    @update:value="value => setDateValue(field.key, value)"
                  />

                  <NColorPicker
                    v-else-if="normalizeFieldType(field.type) === 'color'"
                    :value="getColorValue(field.key)"
                    class="w-full"
                    clearable
                    @update:value="value => setColorValue(field.key, value)"
                  />

                  <NSelect
                    v-else-if="['select', 'select_multiple'].includes(normalizeFieldType(field.type))"
                    :value="getSelectValue(field.key)"
                    :placeholder="getFieldPlaceholder(field)"
                    :options="toSelectOptions(field.options)"
                    :multiple="normalizeFieldType(field.type) === 'select_multiple' || Boolean(field.multiple)"
                    :render-label="renderSelectOptionLabel"
                    clearable
                    class="w-full"
                    @update:value="value => setSelectValue(field.key, value)"
                  />

                  <NRadioGroup
                    v-else-if="normalizeFieldType(field.type) === 'radio'"
                    :value="getRadioValue(field.key)"
                    class="w-full"
                    @update:value="value => setRadioValue(field.key, value)"
                  >
                    <NSpace>
                      <NRadio
                        v-for="option in toSelectOptions(field.options)"
                        :key="`${field.key}-${option.value}`"
                        :value="option.value"
                      >
                        <span class="field-option-tag" :style="getOptionTagStyle(option)">{{ option.label }}</span>
                      </NRadio>
                    </NSpace>
                  </NRadioGroup>

                  <NCheckboxGroup
                    v-else-if="normalizeFieldType(field.type) === 'checkbox'"
                    :value="getCheckboxValue(field.key)"
                    class="w-full"
                    @update:value="value => setCheckboxValue(field.key, value)"
                  >
                    <NSpace>
                      <NCheckbox
                        v-for="option in toSelectOptions(field.options)"
                        :key="`${field.key}-${option.value}`"
                        :value="option.value"
                      >
                        <span class="field-option-tag" :style="getOptionTagStyle(option)">{{ option.label }}</span>
                      </NCheckbox>
                    </NSpace>
                  </NCheckboxGroup>

                  <div
                    v-else-if="normalizeFieldType(field.type) === 'upload_image'"
                    class="upload-image-field"
                    tabindex="0"
                    @click="setActiveUploadImageField(field)"
                    @focusin="setActiveUploadImageField(field)"
                    @paste="event => onUploadFieldPaste(field, event)"
                    @keydown.enter.prevent="pickUploadFile(field)"
                    @keydown.space.prevent="pickUploadFile(field)"
                  >
                    <div class="upload-image-grid">
                      <div
                        v-for="(uploadItem, uploadIndex) in getUploadValues(field.key)"
                        :key="`${field.key}-${uploadItem.name}-${uploadIndex}`"
                        class="upload-image-item"
                      >
                        <img :src="uploadItem.data_url" class="upload-image-box__preview" />
                        <button
                          type="button"
                          class="upload-image-item__remove"
                          @click.stop="removeUploadValue(field.key, uploadIndex)"
                        >
                          移除
                        </button>
                      </div>
                      <button
                        v-if="getUploadValues(field.key).length < UPLOAD_MAX_COUNT"
                        type="button"
                        class="upload-image-box"
                        @click="pickUploadFile(field)"
                      >
                        <div class="upload-image-box__plus">+</div>
                        <div class="upload-image-box__text">点击上传或粘贴图片</div>
                      </button>
                    </div>

                    <div class="upload-hint"></div>

                    <div v-if="getUploadValues(field.key).length" class="upload-meta">
                      <span class="upload-name">已上传 {{ getUploadValues(field.key).length }} 张</span>
                      <NButton text type="error" @click="clearUploadValue(field.key)">清空</NButton>
                    </div>

                    <input
                      :ref="el => setUploadInputRef(field.key, el as HTMLInputElement | null)"
                      type="file"
                      class="hidden"
                      accept="image/*"
                      multiple
                      @change="event => onUploadInputChange(field, event)"
                    />
                  </div>

                  <div v-else-if="normalizeFieldType(field.type) === 'upload_attachment'" class="w-full">
                    <NSpace vertical size="small" class="w-full">
                      <NButton
                        secondary
                        :disabled="getUploadValues(field.key).length >= UPLOAD_MAX_COUNT"
                        @click="pickUploadFile(field)"
                      >
                        选择附件
                      </NButton>
                      <div class="upload-hint">
                        支持任意文件格式，单个不超过 100MB，最多上传 {{ UPLOAD_MAX_COUNT }} 个
                      </div>
                      <div v-if="getUploadValues(field.key).length" class="upload-value">
                        <div
                          v-for="(uploadItem, uploadIndex) in getUploadValues(field.key)"
                          :key="`${field.key}-${uploadItem.name}-${uploadIndex}`"
                          class="upload-meta"
                        >
                          <span class="upload-name">{{ uploadItem.name }}</span>
                          <NButton text type="error" @click="removeUploadValue(field.key, uploadIndex)">移除</NButton>
                        </div>
                        <div class="upload-meta upload-meta--summary">
                          <span class="upload-name">已上传 {{ getUploadValues(field.key).length }} 个文件</span>
                          <NButton text type="error" @click="clearUploadValue(field.key)">清空</NButton>
                        </div>
                      </div>
                    </NSpace>
                    <input
                      :ref="el => setUploadInputRef(field.key, el as HTMLInputElement | null)"
                      type="file"
                      class="hidden"
                      multiple
                      @change="event => onUploadInputChange(field, event)"
                    />
                  </div>

                  <NSwitch
                    v-else-if="normalizeFieldType(field.type) === 'switch'"
                    :value="getSwitchValue(field.key)"
                    @update:value="value => setSwitchValue(field.key, value)"
                  />

                  <NInput
                    v-else
                    :value="getStringValue(field.key)"
                    :placeholder="getFieldPlaceholder(field)"
                    class="w-full"
                    @update:value="value => setStringValue(field.key, value)"
                  />

                  <div v-if="field.help || field.help_text" class="field-help">{{ field.help || field.help_text }}</div>
                </NFormItem>
              </template>

              <div class="form-actions form-item--full">
                <NSpace>
                  <NButton type="primary" size="large" :loading="submitLoading" @click="onSubmit">提交</NButton>
                  <NButton size="large" :disabled="submitLoading" @click="resetForm">重置</NButton>
                </NSpace>
              </div>
            </div>
          </NForm>
        </template>

        <template v-else>
          <NEmpty description="暂无可用表单配置，请联系管理员检查 schema code 是否为 player_form" />
        </template>
      </NSpin>
    </NCard>
  </div>
</template>

<style scoped>
.submit-page {
  min-height: 500px;
}

.submit-card {
  border-radius: 16px;
  animation: submit-fade-in 0.28s ease-out both;
}

.submit-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 10px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--n-border-color);
}

.submit-header__eyebrow {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--n-primary-color);
}

.submit-header__title {
  margin: 4px 0 6px;
  font-size: 24px;
  line-height: 1.25;
  color: var(--n-text-color);
}

.submit-header__desc {
  margin: 0;
  color: var(--n-text-color-2);
  font-size: 13px;
}

.submit-header__stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.stat-pill {
  min-width: 84px;
  border: 1px solid var(--n-border-color);
  border-radius: 12px;
  padding: 8px 12px;
  background: color-mix(in srgb, var(--n-primary-color) 6%, var(--n-card-color));
}

.stat-pill span {
  display: block;
  font-size: 12px;
  color: var(--n-text-color-3);
  line-height: 1.2;
}

.stat-pill strong {
  display: block;
  margin-top: 4px;
  font-size: 18px;
  line-height: 1;
  color: var(--n-text-color);
}

.progress-wrap {
  margin-bottom: 18px;
}

.progress-caption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--n-text-color-3);
}

.progress-caption strong {
  font-size: 13px;
  color: var(--n-primary-color);
}

.submit-form {
  max-width: 960px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 16px;
}

.form-item {
  margin-bottom: 2px;
}

.form-item--full {
  grid-column: 1 / -1;
}

.field-help {
  margin-top: 6px;
  color: var(--n-text-color-3);
  font-size: 12px;
}

.field-option-tag {
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 1px 8px;
}

.upload-value {
  width: 100%;
  border: 1px solid var(--n-border-color);
  border-radius: 10px;
  padding: 9px 10px;
  background: var(--n-color);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.upload-image-field {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  outline: none;
}

.upload-image-grid {
  display: grid;
  width: 100%;
  grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
  gap: 10px;
}

.upload-image-box {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  border: 1px dashed var(--n-border-color);
  border-radius: 12px;
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--n-primary-color) 8%, transparent),
    color-mix(in srgb, var(--n-info-color) 6%, transparent)
  );
  color: var(--n-text-color-3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
  padding: 0;
}

.upload-image-box:hover,
.upload-image-field:focus-within .upload-image-box {
  border-color: var(--n-primary-color);
  color: var(--n-primary-color);
  box-shadow: 0 10px 18px color-mix(in srgb, var(--n-primary-color) 16%, transparent);
  transform: translateY(-1px);
}

.upload-image-box__plus {
  font-size: 34px;
  line-height: 1;
  font-weight: 600;
}

.upload-image-box__text {
  width: 86%;
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.4;
  text-align: center;
}

.upload-image-box__preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 12px;
}

.upload-image-item {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 12px;
  overflow: hidden;
}

.upload-image-item__remove {
  position: absolute;
  right: 6px;
  bottom: 6px;
  border: 0;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
  line-height: 1.4;
  color: #fff;
  background: rgba(0, 0, 0, 0.55);
  cursor: pointer;
}

.upload-image-item__remove:hover {
  background: rgba(0, 0, 0, 0.72);
}

.upload-image-box__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.45);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.upload-image-box:hover .upload-image-box__overlay,
.upload-image-field:focus-within .upload-image-box__overlay {
  opacity: 1;
}

.upload-meta {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 10px;
  justify-content: space-between;
}

.upload-meta--summary {
  padding-top: 6px;
  border-top: 1px dashed var(--n-border-color);
}

.upload-name {
  color: var(--n-text-color);
  font-size: 13px;
  word-break: break-all;
}

.upload-hint {
  color: var(--n-text-color-3);
  font-size: 12px;
}

.form-actions {
  position: sticky;
  bottom: 6px;
  z-index: 1;
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
  padding: 12px 14px;
  border: 1px solid var(--n-border-color);
  border-radius: 12px;
  background: color-mix(in srgb, var(--n-card-color) 86%, #fff);
  backdrop-filter: blur(6px);
}

@media (max-width: 1024px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .submit-header {
    flex-direction: column;
  }

  .submit-header__stats {
    width: 100%;
  }

  .stat-pill {
    flex: 1;
  }

  .form-actions {
    position: static;
    padding: 10px 0 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    backdrop-filter: none;
  }

  .form-actions :deep(.n-space) {
    width: 100%;
  }

  .form-actions :deep(.n-space > .n-button) {
    flex: 1;
  }
}

@keyframes submit-fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
