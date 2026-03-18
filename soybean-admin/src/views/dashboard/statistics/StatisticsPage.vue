<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { NSpace } from 'naive-ui';
import { STATISTICS_CONFIG, type StatisticsPreset } from '@/constants/statistics';
import { fetchDailyStatistics, fetchStatistics } from '@/service/api/statistics';
import StatCardGroup from '@/components/business/statistics/StatCardGroup.vue';
import LineChart from '@/components/business/statistics/LineChart.vue';
import BarChart from '@/components/business/statistics/BarChart.vue';
import StatisticsTable from '@/components/business/statistics/StatisticsTable.vue';

interface Props {
  preset: StatisticsPreset;
}

const props = defineProps<Props>();

// 加载状态
const statisticsLoading = ref(false);
const dailyLoading = ref(false);

// 统计数据
const statisticsData = ref<Api.Statistics.QgsStatisticsResponse | Api.Statistics.HgsStatisticsResponse | null>(null);

// 每日明细数据
const dailyData = ref<Api.Statistics.QgsDailyStatisticsItem[] | Api.Statistics.HgsDailyStatisticsItem[]>([]);
const dailyTotal = ref(0);
const dailyPage = ref(1);
const dailyPageSize = ref(20);

// 筛选条件
const sortField = ref('date');
const sortOrder = ref<'asc' | 'desc'>('desc');
const startDate = ref<string | undefined>();
const endDate = ref<string | undefined>();

// 配置
const config = computed(() => STATISTICS_CONFIG[props.preset]);

// 折线图数据系列
const lineChartSeries = computed(() => {
  return config.value.metrics.map(metric => ({
    key: metric.key,
    name: metric.label,
    color: getSeriesColor(metric.key)
  }));
});

// 获取系列颜色
function getSeriesColor(key: string): string {
  const colors: Record<string, string> = {
    new_registrations: '#67c23a',
    paying_users: '#409eff',
    total_amount: '#e6a23c',
    connected_users: '#909399',
    new_paying_users: '#f56c6c'
  };
  return colors[key] || '#409eff';
}

// 格式化日期
function formatDate(timestamp: number): string {
  const date = new Date(timestamp);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

// 获取统计数据
async function loadStatistics() {
  statisticsLoading.value = true;
  try {
    const res = await fetchStatistics(props.preset);
    statisticsData.value = res.data;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Failed to load statistics:', error);
  } finally {
    statisticsLoading.value = false;
  }
}

// 获取每日明细
async function loadDailyData() {
  dailyLoading.value = true;
  try {
    const params: Api.Statistics.DailyStatisticsParams = {
      sort_field: sortField.value,
      sort_order: sortOrder.value,
      page: dailyPage.value,
      page_size: dailyPageSize.value,
      start_date: startDate.value,
      end_date: endDate.value
    };

    const res = await fetchDailyStatistics(props.preset, params);
    if (res.data) {
      dailyData.value = res.data.items as any;
      dailyTotal.value = res.data.total;
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Failed to load daily data:', error);
  } finally {
    dailyLoading.value = false;
  }
}

// 处理分页变化
function handlePageChange(page: number) {
  dailyPage.value = page;
  loadDailyData();
}

function handlePageSizeChange(pageSize: number) {
  dailyPageSize.value = pageSize;
  dailyPage.value = 1;
  loadDailyData();
}

// 处理排序变化
function handleSortChange(sortFieldValue: string, sortOrderValue: 'asc' | 'desc') {
  sortField.value = sortFieldValue;
  sortOrder.value = sortOrderValue;
  loadDailyData();
}

// 处理筛选变化
function handleFilterChange(start?: number, end?: number) {
  startDate.value = start ? formatDate(start) : undefined;
  endDate.value = end ? formatDate(end) : undefined;
  dailyPage.value = 1;
  loadDailyData();
}

// 处理导出
function handleExport() {
  // eslint-disable-next-line no-console
  console.log('Export data');
}

// 初始化
onMounted(() => {
  loadStatistics();
  loadDailyData();
});

// 监听预设变化
watch(
  () => props.preset,
  () => {
    loadStatistics();
    loadDailyData();
  }
);
</script>

<template>
  <div class="statistics-page">
    <NSpace vertical :size="20">
      <!-- 统计卡片组 -->
      <StatCardGroup :preset="props.preset" :loading="statisticsLoading" :data="statisticsData || undefined" />

      <!-- 趋势图表 -->
      <LineChart :data="dailyData as any" :series="lineChartSeries" :loading="dailyLoading" />

      <!-- 柱状图（仅 HGS） -->
      <BarChart v-if="props.preset === 'hgs'" title="玩家充值排行 Top 10" :data="[]" :loading="dailyLoading" />

      <!-- 数据表格 -->
      <StatisticsTable
        :preset="props.preset"
        :data="dailyData as any"
        :loading="dailyLoading"
        :total="dailyTotal"
        :page="dailyPage"
        :page-size="dailyPageSize"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        @sort-change="handleSortChange"
        @filter-change="handleFilterChange"
        @export="handleExport"
      />
    </NSpace>
  </div>
</template>

<style scoped>
.statistics-page {
  width: 100%;
  padding: 16px;
}
</style>
