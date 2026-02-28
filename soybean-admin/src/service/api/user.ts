import { request } from '../request';

/** 仅保留有值的字段，避免传 undefined 导致后端 422 */
function cleanParams<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).filter(([_, v]) => v !== undefined && v !== null && v !== '')
  ) as Record<string, unknown>;
}

export function fetchUserList(params: { page?: number; page_size?: number; keyword?: string; role?: string }) {
  return request<Api.User.ListResult>({
    url: '/users',
    method: 'get',
    params: cleanParams({
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
      keyword: params.keyword,
      role: params.role
    })
  });
}

export function fetchDepartmentList() {
  return request<Api.User.DepartmentItem[]>({
    url: '/users/departments',
    method: 'get'
  });
}

export function createDepartment(data: { name: string }) {
  return request<Api.User.DepartmentItem>({
    url: '/users/departments',
    method: 'post',
    data
  });
}

export function fetchTeamList(departmentId?: number | null) {
  return request<Api.User.TeamItem[]>({
    url: '/users/teams',
    method: 'get',
    params: departmentId !== undefined && departmentId !== null ? { department_id: departmentId } : {}
  });
}

export function createTeam(data: { name: string; department_id: number }) {
  return request<Api.User.TeamItem>({
    url: '/users/teams',
    method: 'post',
    data
  });
}

export function fetchUserOptions(keyword?: string) {
  return request<Api.User.UserOption[]>({
    url: '/users/options',
    method: 'get',
    params: cleanParams({ keyword })
  });
}

export function fetchUser(id: number) {
  return request<Api.User.UserItem>({
    url: `/users/${id}`,
    method: 'get'
  });
}

export function updateUser(
  id: number,
  data: {
    role?: string | null;
    department_id?: number | null;
    team_id?: number | null;
    managed_team_ids?: number[] | null;
    manager_id?: number | null;
    managed_user_ids?: number[] | null;
    is_admin?: boolean | null;
    enabled?: boolean | null;
  }
) {
  return request<Api.User.UserItem>({
    url: `/users/${id}`,
    method: 'patch',
    data
  });
}

export function fetchMyProfile() {
  return request<Api.User.UserProfile>({
    url: '/users/profile',
    method: 'get'
  });
}

export function updateMyProfile(data: { user: string; alias: string | null; email: string; avatar: string | null }) {
  return request<Api.User.UserProfile>({
    url: '/users/profile',
    method: 'patch',
    data
  });
}
