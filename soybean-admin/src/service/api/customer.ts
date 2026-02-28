import { request } from '../request';

/** 仅保留有值的字段，避免传 undefined 导致后端 422 */
function cleanParams<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).filter(([_, v]) => v !== undefined && v !== null && v !== '')
  ) as Record<string, unknown>;
}

export function fetchCustomerList(params: { page?: number; page_size?: number; name?: string; contact?: string }) {
  return request<Api.Customer.ListResult>({
    url: '/customers',
    method: 'get',
    params: cleanParams({
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
      name: params.name,
      contact: params.contact
    })
  });
}

export function fetchCustomer(id: number) {
  return request<Api.Customer.Item>({
    url: `/customers/${id}`,
    method: 'get'
  });
}
