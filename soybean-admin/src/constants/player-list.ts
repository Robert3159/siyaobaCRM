/**
 * 鐜╁鍒楄〃鍒楀彲瑙佹€ч厤缃紙鍓嶇鎺у埗锛夈€? * 鍚庣鍙帶鍒舵暟鎹鑼冨洿锛泀gs_list / hgs_list 浣跨敤鍚屼竴鎺ュ彛 GET /api/players锛屼笉鍚屽垪閰嶇疆銆? */

/** 鍩虹鍒楋紙鎵€鏈夎鍥惧潎鍙€夋樉绀猴級 */
export const PLAYER_BASE_COLUMNS = ['id', 'project_id', 'created_at'] as const;

/** 鎺ㄥ箍宸ヤ綔鍙?qgs) 榛樿灞曠ず鐨?content 瀛楁 key */
export const QGS_CONTENT_KEYS = ['name', 'phone', 'register_time', 'promoter', 'qgs_author', 'hgs_maintainer'] as const;

/** 鍥㈤暱宸ヤ綔鍙?hgs) 榛樿灞曠ず鐨?content 瀛楁 key */
export const HGS_CONTENT_KEYS = ['name', 'phone', 'leader', 'order_no', 'qgs_author', 'hgs_maintainer'] as const;

export type PlayerListPreset = 'full' | 'qgs' | 'hgs';
