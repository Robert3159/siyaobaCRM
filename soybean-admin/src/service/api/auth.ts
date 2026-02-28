import { request } from '../request';

/**
 * Login（用户名 user + 密码 + Turnstile token）
 */
export function fetchLogin(user: string, password: string, turnstileToken: string) {
  return request<Api.Auth.LoginToken>({
    url: '/auth/login',
    method: 'post',
    data: {
      user,
      password,
      turnstile_token: turnstileToken
    }
  });
}

/** Get user info（对接 /auth/me） */
export function fetchGetUserInfo() {
  return request<Api.Auth.MeResponse | null>({ url: '/auth/me' });
}

/** 发送邮箱验证码（用于注册） */
export function fetchSendEmailCode(email: string) {
  return request<Record<string, never>>({
    url: '/auth/send-email-code',
    method: 'post',
    data: { email }
  });
}

/** 注册（用户名 + 花名 + 邮箱 + 验证码 + 密码）；待审核时返回 registered + message，否则返回 LoginToken */
export function fetchRegister(payload: {
  user: string;
  alias: string;
  email: string;
  code: string;
  password: string;
  turnstile_token: string;
}) {
  return request<Api.Auth.RegisterResponse>({
    url: '/auth/register',
    method: 'post',
    data: payload
  });
}

export function fetchResetPasswordByEmail(payload: { email: string; code: string; password: string }) {
  return request<Record<string, never>>({
    url: '/auth/reset-password-by-email',
    method: 'post',
    data: payload
  });
}

/**
 * Refresh token
 *
 * @param refreshToken Refresh token
 */
export function fetchRefreshToken(refreshToken: string) {
  return request<Api.Auth.LoginToken>({
    url: '/auth/refreshToken',
    method: 'post',
    data: {
      refreshToken
    }
  });
}

/**
 * return custom backend error
 *
 * @param code error code
 * @param msg error message
 */
export function fetchCustomBackendError(code: string, msg: string) {
  return request({ url: '/auth/error', params: { code, msg } });
}
