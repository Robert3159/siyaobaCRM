import { request } from '../request';

/** 仅保留有值的字段，避免传 undefined 导致后端 422 */
function cleanParams<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).filter(([_, v]) => v !== undefined && v !== null && v !== '')
  ) as Record<string, unknown>;
}

export function fetchSchemaList(params: { page?: number; page_size?: number; name?: string; enabled?: boolean }) {
  return request<Api.Schema.ListResult>({
    url: '/schemas',
    method: 'get',
    params: cleanParams({
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
      name: params.name,
      enabled: params.enabled
    })
  });
}

export function fetchSchemaByCode(code: string) {
  return request<Api.Schema.Item>({
    url: `/schemas/by-code/${encodeURIComponent(code)}`,
    method: 'get'
  });
}

export function fetchSchema(id: number) {
  return request<Api.Schema.Item>({
    url: `/schemas/${id}`,
    method: 'get'
  });
}

export function createSchema(data: {
  name: string;
  code: string;
  enabled?: boolean;
  fields: Api.Schema.FormFieldDef[];
}) {
  return request<Api.Schema.Item>({
    url: '/schemas',
    method: 'post',
    data
  });
}

export function updateSchema(
  id: number,
  data: {
    name?: string;
    enabled?: boolean;
    fields?: Api.Schema.FormFieldDef[];
  }
) {
  return request<Api.Schema.Item>({
    url: `/schemas/${id}`,
    method: 'patch',
    data
  });
}
