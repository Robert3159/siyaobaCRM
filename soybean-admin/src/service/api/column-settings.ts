import { request } from '../request';

/** 列设置的数据结构 */
export interface ColumnSettings {
  staticColumnWidths?: Record<string, number>;
  fieldColumnWidths?: Record<string, number>;
  fieldOrder?: string[];
}

/**
 * 获取全局列设置
 * @param preset 预设类型：qgs、hgs、full
 */
export function fetchColumnSettings(preset: string) {
  const key = `player-list-${preset}`;
  return request<{ key: string; value: ColumnSettings }>({
    url: `/system-config/${key}`,
    method: 'get'
  });
}

/**
 * 更新全局列设置（仅 ADMIN 可调用）
 * @param preset 预设类型：qgs、hgs、full
 * @param settings 列设置数据
 */
export function updateColumnSettings(preset: string, settings: ColumnSettings) {
  const key = `player-list-${preset}`;
  return request<{ key: string; value: ColumnSettings }>({
    url: `/system-config/${key}`,
    method: 'put',
    data: { value: settings }
  });
}
