<script setup lang="ts">
import { computed } from 'vue';
import { NGrid, NGridItem } from 'naive-ui';
import { STATISTICS_CONFIG, type StatisticsPreset, TIME_RANGE_LABELS } from '@/constants/statistics';
import StatCard from './StatCard.vue';

interface Props {
  preset: StatisticsPreset;
  loading?: boolean;
  data?: Api.Statistics.QgsStatisticsResponse | Api.Statistics.HgsStatisticsResponse;
}

const props = defineProps<Props>();

// 时间范围列表
const timeRanges = ['today', 'yesterday', 'last_7_days', 'this_month', 'all_time'] as const;

// 获取配置
const config = computed(() => STATISTICS_CONFIG[props.preset]);

// 获取卡片数据
function getCardData(timeRange: string) {
  if (!props.data) {
    return {
      new_registrations: 0,
      paying_users: 0,
      connected_users: 0,
      new_paying_users: 0,
      total_amount: 0
    };
  }
  return (props.data as any)[timeRange] || {};
}

// 计算趋势
function calculateTrend(current: number, previous: number) {
  if (previous === 0) {
    return current > 0 ? { value: 100, direction: 'up' as const } : { value: 0, direction: 'neutral' as const };
  }

  const change = ((current - previous) / previous) * 100;
  let direction: 'up' | 'down' | 'neutral';

  if (change > 0) {
    direction = 'up';
  } else if (change < 0) {
    direction = 'down';
  } else {
    direction = 'neutral';
  }

  return {
    value: Number(Math.abs(change).toFixed(1)),
    direction
  };
}

// 获取趋势数据
function getTrend(timeRange: string, metricKey: string) {
  if (!props.data || timeRange === 'all_time') return undefined;

  const timeRangeIndex = timeRanges.indexOf(timeRange as any);
  if (timeRangeIndex === 0) return undefined; // 今日没有昨日对比

  const currentData = getCardData(timeRange);
  const previousTimeRange = timeRanges[timeRangeIndex - 1];
  const previousData = getCardData(previousTimeRange);

  const current = (currentData as any)[metricKey] || 0;
  const previous = (previousData as any)[metricKey] || 0;

  return calculateTrend(current, previous);
}
</script>

<template>
  <div class="stat-card-group">
    <NGrid :cols="5" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
      <NGridItem v-for="timeRange in timeRanges" :key="timeRange" span="5 m:2 l:1">
        <StatCard
          v-for="metric in config.metrics"
          :key="`${timeRange}-${metric.key}`"
          :title="`${TIME_RANGE_LABELS[timeRange]} - ${metric.label}`"
          :value="(getCardData(timeRange) as any)[metric.key] || 0"
          :type="metric.key === 'total_amount' ? 'currency' : 'number'"
          :loading="loading"
          :trend="getTrend(timeRange, metric.key)"
        />
      </NGridItem>
    </NGrid>
  </div>
</template>

<style scoped>
.stat-card-group {
  width: 100%;
}
</style>
