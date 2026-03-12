<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue';
import { NButton, NImage, NTag } from 'naive-ui';
import type { DataTableBaseColumn, UploadCustomRequestOptions, UploadFileInfo } from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { HGS_CONTENT_KEYS, type PlayerListPreset, QGS_CONTENT_KEYS } from '@/constants/player-list';
import { fetchPlayerList, updatePlayer } from '@/service/api/player';
import { fetchProjectList } from '@/service/api/project';
import { fetchSchemaByCode } from '@/service/api/schema';
import { useAuthStore } from '@/store/modules/auth';
import { useNotificationStore } from '@/store/modules/notification';
import { formatUtc8DateTime } from '@/utils/datetime';

interface PlayerListField {
  key: string;
  label: string;
  order: number;
  type?: string;
  options?: unknown[];
  multiple?: boolean;
  required?: boolean;
  placeholder?: string;
  visible_pages?: string[];
  visible_roles?: string[];
  editable_roles?: string[];
  readonly_roles?: string[];
}

type FieldOption = { label: string; value: string | number };

type DateRangeValue = [number, number] | null;
type StaticColumnKey = 'project_id' | 'created_at' | 'actions';

const SCHEMA_CODE = 'player_form';
const QGS_AUTHOR_KEY = 'qgs_author';
const HGS_MAINTAINER_KEY = 'hgs_maintainer';
const SYSTEM_PLAYER_FIELDS: Array<Pick<Api.Schema.FormFieldDef, 'key' | 'label' | 'type' | 'required'>> = [
  { key: QGS_AUTHOR_KEY, label: 'QGS负责人', type: 'single_line_text', required: false },
  { key: HGS_MAINTAINER_KEY, label: 'HGS负责人', type: 'single_line_text', required: false }
];
const MIN_COLUMN_WIDTH = 20;
const MAX_COLUMN_WIDTH = 640;
const COLUMN_WIDTH_STORAGE_KEY_PREFIX = 'player-list-column-widths';
const UPLOAD_PREVIEW_MAX_COUNT = 10;
const DEFAULT_STATIC_COLUMN_WIDTHS: Record<StaticColumnKey, number> = {
  project_id: 60,
  created_at: 160,
  actions: 70
};

// 前端GS选项
const QGS_ROLE_OPTIONS = [
  { label: 'ADMIN', value: 'ADMIN' },
  { label: 'SUBADMIN', value: 'SUBADMIN' },
  { label: 'QGS_DIRECTOR', value: 'QGS_DIRECTOR' },
  { label: 'QGS_LEADER', value: 'QGS_LEADER' },
  { label: 'QGS_MEMBER', value: 'QGS_MEMBER' }
];

// 后端GS选项
const HGS_ROLE_OPTIONS = [
  { label: 'ADMIN', value: 'ADMIN' },
  { label: 'SUBADMIN', value: 'SUBADMIN' },
  { label: 'HGS_DIRECTOR', value: 'HGS_DIRECTOR' },
  { label: 'HGS_LEADER', value: 'HGS_LEADER' },
  { label: 'HGS_MEMBER', value: 'HGS_MEMBER' }
];

// 上传图片相关类型
interface UploadFieldValue {
  name: string;
  type: string;
  size: number;
  data_url: string;
}

const props = withDefaults(
  defineProps<{
    preset?: PlayerListPreset;
    title?: string;
  }>(),
  { preset: 'full', title: '' }
);
const columnWidthStorageKey = computed(() => `${COLUMN_WIDTH_STORAGE_KEY_PREFIX}:${props.preset}`);

const authStore = useAuthStore();
const notificationStore = useNotificationStore();
const loading = ref(false);
const tableData = ref<Api.Player.Item[]>([]);
const total = ref(0);
const pagination = reactive({ page: 1, pageSize: 50 });
const projectOptions = ref<{ label: string; value: number }[]>([]);
const projectNameById = ref<Record<number, string>>({});
const schemaFields = ref<PlayerListField[]>([]);
const schemaWarning = ref('');
const draggableFields = ref<PlayerListField[]>([]);
const savedFieldOrder = ref<string[]>([]);
const fieldColumnWidths = reactive<Record<string, number>>({});
const staticColumnWidths = reactive<Record<StaticColumnKey, number>>({ ...DEFAULT_STATIC_COLUMN_WIDTHS });
const uploadModalVisible = ref(false);
const uploadFileList = ref<UploadFileInfo[]>([]);
const selectedUploadFile = ref<File | null>(null);
const uploadPreviewModalVisible = ref(false);
const uploadPreviewUrls = ref<string[]>([]);
const uploadPreviewTitle = ref('上传预览');
const editModalVisible = ref(false);
const editSubmitting = ref(false);
const editingRow = ref<Api.Player.Item | null>(null);
const editProjectId = ref<number | null>(null);
const editFields = ref<PlayerListField[]>([]);
const editContentDraft = reactive<Record<string, unknown>>({});

// 编辑弹窗中上传图片相关状态
const editUploadInputRefs = ref<Record<string, HTMLInputElement | null>>({});
const activeEditUploadImageFieldKey = ref<string | null>(null);
const visiblePageKey = computed(() => {
  if (props.preset === 'qgs') return 'qgs/list';
  if (props.preset === 'hgs') return 'hgs/list';
  return '';
});
const currentUserRoles = computed(() => normalizeRoleList(authStore.userInfo?.roles));

function isStaticColumnKey(key: string): key is StaticColumnKey {
  return key === 'project_id' || key === 'created_at' || key === 'actions';
}

function applyClaimedMaintainer(payload: {
  player_id?: number;
  claimer?: { alias?: string };
} | null) {
  if (!payload?.player_id) return;
  const alias = (payload.claimer?.alias || '').trim();
  if (!alias) return;

  const index = tableData.value.findIndex(row => row.id === payload.player_id);
  if (index < 0) return;

  const row = tableData.value[index];
  const nextContent = { ...(row.content || {}) };
  const existing = nextContent[HGS_MAINTAINER_KEY];
  if (typeof existing === 'string' && existing.trim()) return;

  nextContent[HGS_MAINTAINER_KEY] = alias;
  tableData.value = [
    ...tableData.value.slice(0, index),
    { ...row, content: nextContent },
    ...tableData.value.slice(index + 1)
  ];
}

const searchModel = reactive({
  dateRange: null as DateRangeValue,
  alias: '',
  projectId: null as number | null,
  playerId: '',
  server: '',
  keyword: ''
});

function normalizeFieldType(type?: string) {
  const val = (type || 'single_line_text').trim().toLowerCase();
  if (['single_line_text', 'string', 'text', 'input'].includes(val)) return 'single_line_text';
  if (['multi_line_text', 'textarea', 'multiline'].includes(val)) return 'multi_line_text';
  if (['number', 'int', 'float', 'decimal'].includes(val)) return 'number';
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

function normalizeColumnWidth(width: number | null | undefined, fallback: number) {
  const candidate = typeof width === 'number' ? width : fallback;
  if (!Number.isFinite(candidate)) return fallback;
  return Math.min(MAX_COLUMN_WIDTH, Math.max(MIN_COLUMN_WIDTH, Math.round(candidate)));
}

function persistColumnWidths() {
  if (typeof window === 'undefined') return;

  const payload = {
    staticColumnWidths: { ...staticColumnWidths },
    fieldColumnWidths: { ...fieldColumnWidths },
    fieldOrder: [...savedFieldOrder.value]
  };

  window.localStorage.setItem(columnWidthStorageKey.value, JSON.stringify(payload));
}

function restoreColumnWidths() {
  if (typeof window === 'undefined') return;

  const raw = window.localStorage.getItem(columnWidthStorageKey.value);
  if (!raw) return;

  try {
    const parsed = JSON.parse(raw) as {
      staticColumnWidths?: Record<string, unknown>;
      fieldColumnWidths?: Record<string, unknown>;
      fieldOrder?: unknown;
    };

    const nextStatic = parsed.staticColumnWidths || {};
    (Object.keys(DEFAULT_STATIC_COLUMN_WIDTHS) as StaticColumnKey[]).forEach(key => {
      const restored = nextStatic[key];
      const width = typeof restored === 'number' ? restored : null;
      staticColumnWidths[key] = normalizeColumnWidth(width, DEFAULT_STATIC_COLUMN_WIDTHS[key]);
    });

    const nextFields = parsed.fieldColumnWidths || {};
    Object.keys(nextFields).forEach(key => {
      const restored = nextFields[key];
      if (typeof restored !== 'number') return;
      fieldColumnWidths[key] = normalizeColumnWidth(restored, 180);
    });

    const nextOrder = Array.isArray(parsed.fieldOrder) ? parsed.fieldOrder : [];
    const seen = new Set<string>();
    savedFieldOrder.value = nextOrder
      .map(item => String(item || '').trim())
      .filter(key => {
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      });
  } catch {
    window.localStorage.removeItem(columnWidthStorageKey.value);
  }
}

function estimateFieldColumnWidth(label: string) {
  return Math.max(96, Math.min(320, label.length * 14 + 48));
}

function isProjectField(field: Api.Schema.FormFieldDef) {
  const normalizedType = normalizeFieldType(field.type);
  const key = (field.key || '').trim().toLowerCase();
  return normalizedType === 'project' || key === 'project' || key === 'project_id' || key === 'projectid';
}

function isListBuiltInSchemaField(field: Api.Schema.FormFieldDef) {
  const key = (field.key || '').trim().toLowerCase();
  return key === 'created_at' || key === 'actions';
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
  if (!pageKey) return true;
  const visiblePages = normalizeVisiblePages(field.visible_pages);
  if (visiblePages.length === 0) return true;
  return visiblePages.includes(pageKey);
}

function normalizeRoleList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  const seen = new Set<string>();
  const normalized: string[] = [];
  value.forEach(item => {
    const role = String(item || '')
      .trim()
      .toLowerCase();
    if (!role || seen.has(role)) return;
    seen.add(role);
    normalized.push(role);
  });
  return normalized;
}

function hasAnyMatchedRole(userRoles: string[], targetRoles: string[]) {
  if (userRoles.length === 0 || targetRoles.length === 0) return false;
  return userRoles.some(role => targetRoles.includes(role));
}

function isFieldVisibleForRoles(field: { visible_roles?: string[] }, userRoles: string[]) {
  const visibleRoles = normalizeRoleList(field.visible_roles);
  if (visibleRoles.length === 0) return true;
  return hasAnyMatchedRole(userRoles, visibleRoles);
}

function isFieldVisibleForCurrentUser(field: { visible_roles?: string[] }) {
  return isFieldVisibleForRoles(field, currentUserRoles.value);
}

function isFieldEditableForRoles(
  field: Pick<PlayerListField, 'editable_roles' | 'readonly_roles'>,
  userRoles: string[]
) {
  const readonlyRoles = normalizeRoleList(field.readonly_roles);
  if (hasAnyMatchedRole(userRoles, readonlyRoles)) {
    return false;
  }

  const editableRoles = normalizeRoleList(field.editable_roles);
  if (editableRoles.length === 0) {
    return true;
  }

  return hasAnyMatchedRole(userRoles, editableRoles);
}

function isEditFieldReadonly(field: PlayerListField) {
  return !isFieldEditableForRoles(field, currentUserRoles.value);
}

function ensureSystemPlayerFields(fields: Api.Schema.FormFieldDef[] | undefined): Api.Schema.FormFieldDef[] {
  const source = Array.isArray(fields) ? [...fields] : [];
  const existingKeys = new Set(
    source.map(item => (typeof item?.key === 'string' ? item.key.trim() : '')).filter(Boolean)
  );
  const maxOrder = source.reduce((max, field, index) => {
    const order = typeof field.order === 'number' ? field.order : index;
    return Math.max(max, order);
  }, -1);

  let nextOrder = maxOrder + 1;
  SYSTEM_PLAYER_FIELDS.forEach(field => {
    const key = field.key?.trim();
    if (!key || existingKeys.has(key)) return;
    source.push({
      key,
      label: field.label,
      type: field.type,
      required: field.required,
      order: nextOrder
    });
    existingKeys.add(key);
    nextOrder += 1;
  });

  return source;
}

function normalizeSchemaFields(fields: Api.Schema.FormFieldDef[] | undefined, pageKey: string): PlayerListField[] {
  return ensureSystemPlayerFields(fields)
    .filter((field): field is Api.Schema.FormFieldDef & { key: string } => {
      if (typeof field?.key !== 'string' || !field.key.trim()) return false;
      return !isProjectField(field) && !isListBuiltInSchemaField(field) && isFieldVisibleForPage(field, pageKey);
    })
    .map(field => ({
      key: field.key.trim(),
      label: (field.label || field.key).trim(),
      order: typeof field.order === 'number' ? field.order : 0,
      type: normalizeFieldType(field.type),
      options: Array.isArray(field.options) ? field.options : undefined,
      multiple: Boolean((field as { multiple?: unknown }).multiple),
      required: Boolean(field.required),
      visible_pages: Array.isArray(field.visible_pages) ? [...field.visible_pages] : undefined,
      visible_roles: Array.isArray(field.visible_roles) ? [...field.visible_roles] : undefined,
      editable_roles: Array.isArray(field.editable_roles) ? [...field.editable_roles] : undefined,
      readonly_roles: Array.isArray(field.readonly_roles) ? [...field.readonly_roles] : undefined,
      placeholder:
        typeof (field as { placeholder?: unknown }).placeholder === 'string'
          ? ((field as { placeholder?: string }).placeholder || '').trim()
          : undefined
    }))
    .sort((a, b) => a.order - b.order);
}

async function loadProjects() {
  const { data, error } = await fetchProjectList({ page: 1, page_size: 100 });
  const projects = !error && Array.isArray(data?.items) ? data.items : [];
  projectNameById.value = projects.reduce<Record<number, string>>((acc, project) => {
    acc[project.id] = project.name;
    return acc;
  }, {});
  projectOptions.value = projects.map(p => ({
    label: p.name,
    value: p.id
  }));
}

async function loadSchema() {
  schemaWarning.value = '';

  try {
    const { data, error } = await fetchSchemaByCode(SCHEMA_CODE);
    if (error || !data) {
      schemaFields.value = [];
      schemaWarning.value = `未找到表单配置：${SCHEMA_CODE}`;
      return;
    }

    schemaFields.value = normalizeSchemaFields(data.fields, visiblePageKey.value);
  } catch {
    schemaFields.value = [];
    schemaWarning.value = `加载表单配置失败：${SCHEMA_CODE}`;
  }
}

const dataContentKeys = computed(() => {
  const keys = new Set<string>();
  tableData.value.forEach(row => {
    Object.keys(row.content || {}).forEach(key => {
      if (key) keys.add(key);
    });
  });
  return Array.from(keys);
});

const schemaFieldMap = computed(() => {
  const map = new Map<string, PlayerListField>();
  schemaFields.value.forEach(field => map.set(field.key, field));
  return map;
});

const sourceContentFields = computed<PlayerListField[]>(() => {
  if (schemaFields.value.length > 0) {
    return [...schemaFields.value];
  }

  if (props.preset === 'full') {
    const merged = [...schemaFields.value];
    const existing = new Set(merged.map(field => field.key));
    dataContentKeys.value.forEach(key => {
      if (!existing.has(key)) {
        merged.push({ key, label: key, order: Number.MAX_SAFE_INTEGER });
      }
    });
    return merged;
  }

  const presetKeys = props.preset === 'qgs' ? QGS_CONTENT_KEYS : HGS_CONTENT_KEYS;
  const fromPreset = presetKeys
    .map(
      key =>
        schemaFieldMap.value.get(key) ||
        (dataContentKeys.value.includes(key) ? { key, label: key, order: 0, type: undefined } : null)
    )
    .filter((field): field is PlayerListField => Boolean(field));

  if (fromPreset.length > 0) return fromPreset;
  if (schemaFields.value.length > 0) return schemaFields.value;

  return dataContentKeys.value.map(key => ({ key, label: key, order: 0, type: undefined }));
});

const contentFields = computed(() => draggableFields.value.filter(field => isFieldVisibleForCurrentUser(field)));

const editModalTitle = computed(() => {
  if (!editingRow.value) return '修改信息';
  return '修改信息';
});

restoreColumnWidths();

watch(visiblePageKey, () => {
  loadSchema();
});

watch(
  () => notificationStore.lastClaimed,
  payload => {
    applyClaimedMaintainer(payload);
  }
);

watch(
  sourceContentFields,
  nextFields => {
    const nextMap = new Map(nextFields.map(field => [field.key, field]));
    const merged: PlayerListField[] = [];
    const preferredOrderKeys =
      draggableFields.value.length > 0 ? draggableFields.value.map(field => field.key) : savedFieldOrder.value;

    preferredOrderKeys.forEach(key => {
      const nextField = nextMap.get(key);
      if (!nextField) return;
      merged.push(nextField);
      nextMap.delete(key);
    });

    nextFields.forEach(field => {
      if (!nextMap.has(field.key)) return;
      merged.push(field);
      nextMap.delete(field.key);
    });

    draggableFields.value = merged;
    if (merged.length > 0) {
      savedFieldOrder.value = merged.map(field => field.key);
    }

    if (merged.length > 0) {
      const fieldKeySet = new Set(merged.map(field => field.key));
      Object.keys(fieldColumnWidths).forEach(key => {
        if (!fieldKeySet.has(key)) {
          Reflect.deleteProperty(fieldColumnWidths, key);
        }
      });

      merged.forEach(field => {
        fieldColumnWidths[field.key] = normalizeColumnWidth(
          fieldColumnWidths[field.key],
          estimateFieldColumnWidth(field.label)
        );
      });
    }

    persistColumnWidths();
  },
  { immediate: true }
);

watch(
  () => draggableFields.value.map(field => field.key),
  fieldOrder => {
    if (fieldOrder.length === 0) return;
    savedFieldOrder.value = [...fieldOrder];
    persistColumnWidths();
  }
);

function formatCellValue(value: unknown) {
  if (value === null || value === undefined || value === '') return '-';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return '-';
    }
  }
  return String(value);
}

function getFieldColumnWidth(field: PlayerListField) {
  return normalizeColumnWidth(fieldColumnWidths[field.key], estimateFieldColumnWidth(field.label));
}

function updateFieldColumnWidth(fieldKey: string, width: number | null) {
  const field = draggableFields.value.find(item => item.key === fieldKey);
  const fallback = field ? estimateFieldColumnWidth(field.label) : 180;
  fieldColumnWidths[fieldKey] = normalizeColumnWidth(width, fallback);
  persistColumnWidths();
}

function updateStaticColumnWidth(key: StaticColumnKey, width: number | null) {
  staticColumnWidths[key] = normalizeColumnWidth(width, DEFAULT_STATIC_COLUMN_WIDTHS[key]);
  persistColumnWidths();
}

function resetColumnWidths() {
  updateStaticColumnWidth('project_id', DEFAULT_STATIC_COLUMN_WIDTHS.project_id);
  updateStaticColumnWidth('created_at', DEFAULT_STATIC_COLUMN_WIDTHS.created_at);
  updateStaticColumnWidth('actions', DEFAULT_STATIC_COLUMN_WIDTHS.actions);
  draggableFields.value.forEach(field => {
    fieldColumnWidths[field.key] = estimateFieldColumnWidth(field.label);
  });
  persistColumnWidths();
}

function isDataImageUrl(url: string) {
  return /^data:image\//i.test(url);
}

function isHttpUrl(url: string) {
  return /^https?:\/\//i.test(url);
}

function hasImageExtension(url: string) {
  return /\.(png|jpe?g|gif|webp|bmp|svg)(\?.*)?$/i.test(url);
}

function collectUrlCandidates(value: unknown, collector: Set<string>) {
  if (typeof value === 'string') {
    const url = value.trim();
    if (url) collector.add(url);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach(item => collectUrlCandidates(item, collector));
    return;
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    ['data_url', 'url', 'src', 'image', 'thumbnail', 'thumb', 'value'].forEach(key => {
      if (key in record) collectUrlCandidates(record[key], collector);
    });
  }
}

function isLikelyImageField(field: PlayerListField) {
  const normalizedType = normalizeFieldType(field.type);
  if (normalizedType === 'upload_image') return true;
  return /(screenshot|screen|image|img|pic|photo|avatar|thumb|cover)/i.test(field.key);
}

function isUploadField(field: PlayerListField) {
  const normalizedType = normalizeFieldType(field.type);
  return normalizedType === 'upload_image' || normalizedType === 'upload_attachment';
}

function resolveThumbnailUrls(field: PlayerListField, value: unknown) {
  const candidates = new Set<string>();
  collectUrlCandidates(value, candidates);
  const allowAnyHttp = isLikelyImageField(field);
  const urls = Array.from(candidates).filter(url => {
    if (isDataImageUrl(url)) return true;
    if (hasImageExtension(url)) return true;
    return allowAnyHttp && isHttpUrl(url);
  });
  return urls.slice(0, UPLOAD_PREVIEW_MAX_COUNT);
}

function renderContentCell(field: PlayerListField, row: Api.Player.Item) {
  const value = (row.content || {})[field.key];

  if (normalizeFieldType(field.type) === 'color') {
    if (!value) return '-';

    if (field.options && Array.isArray(field.options)) {
      const matchedOption = field.options.find(opt => {
        if (typeof opt === 'object' && opt !== null) {
          return (opt as any).value === value || (opt as any).label === value;
        }
        return opt === value;
      });

      if (matchedOption && typeof matchedOption === 'object' && (matchedOption as any).color) {
        return h(
          NTag,
          {
            type: 'info',
            size: 'small',
            color: { color: (matchedOption as any).color, textColor: '#fff' }
          },
          { default: () => String((matchedOption as any).label || value) }
        );
      }
    }

    const colorValue = String(value);
    return h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } }, [
      h('div', {
        style: {
          width: '20px',
          height: '20px',
          borderRadius: '4px',
          backgroundColor: colorValue,
          border: '1px solid #d9d9d9'
        }
      }),
      h('span', { style: { fontSize: '12px' } }, colorValue)
    ]);
  }

  if (field.options && Array.isArray(field.options)) {
    const values = Array.isArray(value) ? value : [value];
    const tags: Array<{ label: string; color?: string }> = [];
    values.forEach(val => {
      if (!val) return;
      const option = field.options!.find(opt => {
        if (typeof opt === 'object' && opt !== null) {
          return (opt as any).value === val || (opt as any).label === val;
        }
        return opt === val;
      });
      if (!option) return;

      const label = typeof option === 'object' ? (option as any).label || (option as any).value : option;
      const color = typeof option === 'object' ? (option as any).color : undefined;
      tags.push({ label: String(label), color: typeof color === 'string' ? color : undefined });
    });

    if (tags.length > 0 && tags.some(t => t.color)) {
      return h(
        'div',
        { style: { display: 'flex', gap: '4px', flexWrap: 'wrap' } },
        tags.map((tag, idx) =>
          h(
            NTag,
            {
              key: idx,
              type: 'info',
              size: 'small',
              ...(tag.color ? { color: { color: tag.color, textColor: '#fff' } } : {})
            },
            { default: () => tag.label }
          )
        )
      );
    }
  }

  const urls = resolveThumbnailUrls(field, value);
  if (isUploadField(field)) {
    if (!urls.length) return formatCellValue(value);

    return h(
      NButton,
      {
        size: 'small',
        type: 'primary',
        text: true,
        onClick: () => openUploadPreview(field, value)
      },
      { default: () => '查看预览' }
    );
  }

  if (!urls.length) return formatCellValue(value);

  return h(
    'div',
    { class: 'thumb-grid' },
    urls.map((url, index) =>
      h(NImage, {
        src: url,
        width: 40,
        height: 40,
        objectFit: 'cover',
        alt: `${field.key}-${index + 1}`
      })
    )
  );
}
function openUploadPreview(field: PlayerListField, value: unknown) {
  uploadPreviewUrls.value = resolveThumbnailUrls(field, value);
  uploadPreviewTitle.value = `${field.label}预览`;
  uploadPreviewModalVisible.value = true;
}

function closeUploadPreview() {
  uploadPreviewModalVisible.value = false;
}

function parseBooleanValue(raw: string): boolean | undefined {
  const normalized = raw.trim().toLowerCase();
  if (['true', '1', 'yes', 'y'].includes(normalized)) return true;
  if (['false', '0', 'no', 'n'].includes(normalized)) return false;
  return undefined;
}

function toFieldOptions(options: unknown): FieldOption[] {
  if (!Array.isArray(options)) return [];
  const result: FieldOption[] = [];
  options.forEach(item => {
    if (item === null || item === undefined) return;
    if (typeof item === 'object') {
      const option = item as Record<string, unknown>;
      const rawValue = option.value ?? option.id ?? option.key;
      if (rawValue === null || rawValue === undefined) return;
      if (typeof rawValue !== 'string' && typeof rawValue !== 'number') return;
      const rawLabel = option.label ?? option.name ?? rawValue;
      result.push({ label: String(rawLabel), value: rawValue });
      return;
    }
    if (typeof item === 'string' || typeof item === 'number') {
      result.push({ label: String(item), value: item });
    }
  });
  return result;
}

function isEditTextareaField(field: PlayerListField) {
  return normalizeFieldType(field.type) === 'multi_line_text';
}

function isEditNumberField(field: PlayerListField) {
  return normalizeFieldType(field.type) === 'number';
}

function isEditDatetimeField(field: PlayerListField) {
  return normalizeFieldType(field.type) === 'datetime';
}

function isEditColorField(field: PlayerListField) {
  return normalizeFieldType(field.type) === 'color';
}

function isEditSwitchField(field: PlayerListField) {
  return normalizeFieldType(field.type) === 'switch';
}

function isEditRadioField(field: PlayerListField) {
  return normalizeFieldType(field.type) === 'radio';
}

function isEditCheckboxField(field: PlayerListField) {
  return normalizeFieldType(field.type) === 'checkbox';
}

function isEditSelectField(field: PlayerListField) {
  return normalizeFieldType(field.type) === 'select' || normalizeFieldType(field.type) === 'select_multiple';
}

function isEditMultipleField(field: PlayerListField) {
  const type = normalizeFieldType(field.type);
  return type === 'checkbox' || type === 'select_multiple' || (type === 'select' && Boolean(field.multiple));
}

function getEditFieldPlaceholder(field: PlayerListField) {
  if (field.placeholder) return field.placeholder;
  const type = normalizeFieldType(field.type);
  const prefix = ['select', 'select_multiple', 'radio', 'checkbox', 'datetime', 'color', 'switch'].includes(type)
    ? '请选择'
    : '请输入';
  return `${prefix}${field.label}`;
}

function toPrimitiveValue(value: unknown): string | number | undefined {
  if (typeof value === 'string' || typeof value === 'number') return value;
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const rawValue = record.value ?? record.id;
    if (typeof rawValue === 'string' || typeof rawValue === 'number') return rawValue;
  }
  return undefined;
}

function toArrayValue(value: unknown): Array<string | number> {
  if (!Array.isArray(value)) return [];
  return value.map(item => toPrimitiveValue(item)).filter((item): item is string | number => item !== undefined);
}

function toTextValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return '';
  }
}

function toNumberValue(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (value === null || value === undefined || value === '') return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function toDatetimeValue(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (value === null || value === undefined || value === '') return undefined;
  const timestamp = new Date(String(value)).getTime();
  return Number.isFinite(timestamp) ? timestamp : undefined;
}

function toEditDraftValue(field: PlayerListField, value: unknown): unknown {
  if (isEditNumberField(field)) return toNumberValue(value);
  if (isEditDatetimeField(field)) return toDatetimeValue(value);
  if (isEditSwitchField(field)) {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'string') return parseBooleanValue(value) ?? false;
    return Boolean(value);
  }
  if (isEditMultipleField(field)) {
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);
        return toArrayValue(parsed);
      } catch {
        return value
          .split(',')
          .map(item => item.trim())
          .filter(Boolean);
      }
    }
    return toArrayValue(value);
  }
  if (isEditSelectField(field) || isEditRadioField(field)) {
    const primitive = toPrimitiveValue(value);
    return primitive ?? undefined;
  }
  return toTextValue(value);
}

function getEditStringValue(key: string) {
  return toTextValue(editContentDraft[key]);
}

function setEditStringValue(key: string, value: string | null) {
  editContentDraft[key] = value ?? '';
}

function getEditNumberValue(key: string) {
  return toNumberValue(editContentDraft[key]);
}

function setEditNumberValue(key: string, value: number | null) {
  editContentDraft[key] = value ?? undefined;
}

function getEditDatetimeValue(key: string) {
  return toDatetimeValue(editContentDraft[key]);
}

function setEditDatetimeValue(key: string, value: number | null) {
  editContentDraft[key] = value ?? undefined;
}

function getEditSelectValue(key: string): string | number | Array<string | number> | undefined {
  const value = editContentDraft[key];
  if (typeof value === 'string' || typeof value === 'number') return value;
  if (Array.isArray(value)) return toArrayValue(value);
  return undefined;
}

function setEditSelectValue(key: string, value: string | number | Array<string | number> | null) {
  if (Array.isArray(value)) {
    editContentDraft[key] = toArrayValue(value);
    return;
  }
  editContentDraft[key] = value ?? undefined;
}

function getEditRadioValue(key: string): string | number | undefined {
  return toPrimitiveValue(editContentDraft[key]);
}

function setEditRadioValue(key: string, value: string | number | null) {
  editContentDraft[key] = value ?? undefined;
}

function getEditCheckboxValue(key: string): Array<string | number> {
  return toArrayValue(editContentDraft[key]);
}

function setEditCheckboxValue(key: string, value: Array<string | number> | null) {
  editContentDraft[key] = value ? toArrayValue(value) : [];
}

function getEditSwitchValue(key: string): boolean {
  return Boolean(editContentDraft[key]);
}

function setEditSwitchValue(key: string, value: string | number | boolean) {
  editContentDraft[key] = Boolean(value);
}

function getEditColorValue(key: string): string | undefined {
  const value = editContentDraft[key];
  if (typeof value !== 'string') return undefined;
  const color = value.trim();
  return color || undefined;
}

function setEditColorValue(key: string, value: string | null) {
  editContentDraft[key] = value?.trim() || '';
}

function parseNumberEditValue(rawValue: unknown): unknown {
  if (rawValue === null || rawValue === undefined || rawValue === '') return '';
  const parsed = toNumberValue(rawValue);
  return parsed ?? rawValue;
}

function parseSwitchEditValue(rawValue: unknown): boolean {
  if (typeof rawValue === 'boolean') return rawValue;
  const boolValue = parseBooleanValue(toTextValue(rawValue));
  return boolValue ?? Boolean(rawValue);
}

function parseDatetimeEditValue(rawValue: unknown): string {
  const timestamp = toDatetimeValue(rawValue);
  if (timestamp === undefined) return '';
  return new Date(timestamp).toISOString();
}

function parseMultipleEditValue(rawValue: unknown): Array<string | number> {
  if (Array.isArray(rawValue)) return toArrayValue(rawValue);
  if (typeof rawValue !== 'string') return [];
  const trimmed = rawValue.trim();
  if (!trimmed) return [];
  try {
    const parsed = JSON.parse(trimmed);
    return Array.isArray(parsed) ? toArrayValue(parsed) : [];
  } catch {
    return trimmed
      .split(',')
      .map(item => item.trim())
      .filter(Boolean);
  }
}

function parseStructuredStringEditValue(rawValue: string): unknown {
  const trimmed = rawValue.trim();
  if (!trimmed) return '';
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return rawValue;
    }
  }
  return rawValue;
}

function parseEditValue(field: PlayerListField, rawValue: unknown, originalValue: unknown): unknown {
  const normalizedType = normalizeFieldType(field.type);

  if (normalizedType === 'number' || typeof originalValue === 'number') {
    return parseNumberEditValue(rawValue);
  }

  if (normalizedType === 'switch' || typeof originalValue === 'boolean') {
    return parseSwitchEditValue(rawValue);
  }

  if (normalizedType === 'datetime') {
    return parseDatetimeEditValue(rawValue);
  }

  if (isEditMultipleField(field) || Array.isArray(originalValue)) {
    return parseMultipleEditValue(rawValue);
  }

  if (normalizedType === 'radio' || normalizedType === 'select') {
    const value = toPrimitiveValue(rawValue);
    return value ?? '';
  }

  if (typeof rawValue !== 'string') return rawValue === null || rawValue === undefined ? '' : rawValue;
  return parseStructuredStringEditValue(rawValue);
}

function buildEditFields() {
  const currentPageKey = visiblePageKey.value;
  return draggableFields.value.filter(field => {
    if (!isFieldVisibleForCurrentUser(field)) return false;
    const key = field.key.toLowerCase();
    if (key === 'created_at' || key === 'actions') {
      return false;
    }
    const pages = normalizeVisiblePages(field.visible_pages);
    if (pages.length === 0 || pages.includes('edit')) return true;
    return currentPageKey ? pages.includes(currentPageKey) : false;
  });
}

function handleColumnResize(resizedWidth: number, limitedWidth: number, column: DataTableBaseColumn) {
  const key = typeof column.key === 'string' ? column.key : '';
  if (!key) return;

  const fallback = typeof column.width === 'number' ? column.width : 180;
  const width = normalizeColumnWidth(limitedWidth || resizedWidth, fallback);

  if (isStaticColumnKey(key)) {
    updateStaticColumnWidth(key, width);
    return;
  }

  if (!key.startsWith('content.')) return;

  const fieldKey = key.slice('content.'.length);
  if (!fieldKey) return;
  updateFieldColumnWidth(fieldKey, width);
}

function clearEditState() {
  editingRow.value = null;
  editProjectId.value = null;
  editFields.value = [];
  Object.keys(editContentDraft).forEach(key => Reflect.deleteProperty(editContentDraft, key));
}

function openEditModal(row: Api.Player.Item) {
  editingRow.value = row;
  editProjectId.value = row.project_id;
  editFields.value = buildEditFields();
  Object.keys(editContentDraft).forEach(key => Reflect.deleteProperty(editContentDraft, key));

  const content = row.content || {};
  editFields.value.forEach(field => {
    editContentDraft[field.key] = toEditDraftValue(field, content[field.key]);
  });

  editModalVisible.value = true;
}

function closeEditModal() {
  editModalVisible.value = false;
}

async function submitEditModal() {
  if (!editingRow.value) return;

  const projectId = editProjectId.value;
  if (!projectId) {
    window.$message?.warning('请选择项目。');
    return;
  }

  const currentContent = editingRow.value.content || {};
  const nextContent: Record<string, unknown> = { ...currentContent };
  editFields.value.forEach(field => {
    if (isEditFieldReadonly(field)) {
      nextContent[field.key] = currentContent[field.key];
      return;
    }
    nextContent[field.key] = parseEditValue(field, editContentDraft[field.key], currentContent[field.key]);
  });

  editSubmitting.value = true;
  try {
    const { error } = await updatePlayer(editingRow.value.id, {
      project_id: projectId,
      content: nextContent
    });
    if (error) return;

    window.$message?.success('保存成功。');
    closeEditModal();
    await loadData();
  } finally {
    editSubmitting.value = false;
  }
}

const columns = computed<DataTableBaseColumn<Api.Player.Item>[]>(() => {
  const cols: DataTableBaseColumn<Api.Player.Item>[] = [
    {
      title: '项目',
      key: 'project_id',
      width: staticColumnWidths.project_id,
      minWidth: MIN_COLUMN_WIDTH,
      resizable: true,
      render: row => projectNameById.value[row.project_id] || `#${row.project_id}`
    },
    {
      title: '提交时间',
      key: 'created_at',
      width: staticColumnWidths.created_at,
      minWidth: MIN_COLUMN_WIDTH,
      resizable: true,
      render: row => formatUtc8DateTime(row.created_at)
    }
  ];

  contentFields.value.forEach(field => {
    cols.push({
      title: field.label,
      key: `content.${field.key}`,
      width: getFieldColumnWidth(field),
      minWidth: MIN_COLUMN_WIDTH,
      resizable: true,
      ellipsis: { tooltip: true },
      render: row => renderContentCell(field, row)
    });
  });

  cols.push({
    title: '操作',
    key: 'actions',
    width: staticColumnWidths.actions,
    minWidth: MIN_COLUMN_WIDTH,
    resizable: true,
    render: row =>
      h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          ghost: true,
          onClick: () => openEditModal(row)
        },
        { default: () => '编辑' }
      )
  });

  return cols;
});

const tableScrollX = computed(() => {
  const totalWidth = columns.value.reduce((sum, column) => {
    return sum + (typeof column.width === 'number' ? column.width : 180);
  }, 0);
  return totalWidth;
});

const cardTitle = computed(() => {
  if (props.title) return props.title;
  if (props.preset === 'qgs') return 'QGS玩家列表';
  if (props.preset === 'hgs') return 'HGS玩家列表';
  return '玩家列表';
});

function normalizePlayerId(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function normalizeDateRange(range: DateRangeValue) {
  if (!range || range.length !== 2) {
    return { startTime: undefined as string | undefined, endTime: undefined as string | undefined };
  }

  const [startValue, endValue] = range;
  const start = new Date(startValue);
  start.setHours(0, 0, 0, 0);

  const end = new Date(endValue);
  end.setHours(23, 59, 59, 999);

  return { startTime: start.toISOString(), endTime: end.toISOString() };
}

async function loadData() {
  loading.value = true;
  try {
    const { startTime, endTime } = normalizeDateRange(searchModel.dateRange);
    const { data, error } = await fetchPlayerList({
      page: pagination.page,
      page_size: pagination.pageSize,
      project_id: searchModel.projectId ?? undefined,
      player_id: normalizePlayerId(searchModel.playerId),
      alias: searchModel.alias.trim() || undefined,
      server: searchModel.server.trim() || undefined,
      keyword: searchModel.keyword.trim() || undefined,
      start_time: startTime,
      end_time: endTime
    });
    tableData.value = !error && Array.isArray(data?.items) ? data.items : [];
    total.value = !error && typeof data?.total === 'number' ? data.total : 0;
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  pagination.page = 1;
  loadData();
}

function onReset() {
  searchModel.dateRange = null;
  searchModel.alias = '';
  searchModel.projectId = null;
  searchModel.playerId = '';
  searchModel.server = '';
  searchModel.keyword = '';
  onSearch();
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

function getPlayerRowKey(row: Api.Player.Item) {
  return row.id;
}

function resetFieldOrder() {
  draggableFields.value = [...sourceContentFields.value];
}

function openUploadModal() {
  uploadModalVisible.value = true;
}

function clearUploadFile() {
  uploadFileList.value = [];
  selectedUploadFile.value = null;
}

function closeUploadModal() {
  uploadModalVisible.value = false;
}

watch(uploadModalVisible, visible => {
  if (!visible) clearUploadFile();
});

watch(uploadPreviewModalVisible, visible => {
  if (visible) return;
  uploadPreviewUrls.value = [];
  uploadPreviewTitle.value = '上传预览';
});

watch(editModalVisible, visible => {
  if (!visible) {
    clearEditState();
    activeEditUploadImageFieldKey.value = null;
  }
});

function handleUploadFile(options: UploadCustomRequestOptions) {
  const rawFile = options.file.file;
  if (!(rawFile instanceof File)) {
    options.onError();
    return;
  }

  selectedUploadFile.value = rawFile;
  options.onFinish();
}

function handleUploadRemove() {
  selectedUploadFile.value = null;
  return true;
}

function downloadImportTemplate() {
  const fixedFields = ['project_id', 'player_id', 'alias', 'server'];
  const dynamicFields = contentFields.value.map(field => field.key);
  const headers = Array.from(new Set([...fixedFields, ...dynamicFields]));
  const sampleRow = headers.map(key => (key === 'project_id' ? '1' : '')).join(',');
  const csvContent = `\uFEFF${headers.join(',')}\n${sampleRow}\n`;

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = '玩家导入模板.csv';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

function confirmUploadFile() {
  if (!selectedUploadFile.value) {
    window.$message?.warning('请先选择文件。');
    return;
  }

  window.$message?.info(`已选择文件：${selectedUploadFile.value.name}。批量上传接口暂未接入。`);
  closeUploadModal();
}

// ========== 编辑弹窗中上传图片相关函数 ==========

function setEditUploadInputRef(key: string, el: HTMLInputElement | null) {
  editUploadInputRefs.value[key] = el;
}

function setActiveEditUploadImageField(field: PlayerListField) {
  if (normalizeFieldType(field.type) === 'upload_image') {
    activeEditUploadImageFieldKey.value = field.key;
  }
}

function isEditUploadImageField(field: PlayerListField): boolean {
  return normalizeFieldType(field.type) === 'upload_image';
}

function normalizeEditUploadValue(value: unknown): UploadFieldValue[] {
  if (value === null || value === undefined) return [];

  if (typeof value === 'string') {
    const url = value.trim();
    if (!url) return [];
    return [{ name: 'uploaded-file', type: '', size: 0, data_url: url }];
  }

  if (Array.isArray(value)) {
    return value
      .map(item => normalizeEditUploadValue(item))
      .flat()
      .slice(0, UPLOAD_PREVIEW_MAX_COUNT);
  }

  if (typeof value === 'object') {
    const data = value as Record<string, unknown>;
    const dataUrl = data.data_url ?? data.url;
    if (typeof dataUrl === 'string' && dataUrl.trim()) {
      return [{
        name: typeof data.name === 'string' && data.name.trim() ? data.name.trim() : 'uploaded-file',
        type: typeof data.type === 'string' ? data.type : '',
        size: typeof data.size === 'number' && Number.isFinite(data.size) ? data.size : 0,
        data_url: dataUrl.trim()
      }];
    }
  }

  return [];
}

function getEditUploadValues(key: string): UploadFieldValue[] {
  return normalizeEditUploadValue(editContentDraft[key]);
}

function toUploadFieldValue(file: File): Promise<UploadFieldValue | null> {
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = e => {
      const dataUrl = e.target?.result as string;
      resolve({
        name: file.name,
        type: file.type,
        size: file.size,
        data_url: dataUrl
      });
    };
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });
}

async function appendEditUploadFiles(field: PlayerListField, files: File[]) {
  const current = getEditUploadValues(field.key);
  const remain = UPLOAD_PREVIEW_MAX_COUNT - current.length;
  const selectedFiles = files.slice(0, remain);
  if (files.length > remain) {
    window.$message?.warning(`最多可上传 ${UPLOAD_PREVIEW_MAX_COUNT} 个文件`);
  }

  const resolvedUploads = await Promise.all(selectedFiles.map(file => toUploadFieldValue(file)));
  const nextUploads = resolvedUploads.filter((item): item is UploadFieldValue => Boolean(item));
  const next = [...current, ...nextUploads];

  editContentDraft[field.key] = next;
}

async function onEditUploadInputChange(field: PlayerListField, event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  if (!files.length) {
    input.value = '';
    return;
  }

  await appendEditUploadFiles(field, files);
  input.value = '';
}

function removeEditUploadValue(fieldKey: string, index: number) {
  const current = getEditUploadValues(fieldKey);
  current.splice(index, 1);
  editContentDraft[fieldKey] = [...current];
}

function clearEditUploadValue(fieldKey: string) {
  editContentDraft[fieldKey] = [];
}

function pickEditUploadFile(field: PlayerListField) {
  const input = editUploadInputRefs.value[field.key];
  if (input) {
    input.click();
  }
}

function getClipboardImageFile(event: ClipboardEvent): File | null {
  const clipboardData = event.clipboardData;
  if (!clipboardData) return null;

  const items = clipboardData.items;
  if (!items) return null;

  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile();
      if (file instanceof File) {
        return file;
      }
    }
  }

  return null;
}

async function onEditUploadFieldPaste(field: PlayerListField, event: Event) {
  const clipboardEvent = event as ClipboardEvent;
  setActiveEditUploadImageField(field);

  if (normalizeFieldType(field.type) !== 'upload_image') return;
  const file = getClipboardImageFile(clipboardEvent);
  if (!file) return;

  clipboardEvent.preventDefault();
  await appendEditUploadFiles(field, [file]);
}

async function onEditWindowPaste(event: ClipboardEvent) {
  if (!editModalVisible.value) return;

  const fieldKey = activeEditUploadImageFieldKey.value;
  if (!fieldKey) return;

  const field = editFields.value.find(item => item.key === fieldKey);
  if (!field || normalizeFieldType(field.type) !== 'upload_image') return;

  const file = getClipboardImageFile(event);
  if (!file) return;

  event.preventDefault();
  await appendEditUploadFiles(field, [file]);
}

// ========== GS字段相关函数 ==========

function isQgsGsField(field: PlayerListField): boolean {
  const key = field.key.toLowerCase();
  return key.includes('qgs_gs') || key.includes('前端gs') || key === 'qgs_gs' || key === 'frontend_gs';
}

function isHgsGsField(field: PlayerListField): boolean {
  const key = field.key.toLowerCase();
  return key.includes('hgs_gs') || key.includes('后端gs') || key === 'hgs_gs' || key === 'backend_gs';
}

function getGsFieldOptions(field: PlayerListField): FieldOption[] {
  if (isQgsGsField(field)) {
    return QGS_ROLE_OPTIONS;
  }
  if (isHgsGsField(field)) {
    return HGS_ROLE_OPTIONS;
  }
  return toFieldOptions(field.options);
}

onMounted(async () => {
  window.addEventListener('paste', onEditWindowPaste);
  await Promise.all([loadProjects(), loadSchema()]);
  await loadData();
});
</script>

<template>
  <div class="player-list-page min-h-500px">
    <NCard :bordered="false">
      <template #header></template>

      <div class="flex-col-stretch gap-8px">
        <div class="search-grid">
          <NDatePicker
            v-model:value="searchModel.dateRange"
            type="daterange"
            clearable
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            class="w-full"
          />
          <NInput v-model:value="searchModel.alias" placeholder="角色别名" clearable @keyup.enter="onSearch" />
          <NSelect
            v-model:value="searchModel.projectId"
            placeholder="项目"
            clearable
            :options="projectOptions"
            class="w-full"
          />
          <NInput v-model:value="searchModel.playerId" placeholder="玩家ID" clearable @keyup.enter="onSearch" />
          <NInput v-model:value="searchModel.server" placeholder="区服" clearable @keyup.enter="onSearch" />
          <NInput v-model:value="searchModel.keyword" placeholder="关键词" clearable @keyup.enter="onSearch" />
        </div>

        <NSpace justify="end">
          <NButton type="primary" @click="onSearch">查询</NButton>
          <NButton @click="onReset">重置</NButton>
        </NSpace>
      </div>
    </NCard>

    <NCard :title="cardTitle" :bordered="false">
      <template #header-extra>
        <NSpace>
          <NButton @click="openUploadModal">批量导入</NButton>
          <NPopover placement="bottom-end" trigger="click">
            <template #trigger>
              <NButton>列设置</NButton>
            </template>
            <div class="field-setting-panel">
              <div class="field-setting-row">
                <span class="field-setting-label">项目列宽</span>
                <NInputNumber
                  :value="staticColumnWidths.project_id"
                  :min="MIN_COLUMN_WIDTH"
                  :max="MAX_COLUMN_WIDTH"
                  :step="4"
                  size="small"
                  class="field-width-input"
                  @update:value="value => updateStaticColumnWidth('project_id', value)"
                />
              </div>
              <div class="field-setting-row">
                <span class="field-setting-label">创建时间列宽</span>
                <NInputNumber
                  :value="staticColumnWidths.created_at"
                  :min="MIN_COLUMN_WIDTH"
                  :max="MAX_COLUMN_WIDTH"
                  :step="4"
                  size="small"
                  class="field-width-input"
                  @update:value="value => updateStaticColumnWidth('created_at', value)"
                />
              </div>
              <div class="field-setting-row">
                <span class="field-setting-label">操作列宽</span>
                <NInputNumber
                  :value="staticColumnWidths.actions"
                  :min="MIN_COLUMN_WIDTH"
                  :max="MAX_COLUMN_WIDTH"
                  :step="4"
                  size="small"
                  class="field-width-input"
                  @update:value="value => updateStaticColumnWidth('actions', value)"
                />
              </div>
              <div class="field-setting-row field-setting-actions">
                <NButton text type="primary" size="small" @click="resetFieldOrder">重置列顺序</NButton>
                <NButton text type="primary" size="small" @click="resetColumnWidths">重置列宽</NButton>
              </div>
              <NDivider class="!my-8px" />
              <div class="field-width-list">
                <VueDraggable v-model="draggableFields" item-key="key" :animation="150" handle=".drag-handle">
                  <div v-for="field in draggableFields" :key="field.key" class="field-sort-item">
                    <icon-mdi-drag class="drag-handle cursor-move text-icon" />
                    <div class="field-sort-text">
                      <span class="field-sort-label">{{ field.label }}</span>
                      <span class="field-sort-key">{{ field.key }}</span>
                    </div>
                    <NInputNumber
                      :value="fieldColumnWidths[field.key]"
                      :min="MIN_COLUMN_WIDTH"
                      :max="MAX_COLUMN_WIDTH"
                      :step="4"
                      size="small"
                      class="field-width-input"
                      @update:value="value => updateFieldColumnWidth(field.key, value)"
                    />
                  </div>
                </VueDraggable>
              </div>
            </div>
          </NPopover>
        </NSpace>
      </template>

      <NAlert v-if="schemaWarning" type="warning" :show-icon="true" :title="schemaWarning" class="mb-12px" />

      <NDataTable
        class="player-list-table"
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :row-key="getPlayerRowKey"
        :scroll-x="tableScrollX"
        size="small"
        :header-height="30"
        :min-row-height="26"
        :single-line="false"
        single-column
        bordered
        table-layout="fixed"
        :on-unstable-column-resize="handleColumnResize"
      />

      <div class="flex justify-end pt-2">
        <NPagination
          v-model:page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :item-count="total"
          :page-sizes="[50, 100, 200]"
          show-size-picker
          @update:page="onPageChange"
          @update:page-size="onPageSizeChange"
        />
      </div>
    </NCard>

    <NModal
      v-model:show="uploadPreviewModalVisible"
      :title="uploadPreviewTitle"
      preset="card"
      class="w-760px"
      @close="closeUploadPreview"
    >
      <div v-if="uploadPreviewUrls.length" class="upload-preview-grid">
        <NImage
          v-for="(url, index) in uploadPreviewUrls"
          :key="`${url}-${index}`"
          :src="url"
          width="132"
          height="132"
          object-fit="cover"
          alt="upload-preview"
        />
      </div>
      <NEmpty v-else description="暂无可预览内容" />
    </NModal>

    <NModal v-model:show="uploadModalVisible" title="上传文件" preset="card" class="w-520px">
      <div class="upload-modal-content">
        <NSpace vertical :size="16">
          <NButton secondary type="primary" @click="downloadImportTemplate">下载导入模板</NButton>

          <NUpload
            v-model:file-list="uploadFileList"
            :max="1"
            :default-upload="false"
            accept=".csv,.xlsx,.xls"
            :custom-request="handleUploadFile"
            @remove="handleUploadRemove"
          >
            <NButton block>选择上传文件</NButton>
          </NUpload>
        </NSpace>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="closeUploadModal">取消</NButton>
          <NButton type="primary" @click="confirmUploadFile">确认上传</NButton>
        </NSpace>
      </template>
    </NModal>

    <NModal
      v-model:show="editModalVisible"
      :title="editModalTitle"
      preset="card"
      class="w-760px"
      :mask-closable="false"
    >
      <div class="edit-modal-content">
        <NForm label-placement="left" :label-width="90">
          <NFormItem label="项目">
            <NSelect
              v-model:value="editProjectId"
              :options="projectOptions"
              filterable
              clearable
              placeholder="请选择项目"
            />
          </NFormItem>
        </NForm>

        <div class="edit-form-scroll">
          <NForm label-placement="left" :label-width="120" size="small">
            <NFormItem v-for="field in editFields" :key="field.key" :label="field.label">
              <NInputNumber
                v-if="isEditNumberField(field)"
                :value="getEditNumberValue(field.key)"
                clearable
                class="w-full"
                :disabled="isEditFieldReadonly(field)"
                :placeholder="getEditFieldPlaceholder(field)"
                @update:value="value => setEditNumberValue(field.key, value)"
              />

              <NDatePicker
                v-else-if="isEditDatetimeField(field)"
                type="datetime"
                clearable
                class="w-full"
                :disabled="isEditFieldReadonly(field)"
                :value="getEditDatetimeValue(field.key)"
                @update:value="value => setEditDatetimeValue(field.key, value)"
              />

              <NSelect
                v-else-if="isEditSelectField(field) || isQgsGsField(field) || isHgsGsField(field)"
                :value="getEditSelectValue(field.key)"
                :placeholder="getEditFieldPlaceholder(field)"
                :options="getGsFieldOptions(field)"
                :multiple="isEditMultipleField(field)"
                clearable
                class="w-full"
                :disabled="isEditFieldReadonly(field)"
                @update:value="value => setEditSelectValue(field.key, value)"
              />

              <NRadioGroup
                v-else-if="isEditRadioField(field)"
                :value="getEditRadioValue(field.key)"
                class="w-full"
                :disabled="isEditFieldReadonly(field)"
                @update:value="value => setEditRadioValue(field.key, value)"
              >
                <NSpace>
                  <NRadio
                    v-for="option in toFieldOptions(field.options)"
                    :key="`${field.key}-${option.value}`"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </NRadio>
                </NSpace>
              </NRadioGroup>

              <NCheckboxGroup
                v-else-if="isEditCheckboxField(field)"
                :value="getEditCheckboxValue(field.key)"
                class="w-full"
                :disabled="isEditFieldReadonly(field)"
                @update:value="value => setEditCheckboxValue(field.key, value)"
              >
                <NSpace>
                  <NCheckbox
                    v-for="option in toFieldOptions(field.options)"
                    :key="`${field.key}-${option.value}`"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </NCheckbox>
                </NSpace>
              </NCheckboxGroup>

              <NColorPicker
                v-else-if="isEditColorField(field)"
                :value="getEditColorValue(field.key)"
                clearable
                class="w-full"
                :disabled="isEditFieldReadonly(field)"
                @update:value="value => setEditColorValue(field.key, value)"
              />

              <NSwitch
                v-else-if="isEditSwitchField(field)"
                :value="getEditSwitchValue(field.key)"
                :disabled="isEditFieldReadonly(field)"
                @update:value="value => setEditSwitchValue(field.key, value)"
              />

              <!-- 上传图片组件 -->
              <div
                v-else-if="isEditUploadImageField(field)"
                class="upload-image-field"
                tabindex="0"
                @click="setActiveEditUploadImageField(field)"
                @focusin="setActiveEditUploadImageField(field)"
                @paste="event => onEditUploadFieldPaste(field, event)"
                @keydown.enter.prevent="pickEditUploadFile(field)"
                @keydown.space.prevent="pickEditUploadFile(field)"
              >
                <div class="upload-image-grid">
                  <div
                    v-for="(uploadItem, uploadIndex) in getEditUploadValues(field.key)"
                    :key="`${field.key}-${uploadItem.name}-${uploadIndex}`"
                    class="upload-image-item"
                  >
                    <img :src="uploadItem.data_url" class="upload-image-box__preview" />
                    <button
                      type="button"
                      class="upload-image-item__remove"
                      @click.stop="removeEditUploadValue(field.key, uploadIndex)"
                    >
                      移除
                    </button>
                  </div>
                  <button
                    v-if="getEditUploadValues(field.key).length < UPLOAD_PREVIEW_MAX_COUNT"
                    type="button"
                    class="upload-image-box"
                    @click.stop="pickEditUploadFile(field)"
                  >
                    <div class="upload-image-box__plus">+</div>
                    <div class="upload-image-box__text">点击上传或粘贴图片</div>
                  </button>
                </div>

                <div v-if="getEditUploadValues(field.key).length" class="upload-meta">
                  <span class="upload-name">已上传 {{ getEditUploadValues(field.key).length }} 张</span>
                  <NButton text type="error" @click.stop="clearEditUploadValue(field.key)">清空</NButton>
                </div>

                <input
                  :ref="el => setEditUploadInputRef(field.key, el as HTMLInputElement | null)"
                  type="file"
                  class="hidden"
                  accept="image/*"
                  multiple
                  @change="event => onEditUploadInputChange(field, event)"
                />
              </div>

              <NInput
                v-else-if="isEditTextareaField(field)"
                :value="getEditStringValue(field.key)"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 4 }"
                :disabled="isEditFieldReadonly(field)"
                :placeholder="getEditFieldPlaceholder(field)"
                @update:value="value => setEditStringValue(field.key, value)"
              />

              <NInput
                v-else
                :value="getEditStringValue(field.key)"
                :disabled="isEditFieldReadonly(field)"
                :placeholder="getEditFieldPlaceholder(field)"
                @update:value="value => setEditStringValue(field.key, value)"
              />
            </NFormItem>
          </NForm>
        </div>
      </div>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="closeEditModal">取消</NButton>
          <NButton type="primary" :loading="editSubmitting" @click="submitEditModal">保存</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.player-list-page {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
}

.field-setting-panel {
  width: 460px;
}

.field-setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.field-setting-row + .field-setting-row {
  margin-top: 8px;
}

.field-setting-label {
  color: var(--n-text-color);
  font-size: 13px;
}

.field-setting-actions {
  justify-content: flex-end;
  gap: 4px;
}

.field-width-list {
  max-height: 320px;
  overflow-y: auto;
  padding-right: 2px;
}

.field-sort-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--n-border-color);
  border-radius: 6px;
}

.field-sort-item + .field-sort-item {
  margin-top: 6px;
}

.field-sort-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-sort-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field-sort-key {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--n-text-color-3);
  font-size: 12px;
}

.field-width-input {
  width: 96px;
  flex-shrink: 0;
}

.thumb-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.player-list-page :deep(.player-list-table .n-data-table-th),
.player-list-page :deep(.player-list-table .n-data-table-td) {
  padding-top: 5px;
  padding-bottom: 5px;
}

.player-list-page :deep(.player-list-table .n-data-table-tbody .n-data-table-tr .n-data-table-td) {
  border-bottom: 1px solid var(--n-border-color);
}

.upload-modal-content {
  padding-top: 4px;
}

.upload-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 10px;
}

.edit-modal-content {
  padding-top: 4px;
}

.edit-form-scroll {
  max-height: 56vh;
  overflow-y: auto;
  padding-right: 4px;
}

/* 上传图片组件样式 */
.upload-image-field {
  width: 100%;
}

.upload-image-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.upload-image-box {
  width: 80px;
  height: 80px;
  border: 1px dashed var(--n-border-color);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: transparent;
  transition: all 0.2s;
}

.upload-image-box:hover,
.upload-image-field:focus-within .upload-image-box {
  border-color: var(--n-primary-color);
  background: color-mix(in srgb, var(--n-primary-color) 5%, transparent);
}

.upload-image-box__plus {
  font-size: 24px;
  color: var(--n-text-color-3);
  line-height: 1;
}

.upload-image-box__text {
  font-size: 10px;
  color: var(--n-text-color-3);
  text-align: center;
  margin-top: 4px;
  max-width: 70px;
}

.upload-image-item {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 6px;
  overflow: hidden;
}

.upload-image-box__preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-image-item__remove {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 12px;
  border: none;
  padding: 4px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.upload-image-item:hover .upload-image-item__remove {
  opacity: 1;
}

.upload-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.upload-name {
  font-size: 12px;
  color: var(--n-text-color-3);
}
</style>
