import { request } from '../request';

export function fetchMenuList() {
  return request<Api.Menu.Item[]>({
    url: '/system/menus',
    method: 'get'
  });
}

export function createMenu(data: Api.Menu.CreatePayload) {
  return request<Api.Menu.Item>({
    url: '/system/menus',
    method: 'post',
    data
  });
}

export function updateMenu(id: number, data: Api.Menu.UpdatePayload) {
  return request<Api.Menu.Item>({
    url: `/system/menus/${id}`,
    method: 'patch',
    data
  });
}

export function deleteMenu(id: number) {
  return request<{ deleted_count: number }>({
    url: `/system/menus/${id}`,
    method: 'delete'
  });
}

export function batchDeleteMenus(ids: number[]) {
  return request<{ deleted_count: number }>({
    url: '/system/menus/batch-delete',
    method: 'post',
    data: { ids }
  });
}
