/**
 * 统计模块 API 服务
 */

import { request } from '../request';

/** 仅保留有值的字段 */
function cleanParams<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).filter(([_, v]) => v !== undefined && v !== null && v !== '')
  ) as Record<string, unknown>;
}

// ============ QGS 统计 API ============

/** 获取 QGS 统计聚合数据 */
export function fetchQgsStatistics() {
  return request<Api.Statistics.QgsStatisticsResponse>({
    url: '/qgs/statistics',
    method: 'get'
  });
}

/** 获取 QGS 每日明细 */
export function fetchQgsDailyStatistics(params: Api.Statistics.DailyStatisticsParams = {}) {
  return request<Api.Statistics.QgsDailyStatisticsResponse>({
    url: '/qgs/statistics/daily',
    method: 'get',
    params: cleanParams({
      start_date: params.start_date,
      end_date: params.end_date,
      sort_field: params.sort_field,
      sort_order: params.sort_order,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20
    })
  });
}

// ============ HGS 统计 API ============

/** 获取 HGS 统计聚合数据 */
export function fetchHgsStatistics() {
  return request<Api.Statistics.HgsStatisticsResponse>({
    url: '/hgs/statistics',
    method: 'get'
  });
}

/** 获取 HGS 每日明细 */
export function fetchHgsDailyStatistics(params: Api.Statistics.DailyStatisticsParams = {}) {
  return request<Api.Statistics.HgsDailyStatisticsResponse>({
    url: '/hgs/statistics/daily',
    method: 'get',
    params: cleanParams({
      start_date: params.start_date,
      end_date: params.end_date,
      sort_field: params.sort_field,
      sort_order: params.sort_order,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20
    })
  });
}

// ============ 统一导出 ============

/** 根据 preset 获取统计聚合数据 */
export function fetchStatistics(preset: 'qgs' | 'hgs') {
  if (preset === 'qgs') {
    return fetchQgsStatistics();
  }
  return fetchHgsStatistics();
}

/** 根据 preset 获取每日明细 */
export function fetchDailyStatistics(preset: 'qgs' | 'hgs', params: Api.Statistics.DailyStatisticsParams = {}) {
  if (preset === 'qgs') {
    return fetchQgsDailyStatistics(params);
  }
  return fetchHgsDailyStatistics(params);
}
