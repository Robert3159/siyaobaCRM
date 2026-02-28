import { request } from '../request';

/** 仅保留有值的字段，避免传 undefined 导致后端 422 */
function cleanParams<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).filter(([_, v]) => v !== undefined && v !== null && v !== '')
  ) as Record<string, unknown>;
}

export function fetchProjectList(params: { page?: number; page_size?: number; name?: string; enabled?: boolean }) {
  return request<Api.Project.ListResult>({
    url: '/projects',
    method: 'get',
    params: cleanParams({
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
      name: params.name,
      enabled: params.enabled
    })
  });
}

export function fetchProject(id: number) {
  return request<Api.Project.Item>({
    url: `/projects/${id}`,
    method: 'get'
  });
}

export function createProject(data: { name: string; date?: string | null; remark?: string | null }) {
  return request<Api.Project.Item>({
    url: '/projects',
    method: 'post',
    data
  });
}

export function updateProject(
  id: number,
  data: { name?: string; date?: string | null; remark?: string | null; enabled?: boolean }
) {
  return request<Api.Project.Item>({
    url: `/projects/${id}`,
    method: 'patch',
    data
  });
}
