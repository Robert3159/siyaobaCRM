<script setup lang="ts">
import { computed } from 'vue';
import { NCard, NSpace, NSpin, NStatistic, NText } from 'naive-ui';
import { formatCurrency, formatNumber } from '@/constants/statistics';

interface Props {
  title: string;
  value: number | string;
  type?: 'number' | 'currency';
  loading?: boolean;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
  };
}

const props = withDefaults(defineProps<Props>(), {
  type: 'number',
  loading: false,
  trend: undefined
});

const formattedValue = computed(() => {
  if (props.type === 'currency') {
    return formatCurrency(props.value);
  }
  return formatNumber(props.value);
});

const trendColor = computed(() => {
  if (!props.trend) return undefined;
  switch (props.trend.direction) {
    case 'up':
      return '#18a058';
    case 'down':
      return '#d03050';
    default:
      return '#808080';
  }
});

const trendIcon = computed(() => {
  if (!props.trend) return undefined;
  switch (props.trend.direction) {
    case 'up':
      return '↑';
    case 'down':
      return '↓';
    default:
      return '→';
  }
});
</script>

<template>
  <NCard :bordered="false" class="stat-card">
    <NSpace vertical :size="12">
      <NText depth="3" class="stat-card-title">{{ title }}</NText>

      <NSpin :show="loading">
        <div class="stat-card-content">
          <NStatistic class="stat-value" :class="`stat-value--${type}`">
            {{ formattedValue }}
          </NStatistic>

          <div v-if="trend" class="stat-trend" :style="{ color: trendColor }">
            <span class="stat-trend-icon">{{ trendIcon }}</span>
            <span class="stat-trend-value">{{ Math.abs(trend.value) }}%</span>
          </div>
        </div>
      </NSpin>
    </NSpace>
  </NCard>
</template>

<style scoped>
.stat-card {
  height: 100%;
}

.stat-card-title {
  font-size: 14px;
  font-weight: 500;
}

.stat-card-content {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
}

.stat-value--currency {
  color: #f0a020;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.stat-trend-icon {
  font-weight: bold;
}
</style>
