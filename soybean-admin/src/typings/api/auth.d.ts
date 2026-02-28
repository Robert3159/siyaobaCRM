declare namespace Api {
  /**
   * namespace Auth
   *
   * backend api module: "auth"
   */
  namespace Auth {
    /** 后端可能返回 access_token 或 token；登录/注册成功时带 user 可少请求一次 /auth/me，加快跳转 */
    interface LoginToken {
      token?: string;
      refreshToken?: string;
      access_token?: string;
      token_type?: string;
      user?: Api.Auth.MeResponse;
    }

    /** 注册接口：待审核时仅返回 registered + message，不返回 token */
    type RegisterResponse = LoginToken | { registered: true; message: string };

    interface UserInfo {
      userId: string;
      userName: string;
      roles: string[];
      buttons: string[];
      homeRoute: string | null;
      availableHomeRoutes: string[];
    }

    /** 后端 /auth/me 返回的当前用户（与 UserInfo 在 store 中做映射） */
    interface MeResponse {
      id: number;
      role: string;
      department_id: number | null;
      team_id: number | null;
      managed_team_ids?: number[];
      is_admin: boolean;
      home_route: string | null;
      available_home_routes: string[];
    }
  }
}
