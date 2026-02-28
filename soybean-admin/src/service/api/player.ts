import { request } from '../request';

/** 仅保留有值的字段，避免传 undefined 导致后端 422 */
function cleanParams<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).filter(([_, v]) => v !== undefined && v !== null && v !== '')
  ) as Record<string, unknown>;
}

export interface FetchPlayerListParams {
  page?: number;
  page_size?: number;
  project_id?: number;
  player_id?: number;
  alias?: string;
  server?: string;
  keyword?: string;
  start_time?: string;
  end_time?: string;
}

export function fetchPlayerList(params: FetchPlayerListParams) {
  return request<Api.Player.ListResult>({
    url: '/players',
    method: 'get',
    params: cleanParams({
      page: params.page ?? 1,
      page_size: params.page_size ?? 50,
      project_id: params.project_id,
      player_id: params.player_id,
      alias: params.alias,
      server: params.server,
      keyword: params.keyword,
      start_time: params.start_time,
      end_time: params.end_time
    })
  });
}

export function submitPlayer(payload: Api.Player.SubmitPayload) {
  return request<Api.Player.Item>({
    url: '/players',
    method: 'post',
    data: payload
  });
}

export function updatePlayer(id: number, payload: Api.Player.UpdatePayload) {
  return request<Api.Player.Item>({
    url: `/players/${id}`,
    method: 'patch',
    data: payload
  });
}
