import { request } from '../request';

/** 角色项 */
export function fetchRoleList() {
  return request<Api.Role.RoleItem[]>({
    url: '/system/roles',
    method: 'get'
  });
}

/** 权限选项（供角色权限勾选） */
export function fetchPermissionOptions() {
  return request<Api.Role.PermissionOption[]>({
    url: '/system/permission-options',
    method: 'get'
  });
}

/** 获取某角色的权限列表 */
export function fetchRolePermissions(role: string) {
  return request<Api.Role.RolePermissionsResponse>({
    url: `/system/roles/${encodeURIComponent(role)}/permissions`,
    method: 'get'
  });
}

/** 获取某角色详情（含权限、首页、可访问菜单树） */
export function fetchRoleDetail(role: string) {
  return request<Api.Role.RoleDetail>({
    url: `/system/roles/${encodeURIComponent(role)}`,
    method: 'get'
  });
}

/** 更新某角色的权限（全量替换） */
export function updateRolePermissions(role: string, permissions: string[]) {
  return request<Api.Role.RolePermissionsResponse>({
    url: `/system/roles/${encodeURIComponent(role)}/permissions`,
    method: 'put',
    data: { permissions }
  });
}

/** 更新某角色配置（权限 + 首页） */
export function updateRole(role: string, payload: Api.Role.RoleUpdatePayload) {
  return request<Api.Role.RoleDetail>({
    url: `/system/roles/${encodeURIComponent(role)}`,
    method: 'put',
    data: payload
  });
}
