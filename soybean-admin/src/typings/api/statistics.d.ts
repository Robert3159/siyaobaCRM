/**
 * 统计模块类型定义
 */

declare namespace Api {
  namespace Statistics {
    // ============ QGS 统计类型 ============

    /** QGS 统计数据 */
    interface QgsStatisticsData {
      new_registrations: number;
      paying_users: number;
      total_amount: number;
    }

    /** QGS 统计聚合响应 */
    interface QgsStatisticsResponse {
      today: QgsStatisticsData;
      yesterday: QgsStatisticsData;
      last_7_days: QgsStatisticsData;
      this_month: QgsStatisticsData;
      all_time: QgsStatisticsData;
    }

    // ============ HGS 统计类型 ============

    /** HGS 统计数据 */
    interface HgsStatisticsData {
      connected_users: number;
      new_paying_users: number;
      total_amount: number;
    }

    /** HGS 统计聚合响应 */
    interface HgsStatisticsResponse {
      today: HgsStatisticsData;
      yesterday: HgsStatisticsData;
      last_7_days: HgsStatisticsData;
      this_month: HgsStatisticsData;
      all_time: HgsStatisticsData;
    }

    // ============ 每日明细类型 ============

    /** QGS 每日明细项 */
    interface QgsDailyStatisticsItem {
      date: string;
      new_registrations: number;
      paying_users: number;
      total_amount: number;
    }

    /** HGS 每日明细项 */
    interface HgsDailyStatisticsItem {
      date: string;
      connected_users: number;
      new_paying_users: number;
      total_amount: number;
    }

    /** QGS 每日明细汇总 */
    interface QgsDailyStatisticsSummary {
      total_new_registrations: number;
      total_paying_users: number;
      total_amount: number;
    }

    /** HGS 每日明细汇总 */
    interface HgsDailyStatisticsSummary {
      total_connected_users: number;
      total_new_paying_users: number;
      total_amount: number;
    }

    /** 每日明细响应 - QGS */
    interface QgsDailyStatisticsResponse {
      items: QgsDailyStatisticsItem[];
      total: number;
      summary: QgsDailyStatisticsSummary;
    }

    /** 每日明细响应 - HGS */
    interface HgsDailyStatisticsResponse {
      items: HgsDailyStatisticsItem[];
      total: number;
      summary: HgsDailyStatisticsSummary;
    }

    // ============ 查询参数类型 ============

    /** 每日明细查询参数 */
    interface DailyStatisticsParams {
      start_date?: string;
      end_date?: string;
      sort_field?: string;
      sort_order?: 'asc' | 'desc';
      page?: number;
      page_size?: number;
    }
  }
}

// ============ 前端组件 Props 类型 ============

/** 统计卡片 Props */
interface StatCardProps {
  title: string;
  value: number | string;
  type?: 'number' | 'currency';
  icon?: string;
  loading?: boolean;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
  };
}

/** 统计卡片组 Props */
interface StatCardGroupProps {
  preset: 'qgs' | 'hgs';
  loading?: boolean;
  data?: Api.Statistics.QgsStatisticsResponse | Api.Statistics.HgsStatisticsResponse;
}

/** 折线图 Props */
interface LineChartProps {
  data: Array<{ date: string; [key: string]: number | string }>;
  series: Array<{ key: string; name: string; color: string }>;
  loading?: boolean;
}

/** 柱状图 Props */
interface BarChartProps {
  data: Array<{ playerName: string; totalAmount: number }>;
  title?: string;
  loading?: boolean;
}

/** 数据表格 Props */
interface StatisticsTableProps {
  preset: 'qgs' | 'hgs';
  columns: Array<{
    key: string;
    title: string;
    sorter?: boolean;
  }>;
  data: Api.Statistics.QgsDailyStatisticsItem[] | Api.Statistics.HgsDailyStatisticsItem[];
  loading?: boolean;
  total: number;
  page: number;
  pageSize: number;
}

/** 统计页面 Props */
interface StatisticsPageProps {
  /** 角色标识: 'qgs' | 'hgs' */
  preset: 'qgs' | 'hgs';
}
