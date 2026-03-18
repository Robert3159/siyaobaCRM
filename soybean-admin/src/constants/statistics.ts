/**
 * 统计模块通用配置
 */

/** 统计预设类型 */
export type StatisticsPreset = 'qgs' | 'hgs';

/** 指标定义 */
export interface StatMetric {
  key: string;
  label: string;
  icon?: string;
}

/** 统计预设配置 */
export interface StatisticsPresetConfig {
  api: string;
  dailyApi: string;
  metrics: StatMetric[];
}

/** 统计配置 */
export const STATISTICS_CONFIG: Record<StatisticsPreset, StatisticsPresetConfig> = {
  qgs: {
    api: '/api/qgs/statistics',
    dailyApi: '/api/qgs/statistics/daily',
    metrics: [
      { key: 'new_registrations', label: '新增注册', icon: 'mdi:account-plus' },
      { key: 'paying_users', label: '付费人数', icon: 'mdi:account-cash' },
      { key: 'total_amount', label: '付费金额', icon: 'mdi:cash-multiple' }
    ]
  },
  hgs: {
    api: '/api/hgs/statistics',
    dailyApi: '/api/hgs/statistics/daily',
    metrics: [
      { key: 'connected_users', label: '对接数量', icon: 'mdi:account-group' },
      { key: 'new_paying_users', label: '新增付费', icon: 'mdi:account-plus' },
      { key: 'total_amount', label: '付费金额', icon: 'mdi:cash-multiple' }
    ]
  }
} as const;

/** 时间范围选项 */
export const TIME_RANGE_OPTIONS = [
  { label: '今日', value: 'today' },
  { label: '昨日', value: 'yesterday' },
  { label: '近7日', value: 'last_7_days' },
  { label: '本月', value: 'this_month' },
  { label: '全部', value: 'all_time' }
] as const;

/** 时间段标签 */
export const TIME_RANGE_LABELS: Record<string, string> = {
  today: '今日',
  yesterday: '昨日',
  last_7_days: '近7日',
  this_month: '本月',
  all_time: '全部'
};

/** 卡片时间范围 */
export const CARD_TIME_RANGES = ['today', 'yesterday', 'last_7_days', 'this_month', 'all_time'] as const;

/** 默认分页配置 */
export const DEFAULT_PAGINATION = {
  page: 1,
  pageSize: 20
};

/** 表格列配置 - QGS */
export const QGS_TABLE_COLUMNS = [
  { key: 'date', title: '日期', sorter: true },
  { key: 'new_registrations', title: '新增注册', sorter: true },
  { key: 'paying_users', title: '付费人数', sorter: true },
  { key: 'total_amount', title: '付费金额', sorter: true }
] as const;

/** 表格列配置 - HGS */
export const HGS_TABLE_COLUMNS = [
  { key: 'date', title: '日期', sorter: true },
  { key: 'connected_users', title: '对接数量', sorter: true },
  { key: 'new_paying_users', title: '新增付费', sorter: true },
  { key: 'total_amount', title: '付费金额', sorter: true }
] as const;

/** 获取表格列配置 */
export function getTableColumns(preset: StatisticsPreset) {
  return preset === 'qgs' ? QGS_TABLE_COLUMNS : HGS_TABLE_COLUMNS;
}

/** 格式化金额 */
export function formatCurrency(value: number | string): string {
  const num = typeof value === 'string' ? Number.parseFloat(value) : value;
  if (Number.isNaN(num)) return '¥0.00';
  return `¥${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** 格式化数字 */
export function formatNumber(value: number | string): string {
  const num = typeof value === 'string' ? Number.parseInt(value, 10) : value;
  if (Number.isNaN(num)) return '0';
  return num.toLocaleString('zh-CN');
}
