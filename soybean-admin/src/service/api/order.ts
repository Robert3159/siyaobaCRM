/**
 * 订单模块 API 服务
 */

import { request } from '../request';

/** 仅保留有值的字段，避免传 undefined 导致后端 422 */
function cleanParams<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).filter(([_, v]) => v !== undefined && v !== null && v !== '')
  ) as Record<string, unknown>;
}

/** 获取订单列表 */
export function fetchOrderList(params: Api.Order.FetchParams) {
  return request<Api.Order.ListResult>({
    url: '/orders',
    method: 'get',
    params: cleanParams({
      page: params.page ?? 1,
      page_size: params.page_size ?? 50,
      project_id: params.project_id,
      player_id: params.player_id,
      qgs__author: params.qgs__author,
      hgs_maintainer: params.hgs_maintainer,
      start_time: params.start_time,
      end_time: params.end_time,
      sort_field: params.sort_field,
      sort_order: params.sort_order
    })
  });
}

/** 预览导入数据 */
export function fetchOrderImportPreview(file: File, projectId: number, fieldMapping?: Record<string, string>) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_id', String(projectId));
  if (fieldMapping) {
    formData.append('field_mapping', JSON.stringify(fieldMapping));
  }

  return request<Api.Order.FileParseResult>({
    url: '/orders/preview',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

/** 提交订单导入 */
export function submitOrderImport(file: File, projectId: number, fieldMapping?: Record<string, string>) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_id', String(projectId));
  if (fieldMapping) {
    formData.append('field_mapping', JSON.stringify(fieldMapping));
  }

  return request<Api.Order.ImportResult>({
    url: '/orders/import',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

/** 获取字段映射配置 */
export function fetchFieldMappings(projectId: number) {
  return request<{ items: Api.Order.FieldMapping[] }>({
    url: '/orders/field-mappings',
    method: 'get',
    params: { project_id: projectId }
  });
}

/** 保存字段映射配置 */
export function saveFieldMappings(projectId: number, mappings: Api.Order.FieldMappingPayload[]) {
  return request<{ items: Api.Order.FieldMapping[] }>({
    url: '/orders/field-mappings',
    method: 'post',
    params: { project_id: projectId },
    data: mappings
  });
}

/** 删除字段映射 */
export function deleteFieldMapping(id: number) {
  return request<{ success: boolean }>({
    url: `/orders/field-mappings/${id}`,
    method: 'delete'
  });
}

/** 获取导入日志列表 */
export function fetchImportLogs(params: {
  project_id?: number;
  page?: number;
  page_size?: number;
  start_date?: string;
  end_date?: string;
}) {
  return request<{ items: Api.Order.ImportLog[]; total: number }>({
    url: '/orders/import-logs',
    method: 'get',
    params: cleanParams(params)
  });
}

/** 获取导入日志详情 */
export function fetchImportLogDetail(id: number) {
  return request<Api.Order.ImportLog>({
    url: `/orders/import-logs/${id}`,
    method: 'get'
  });
}

/** 获取系统字段定义 */
export function fetchSystemFields() {
  return request<Api.Order.SystemField[]>({
    url: '/orders/system-fields',
    method: 'get'
  });
}
