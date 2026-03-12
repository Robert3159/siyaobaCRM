<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NModal,
  NProgress,
  NSelect,
  NSpace,
  NStep,
  NSteps,
  NTag,
  NUpload
} from 'naive-ui';
import type { UploadFileInfo } from 'naive-ui';
import {
  fetchFieldMappings,
  fetchOrderImportPreview,
  fetchSystemFields,
  saveFieldMappings,
  submitOrderImport
} from '@/service/api/order';
import { fetchProjectList } from '@/service/api/project';

interface Props {
  show?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  show: false
});

const emit = defineEmits<{
  (e: 'update:show', show: boolean): void;
  (e: 'success'): void;
}>();

// 步骤控制
const currentStep = ref(1);
const steps = [
  { title: '选择项目', description: '选择要导入的项目' },
  { title: '字段映射', description: '映射文件字段到系统字段' },
  { title: '预览数据', description: '确认导入数据' },
  { title: '导入结果', description: '查看导入结果' }
];

// 数据
const projectOptions = ref<{ label: string; value: number }[]>([]);
const systemFields = ref<Api.Order.SystemField[]>([]);
const selectedProject = ref<number | null>(null);
const uploadFileList = ref<UploadFileInfo[]>([]);
const selectedFile = ref<File | null>(null);
const fileHeaders = ref<string[]>([]);
const previewData = ref<Record<string, any>[]>([]);
const suggestedMapping = ref<Record<string, string>>({});
const fieldMapping = ref<Record<string, string>>({});
const saveMapping = ref(false);
const totalRows = ref(0);

// 状态
const loading = ref(false);
const importing = ref(false);
const importProgress = ref(0);
const importResult = ref<Api.Order.ImportResult | null>(null);

// 初始化
onMounted(async () => {
  await loadProjectOptions();
  await loadSystemFields();
});

async function loadProjectOptions() {
  const { data, error } = await fetchProjectList({ page: 1, page_size: 100 });
  projectOptions.value =
    !error && Array.isArray(data?.items) ? data.items.map(p => ({ label: p.name, value: p.id })) : [];
}

async function loadSystemFields() {
  const res = await fetchSystemFields();
  systemFields.value = res.data || [];
}

// 监听弹窗显示
watch(
  () => props.show,
  async newVal => {
    if (newVal) {
      // 重置状态
      currentStep.value = 1;
      selectedProject.value = null;
      uploadFileList.value = [];
      selectedFile.value = null;
      fileHeaders.value = [];
      previewData.value = [];
      suggestedMapping.value = {};
      fieldMapping.value = {};
      importResult.value = null;
    }
  }
);

// 文件上传
function handleFileChange(options: { file: UploadFileInfo }) {
  const file = options.file.file;
  if (file) {
    selectedFile.value = file;
    uploadFileList.value = [options.file];
    // 进入下一步
    if (selectedProject.value) {
      currentStep.value = 2;
      loadPreview();
    }
  }
}

// 加载预览
async function loadPreview() {
  if (!selectedFile.value || !selectedProject.value) return;

  loading.value = true;
  try {
    const res = await fetchOrderImportPreview(
      selectedFile.value,
      selectedProject.value,
      Object.keys(fieldMapping.value).length > 0 ? fieldMapping.value : undefined
    );
    if (res.data) {
      fileHeaders.value = res.data.headers;
      previewData.value = res.data.preview_data;
      suggestedMapping.value = res.data.suggested_mapping;
      totalRows.value = res.data.total_rows;

      // 使用建议的映射
      fieldMapping.value = { ...suggestedMapping.value };

      // 尝试加载已保存的映射
      const savedMappings = await fetchFieldMappings(selectedProject.value);
      if (savedMappings.data?.items.length) {
        savedMappings.data.items.forEach((m: Api.Order.FieldMapping) => {
          if (fileHeaders.value.includes(m.file_field)) {
            fieldMapping.value[m.file_field] = m.system_field;
          }
        });
      }
    }
  } finally {
    loading.value = false;
  }
}

// 字段映射变化
function updateFieldMapping(fileField: string, systemField: string | null) {
  if (systemField) {
    fieldMapping.value[fileField] = systemField;
  } else {
    const keys = Object.keys(fieldMapping.value) as string[];
    const newMapping: Record<string, string> = {};
    keys.forEach(key => {
      if (key !== fileField) {
        newMapping[key] = fieldMapping.value[key];
      }
    });
    fieldMapping.value = newMapping;
  }
}

// 提交导入
async function doImport() {
  if (!selectedFile.value || !selectedProject.value) return;

  importing.value = true;
  importProgress.value = 0;

  try {
    // 保存映射配置
    if (saveMapping.value && selectedProject.value) {
      const mappings = Object.entries(fieldMapping.value).map(([file_field, system_field]) => ({
        file_field,
        system_field
      }));
      await saveFieldMappings(selectedProject.value, mappings);
    }

    const res = await submitOrderImport(selectedFile.value, selectedProject.value, fieldMapping.value);
    if (res.data) {
      importResult.value = res.data;
      importProgress.value = 100;
      currentStep.value = 4;
      if (res.data.success || res.data.success_rows > 0) {
        emit('success');
      }
    }
  } catch {
    importResult.value = {
      success: false,
      total_rows: 0,
      success_rows: 0,
      fail_rows: 0,
      log_id: 0,
      fail_details: []
    };
    currentStep.value = 4;
  } finally {
    importing.value = false;
  }
}

// 关闭弹窗
function handleClose() {
  emit('update:show', false);
}

// 获取系统字段选项
const systemFieldOptions = computed(() => {
  return [
    { label: '不映射', value: '' },
    ...systemFields.value.map(f => ({
      label: `${f.field_label} (${f.system_field})`,
      value: f.system_field
    }))
  ];
});

// 预览表格列
const previewColumns = computed(() => {
  const cols: any[] = [];
  fileHeaders.value.forEach(header => {
    const systemField = fieldMapping.value[header];
    const fieldDef = systemFields.value.find(f => f.system_field === systemField);
    cols.push({
      title: fieldDef ? `${header}\n→${fieldDef.field_label}` : header,
      key: header,
      width: 120,
      ellipsis: { tooltip: true }
    });
  });
  return cols;
});

// 步骤验证
const canGoNext = computed(() => {
  if (currentStep.value === 1) {
    return selectedProject.value && selectedFile.value;
  }
  if (currentStep.value === 2) {
    return fileHeaders.value.length > 0;
  }
  if (currentStep.value === 3) {
    return previewData.value.length > 0;
  }
  return true;
});

function nextStep() {
  if (currentStep.value < 4) {
    currentStep.value += 1;
  }
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value -= 1;
  }
}
</script>

<template>
  <NModal
    :show="props.show"
    :mask-closable="!importing"
    :closable="!importing"
    preset="card"
    title="导入订单"
    class="import-modal-wrapper"
    @update:show="emit('update:show', $event)"
    @close="handleClose"
  >
    <div class="import-modal">
      <!-- 步骤条 -->
      <NSteps :current="currentStep" size="small">
        <NStep v-for="(step, index) in steps" :key="index" :title="step.title" :description="step.description" />
      </NSteps>
      <div class="step-content">
        <!-- 步骤1: 选择项目 + 上传文件 -->
        <div v-show="currentStep === 1" class="step-panel">
          <NCard title="步骤1: 选择项目" size="small">
            <div class="form-item">
              <span class="label">选择项目：</span>
              <NSelect
                v-model:value="selectedProject"
                :options="projectOptions"
                placeholder="请选择项目"
                class="w-300px"
                :disabled="importing"
              />
            </div>
          </NCard>
          <NCard title="步骤2: 上传文件" size="small" class="mt-16px">
            <NUpload
              v-model:file-list="uploadFileList"
              accept=".csv,.xlsx,.xls"
              :max="1"
              :disabled="importing"
              :custom-request="() => {}"
              @change="handleFileChange"
            >
              <NButton>选择文件</NButton>
            </NUpload>
            <div class="upload-tip">支持 .csv, .xlsx, .xls 格式的文件</div>
          </NCard>
        </div>

        <!-- 步骤2: 字段映射 -->
        <div v-show="currentStep === 2" class="step-panel">
          <NCard title="字段映射" size="small">
            <div class="mapping-tip">
              <NAlert type="info" :show-icon="false">
                请将左侧文件字段映射到右侧系统字段。未映射的字段将保存到 raw_data。
              </NAlert>
            </div>
            <div class="mapping-grid">
              <div class="mapping-header">
                <div class="file-field-col">文件字段</div>
                <div class="arrow-col"></div>
                <div class="system-field-col">系统字段</div>
              </div>
              <div v-for="header in fileHeaders" :key="header" class="mapping-row">
                <div class="file-field-col">{{ header }}</div>
                <div class="arrow-col">→</div>
                <div class="system-field-col">
                  <NSelect
                    :value="fieldMapping[header]"
                    :options="systemFieldOptions"
                    placeholder="选择系统字段"
                    @update:value="updateFieldMapping(header, $event)"
                  />
                </div>
              </div>
            </div>
            <div class="save-mapping">
              <!-- 修复: 属性顺序 size 应在 @click 前 -->
              <NButton size="small" :type="saveMapping ? 'primary' : 'default'" @click="saveMapping = !saveMapping">
                {{ saveMapping ? '✓' : '' }} 保存映射配置
              </NButton>
              <span class="save-tip">保存后可复用映射关系</span>
            </div>
          </NCard>
        </div>

        <!-- 步骤3: 预览数据 -->
        <div v-show="currentStep === 3" class="step-panel">
          <NCard title="数据预览" size="small">
            <div class="preview-info">
              <NTag type="info">总行数: {{ totalRows }}</NTag>
              <NTag type="success">预览: {{ previewData.length }} 条</NTag>
            </div>
            <div class="preview-table-wrapper">
              <NDataTable
                :columns="previewColumns"
                :data="previewData"
                :bordered="true"
                :single-line="false"
                size="small"
                :scroll-x="fileHeaders.length * 120"
                :max-height="400"
              />
            </div>
          </NCard>
        </div>

        <!-- 步骤4: 导入结果 -->
        <div v-show="currentStep === 4" class="step-panel">
          <NCard title="导入结果" size="small">
            <div v-if="importResult" class="result-content">
              <div class="result-summary">
                <NTag type="success" :bordered="true" size="large">成功: {{ importResult.success_rows }}</NTag>
                <NTag type="error" :bordered="true" size="large">失败: {{ importResult.fail_rows }}</NTag>
              </div>
              <NAlert v-if="importResult.fail_rows > 0" type="warning" class="mt-16px">
                有 {{ importResult.fail_rows }} 条记录导入失败
              </NAlert>
            </div>
            <NEmpty v-else description="导入中...">
              <template #extra>
                <NProgress type="line" :percentage="importProgress" indicator-placement="inside" />
              </template>
            </NEmpty>
          </NCard>
        </div>
      </div>
      <!-- 底部按钮 -->
      <div class="modal-footer">
        <NSpace justify="end">
          <NButton :disabled="importing" @click="handleClose">取消</NButton>
          <NButton v-if="currentStep > 1 && currentStep < 4" @click="prevStep">上一步</NButton>
          <NButton v-if="currentStep < 3" type="primary" :disabled="!canGoNext" @click="nextStep">下一步</NButton>
          <NButton v-if="currentStep === 3" type="primary" :loading="importing" @click="doImport">开始导入</NButton>
          <NButton v-if="currentStep === 4" type="primary" @click="handleClose">完成</NButton>
        </NSpace>
      </div>
    </div>
  </NModal>
</template>

<style scoped>
.import-modal-wrapper {
  width: 900px;
  max-width: 95vw;
}

.import-modal {
  display: flex;
  flex-direction: column;
  min-height: 500px;
}

.step-content {
  flex: 1;
  margin-top: 24px;
}

.step-panel {
  min-height: 400px;
}

.form-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-item .label {
  font-weight: 500;
}

.w-300px {
  width: 300px;
}

.mt-16px {
  margin-top: 16px;
}

.upload-tip {
  margin-top: 8px;
  color: #666;
  font-size: 12px;
}

.mapping-tip {
  margin-bottom: 16px;
}

.mapping-grid {
  margin-top: 16px;
}

.mapping-header {
  display: flex;
  font-weight: 500;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.mapping-row {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.file-field-col {
  flex: 1;
  padding: 0 8px;
}

.arrow-col {
  width: 40px;
  text-align: center;
  color: #999;
}

.system-field-col {
  flex: 1;
  padding: 0 8px;
}

.save-mapping {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.save-tip {
  font-size: 12px;
  color: #999;
}

.preview-info {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.preview-table-wrapper {
  margin-top: 8px;
}

.result-content {
  text-align: center;
}

.result-summary {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin: 24px 0;
}

.modal-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}
</style>
