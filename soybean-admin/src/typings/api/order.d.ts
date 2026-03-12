/**
 * 订单模块类型定义
 */

declare namespace Api {
  namespace Order {
    /** 订单项 */
    interface Item {
      id: number;
      project_id: number;
      project_name?: string;
      order_no: string | null;
      player_id: string;
      player_name: string | null;
      server: string | null;
      amount: number;
      order_time: string | null;
      qgs__author: number | null;
      qgs__author_name?: string;
      hgs_maintainer: number | null;
      hgs_maintainer_name?: string;
      raw_data: Record<string, unknown> | null;
      fail_reason?: string;
      created_at: string;
      updated_at?: string;
    }

    /** 订单列表响应 */
    interface ListResult {
      items: Api.Order.Item[];
      total: number;
    }

    /** 订单查询参数 */
    interface FetchParams {
      page?: number;
      page_size?: number;
      project_id?: number;
      player_id?: string;
      qgs__author?: number;
      hgs_maintainer?: number;
      start_time?: string;
      end_time?: string;
      sort_field?: 'order_time' | 'amount' | 'created_at';
      sort_order?: 'asc' | 'desc';
    }

    /** 导入请求 payload */
    interface ImportPayload {
      project_id: number;
      field_mapping: Record<string, string>;
    }

    /** 导入结果 */
    interface ImportResult {
      success: boolean;
      total_rows: number;
      success_rows: number;
      fail_rows: number;
      log_id: number;
      fail_details?: Array<{ row: number; error: string; data: unknown }>;
    }

    /** 字段映射 - 后端保存时使用 */
    interface FieldMappingPayload {
      file_field: string;
      system_field: string;
    }

    /** 字段映射 - 完整类型 */
    interface FieldMapping {
      id?: number;
      project_id: number;
      file_field: string;
      system_field: string;
      created_at?: string;
      updated_at?: string;
    }

    /** 导入日志 */
    interface ImportLog {
      id: number;
      project_id: number;
      project_name?: string;
      filename: string;
      total_rows: number;
      success_rows: number;
      fail_rows: number;
      fail_details?: unknown;
      import_user: number;
      import_user_name?: string;
      status: 'pending' | 'processing' | 'success' | 'failed';
      error_message?: string;
      created_at: string;
      updated_at?: string;
    }

    /** 文件解析结果 */
    interface FileParseResult {
      headers: string[];
      preview_data: Record<string, unknown>[];
      suggested_mapping: Record<string, string>;
      total_rows: number;
    }

    /** 系统字段定义 */
    interface SystemField {
      system_field: string;
      field_label: string;
      field_type: string;
      aliases: string[];
    }
  }
}
