<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { NCard, NSpin } from 'naive-ui';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TitleComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { formatCurrency, formatNumber } from '@/constants/statistics';

// 注册 ECharts 组件
echarts.use([LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer]);

interface Props {
  data: Array<{ date: string; [key: string]: number | string }>;
  series: Array<{ key: string; name: string; color: string }>;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const chartRef = ref<HTMLDivElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

// 格式化数值
function formatValue(value: number | string, key: string): string {
  if (key === 'total_amount') {
    return formatCurrency(value);
  }
  return formatNumber(value);
}

// 图表配置
const chartOptions = computed(() => {
  if (!props.data.length) return null;

  const series = props.series.map(s => ({
    name: s.name,
    type: 'line' as const,
    smooth: true,
    data: props.data.map(item => ({
      value: Number(item[s.key]) || 0,
      name: item.date
    })),
    itemStyle: {
      color: s.color
    },
    lineStyle: {
      width: 2
    },
    symbol: 'circle',
    symbolSize: 6,
    emphasis: {
      focus: 'series'
    }
  }));

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        let result = `<div style="font-weight:bold;margin-bottom:8px;">${params[0].axisValue}</div>`;
        params.forEach(param => {
          const key = props.series.find(s => s.name === param.seriesName)?.key || '';
          result += `<div style="display:flex;justify-content:space-between;gap:16px;margin:4px 0;">
            <span style="color:${param.color};">● ${param.seriesName}</span>
            <span style="font-weight:500;">${formatValue(param.value, key)}</span>
          </div>`;
        });
        return result;
      }
    },
    legend: {
      data: props.series.map(s => s.name),
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.data.map(item => item.date),
      axisLabel: {
        rotate: 45,
        formatter: (value: string) => {
          // 简化日期显示
          const date = new Date(value);
          return `${date.getMonth() + 1}-${date.getDate()}`;
        }
      }
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series
  };
});

// 初始化图表
function initChart() {
  if (!chartRef.value) return;

  chartInstance = echarts.init(chartRef.value);
  if (chartOptions.value) {
    chartInstance.setOption(chartOptions.value);
  }
}

// 更新图表
function updateChart() {
  if (chartInstance && chartOptions.value) {
    chartInstance.setOption(chartOptions.value);
  }
}

// 监听数据变化
watch(
  () => props.data,
  () => {
    updateChart();
  },
  { deep: true }
);

// 窗口大小变化时自适应
function handleResize() {
  if (chartInstance) {
    chartInstance.resize();
  }
}

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
});
</script>

<template>
  <NCard title="趋势统计" :bordered="false" class="line-chart-card">
    <NSpin :show="loading">
      <div ref="chartRef" class="chart-container"></div>
    </NSpin>
  </NCard>
</template>

<style scoped>
.line-chart-card {
  width: 100%;
}

.chart-container {
  width: 100%;
  height: 350px;
}
</style>
