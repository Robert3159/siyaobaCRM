declare namespace Api {
  namespace Project {
    interface Item {
      id: number;
      project_no: string;
      name: string;
      date: string | null;
      remark: string | null;
      enabled: boolean;
      created_at: string;
      updated_at: string;
    }
    interface ListResult {
      items: Api.Project.Item[];
      total: number;
    }
  }

  namespace Schema {
    type FormFieldType =
      | 'single_line_text'
      | 'multi_line_text'
      | 'radio'
      | 'checkbox'
      | 'select'
      | 'select_multiple'
      | 'number'
      | 'datetime'
      | 'upload_attachment'
      | 'upload_image'
      | 'color'
      | 'project';

    interface FormFieldDef {
      key?: string;
      label: string;
      type: FormFieldType | string;
      required?: boolean;
      options?: unknown[];
      order?: number;
      visible_pages?: string[];
      visible_roles?: string[];
      editable_roles?: string[];
      readonly_roles?: string[];
    }
    interface Item {
      id: number;
      name: string;
      code: string;
      enabled: boolean;
      fields: Api.Schema.FormFieldDef[];
      created_at: string;
      updated_at: string;
    }
    interface ListResult {
      items: Api.Schema.Item[];
      total: number;
    }
  }

  namespace Player {
    interface Item {
      id: number;
      project_id: number;
      content: Record<string, unknown>;
      owner_id: number;
      department_id: number | null;
      team_id: number | null;
      created_at: string;
      updated_at: string;
    }
    interface ListResult {
      items: Api.Player.Item[];
      total: number;
    }
    interface SubmitPayload {
      project_id: number;
      content: Record<string, unknown>;
    }
    interface UpdatePayload {
      project_id?: number;
      content?: Record<string, unknown>;
    }
  }

  namespace Customer {
    interface Item {
      id: number;
      name: string;
      contact: string | null;
      owner_id: number;
      department_id: number;
      team_id: number;
      created_at: string;
      updated_at: string;
    }
    interface ListResult {
      items: Api.Customer.Item[];
      total: number;
    }
  }

  namespace Role {
    interface RoleItem {
      role: string;
      label: string;
    }
    interface PermissionOption {
      code: string;
      label: string;
    }
    interface RolePermissionsResponse {
      role: string;
      permissions: string[];
    }
    interface RoleMenuItem {
      id: number;
      menu_type: number;
      menu_name: string;
      route_name: string;
      route_path: string;
      parent_id: number | null;
      children: Api.Role.RoleMenuItem[];
    }
    interface RoleDetail {
      role: string;
      label: string;
      permissions: string[];
      home_route: string | null;
      available_home_routes: string[];
      menu_tree: Api.Role.RoleMenuItem[];
      updated_at: string | null;
    }
    interface RoleUpdatePayload {
      permissions: string[];
      home_route: string | null;
    }
  }

  namespace User {
    interface UserItem {
      id: number;
      user: string;
      alias: string | null;
      email: string;
      role: string;
      department_id: number | null;
      team_id: number | null;
      managed_team_ids?: number[];
      manager_id?: number | null;
      manager_name?: string | null;
      managed_user_ids?: number[];
      managed_user_names?: string[];
      department_name?: string | null;
      team_name?: string | null;
      managed_team_names?: string[];
      is_admin: boolean;
      enabled: boolean;
      created_at: string;
      updated_at?: string;
    }
    interface ListResult {
      items: Api.User.UserItem[];
      total: number;
    }
    interface DepartmentItem {
      id: number;
      name: string;
    }
    interface TeamItem {
      id: number;
      name: string;
      department_id: number;
    }
    interface UserOption {
      id: number;
      user: string;
      alias?: string | null;
      role: string;
    }

    interface UserProfile {
      id: number;
      user: string;
      alias: string | null;
      email: string;
      role: string;
      avatar: string | null;
      department_id: number | null;
      team_id: number | null;
      managed_team_ids?: number[];
      manager_id?: number | null;
      manager_name?: string | null;
      managed_user_ids?: number[];
      managed_user_names?: string[];
      department_name?: string | null;
      team_name?: string | null;
      managed_team_names?: string[];
      is_admin: boolean;
      enabled: boolean;
      created_at: string;
      updated_at: string;
    }
  }

  namespace Menu {
    type MenuType = 1 | 2 | 3;

    interface Item {
      id: number;
      menu_type: MenuType;
      menu_name: string;
      icon: string | null;
      route_name: string;
      route_path: string;
      status: boolean;
      hide_in_menu: boolean;
      order: number;
      parent_id: number | null;
      children: Api.Menu.Item[];
      created_at: string;
      updated_at: string;
    }

    interface CreatePayload {
      menu_type: MenuType;
      menu_name: string;
      icon?: string | null;
      route_name: string;
      route_path: string;
      status: boolean;
      hide_in_menu: boolean;
      order: number;
      parent_id: number | null;
    }

    interface UpdatePayload {
      menu_name?: string;
      icon?: string | null;
      route_name?: string;
      route_path?: string;
      status?: boolean;
      hide_in_menu?: boolean;
      order?: number;
    }
  }
}
