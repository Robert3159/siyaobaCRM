<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { NCard, NEmpty, NSpin } from 'naive-ui';
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { GridComponent, TitleComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { formatCurrency } from '@/constants/statistics';

// 注册 ECharts 组件
echarts.use([BarChart, TitleComponent, TooltipComponent, GridComponent, CanvasRenderer]);

interface Props {
  data: Array<{ playerName: string; totalAmount: number }>;
  title?: string;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: '玩家充值排行',
  loading: false
});

const chartRef = ref<HTMLDivElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

// 取前10名数据
const chartData = computed(() => {
  const sortedData = [...props.data].sort((a, b) => b.totalAmount - a.totalAmount);
  return sortedData.slice(0, 10);
});

// 图表配置
const chartOptions = computed(() => {
  if (!chartData.value.length) return null;

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any[]) => {
        const data = params[0];
        return `<div style="font-weight:bold;">${data.name}</div>
          <div>充值金额: ${formatCurrency(data.value)}</div>`;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      },
      axisLabel: {
        formatter: (value: number) => formatCurrency(value)
      }
    },
    yAxis: {
      type: 'category',
      data: chartData.value.map(d => d.playerName).reverse(),
      axisLabel: {
        width: 100,
        overflow: 'truncate'
      }
    },
    series: [
      {
        name: '充值金额',
        type: 'bar',
        data: chartData.value.map(d => d.totalAmount).reverse(),
        itemStyle: {
          color: '#409eff',
          borderRadius: [0, 4, 4, 0]
        },
        barWidth: '60%',
        label: {
          show: true,
          position: 'right',
          formatter: (params: any) => formatCurrency(params.value),
          color: '#666'
        }
      }
    ]
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
  <NCard :title="title" :bordered="false" class="bar-chart-card">
    <NSpin :show="loading">
      <NEmpty v-if="!chartData.length && !loading" description="暂无数据" />
      <div v-else ref="chartRef" class="chart-container"></div>
    </NSpin>
  </NCard>
</template>

<style scoped>
.bar-chart-card {
  width: 100%;
}

.chart-container {
  width: 100%;
  height: 400px;
}
</style>
