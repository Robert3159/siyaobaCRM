"""
订单模块 Router
"""

import json
from datetime import datetime
from io import BytesIO
from typing import Annotated, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import and_, select

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.response import success_json
from app.services.order_service import (
    delete_field_mapping,
    get_field_mappings,
    get_import_log,
    get_system_fields,
    list_import_logs,
    list_orders,
    save_field_mappings,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Order, OrderImportLog, Player, Project

router = APIRouter()


@router.get("")
async def list_orders_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    project_id: int | None = Query(None),
    player_id: str | None = Query(None),
    qgs__author: int | None = Query(None),
    hgs_maintainer: int | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    sort_field: str | None = Query(None, pattern="^(order_time|amount|created_at)$"),
    sort_order: str | None = Query("desc", pattern="^(asc|desc)$"),
):
    """订单列表：分页、筛选、排序"""
    items, total = await list_orders(
        session,
        current_user,
        page=page,
        page_size=page_size,
        project_id=project_id,
        player_id=player_id,
        qgs__author=qgs__author,
        hgs_maintainer=hgs_maintainer,
        start_time=start_time,
        end_time=end_time,
        sort_field=sort_field or "created_at",
        sort_order=sort_order or "desc",
    )
    return success_json({
        "items": items,
        "total": total,
    })


@router.get("/field-mappings")
async def get_field_mappings_api(
    project_id: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_async_session),
):
    """获取字段映射配置"""
    mappings = await get_field_mappings(session, project_id)
    return success_json({
        "items": [
            {
                "id": m.id,
                "project_id": m.project_id,
                "file_field": m.file_field,
                "system_field": m.system_field,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            }
            for m in mappings
        ]
    })


@router.post("/field-mappings")
async def save_field_mappings_api(
    mappings: list[dict],
    project_id: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_async_session),
):
    """保存字段映射配置"""
    new_mappings = await save_field_mappings(session, project_id, mappings)
    return success_json({
        "items": [
            {
                "id": m.id,
                "project_id": m.project_id,
                "file_field": m.file_field,
                "system_field": m.system_field,
                "created_at": m.created_at,
            }
            for m in new_mappings
        ]
    })


@router.delete("/field-mappings/{mapping_id}")
async def delete_field_mapping_api(
    mapping_id: int,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """删除字段映射"""
    result = await delete_field_mapping(session, mapping_id)
    return success_json({"success": result})


@router.get("/system-fields")
async def get_system_fields_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """获取系统字段定义"""
    fields = await get_system_fields(session)
    return success_json([
        {
            "system_field": f.system_field,
            "field_label": f.field_label,
            "field_type": f.field_type,
            "aliases": f.aliases or [],
        }
        for f in fields
    ])


@router.get("/import-logs")
async def list_import_logs_api(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    project_id: int | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
):
    """获取导入日志列表"""
    items, total = await list_import_logs(
        session,
        current_user,
        page=page,
        page_size=page_size,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )
    return success_json({
        "items": items,
        "total": total,
    })


@router.get("/import-logs/{log_id}")
async def get_import_log_api(
    log_id: int,
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """获取导入日志详情"""
    log = await get_import_log(session, log_id)
    if not log:
        return success_json(None)
    return success_json(log)


@router.post("/preview")
async def preview_import_data(
    file: UploadFile = File(...),
    project_id: int = Query(..., ge=1),
    field_mapping: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """预览导入数据"""
    # 读取文件
    content = await file.read()
    filename = file.filename or ""

    if not filename:
        return success_json({"error": "文件名为空"})

    df = None
    if filename.endswith('.csv'):
        df = pd.read_csv(BytesIO(content))
    elif filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(BytesIO(content))
    else:
        return success_json({"error": "不支持的文件格式"})

    if df is None or df.empty:
        return success_json({"error": "文件为空"})

    # 获取表头
    headers = df.columns.tolist()

    # 解析字段映射
    mapping: dict = {}
    if field_mapping:
        try:
            mapping = json.loads(field_mapping)
        except json.JSONDecodeError:
            pass

    # 获取系统字段
    system_fields = await get_system_fields(session)
    system_field_map = {f.system_field: f for f in system_fields}

    # 自动匹配字段
    suggested_mapping: dict = {}
    for header in headers:
        # 精确匹配
        if header in system_field_map:
            suggested_mapping[header] = header
            continue
        # 别名匹配
        for sf, field in system_field_map.items():
            aliases = field.aliases or []
            if header in aliases:
                suggested_mapping[header] = sf
                break
        # 部分匹配
        if header not in suggested_mapping:
            for sf, field in system_field_map.items():
                if sf in header or header in sf:
                    suggested_mapping[header] = sf
                    break

    # 应用映射转换数据
    preview_data = []
    for _, row in df.head(10).iterrows():
        transformed: dict = {}
        raw_data: dict = {}
        for header in headers:
            value = row[header]
            if header in mapping:
                system_field = mapping[header]
                transformed[system_field] = value
            else:
                raw_data[header] = value
        if raw_data:
            transformed["_raw_data"] = raw_data
        preview_data.append(transformed)

    return success_json({
        "headers": headers,
        "preview_data": preview_data,
        "suggested_mapping": suggested_mapping,
        "total_rows": len(df),
    })


async def _match_player_gs(
    session: AsyncSession,
    project_id: int,
    player_id: str,
) -> tuple[int | None, int | None]:
    """根据 project_id 和 player_id 匹配 GS 归属"""
    # 获取 player_form 的字段定义
    form_stmt = select(Project).where(Project.id == project_id)
    form_result = await session.execute(form_stmt)
    project = form_result.scalars().first()

    if not project:
        return None, None

    # 查询 Player 表，匹配该字段
    # 假设 player_id 存储在 content 字段中
    player_stmt = select(Player).where(
        and_(
            Player.project_id == project_id,
            Player.is_deleted == False,
        )
    )
    player_result = await session.execute(player_stmt)
    players = player_result.scalars().all()

    # 查找匹配的 player
    matched_player = None
    for player in players:
        content = player.content or {}
        # 遍历 content 查找 player_id
        for key, value in content.items():
            if str(value) == player_id:
                matched_player = player
                break
        if matched_player:
            break

    if not matched_player:
        return None, None

    # 从 Player 的 owner_id 或相关字段获取 GS 归属
    qgs_author = matched_player.owner_id
    hgs_maintainer = matched_player.content.get("hgs_maintainer")

    return qgs_author, hgs_maintainer


@router.post("/import")
async def import_orders(
    file: UploadFile = File(...),
    project_id: int = Query(..., ge=1),
    field_mapping: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """导入订单"""
    # 读取文件
    content = await file.read()
    filename = file.filename or ""

    if not filename:
        return success_json({"error": "文件名为空"})

    df = None
    if filename.endswith('.csv'):
        df = pd.read_csv(BytesIO(content))
    elif filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(BytesIO(content))
    else:
        return success_json({"error": "不支持的文件格式"})

    if df is None or df.empty:
        return success_json({"error": "文件为空"})

    # 解析字段映射
    mapping: dict = {}
    if field_mapping:
        try:
            mapping = json.loads(field_mapping)
        except json.JSONDecodeError:
            pass

    # 创建导入日志
    import_log = OrderImportLog(
        project_id=project_id,
        filename=filename,
        total_rows=len(df),
        success_rows=0,
        fail_rows=0,
        import_user=None,
        status="processing",
    )
    session.add(import_log)
    await session.flush()

    success_count = 0
    fail_count = 0
    fail_details: list = []

    # 处理每行数据
    for row_num, (_, row) in enumerate(df.iterrows(), start=1):
        try:
            # 转换数据
            order_data: dict = {
                "project_id": project_id,
                "player_id": "",
                "amount": 0,
            }
            raw_data: dict = {}

            for header in df.columns:
                value = row[header]
                if header in mapping:
                    system_field = mapping[header]
                    order_data[system_field] = value
                else:
                    raw_data[header] = value

            # 验证必需字段
            if not order_data.get("player_id"):
                raise ValueError("缺少玩家ID")
            if not order_data.get("amount"):
                raise ValueError("缺少充值金额")

            # 匹配 GS 归属
            qgs_author, hgs_maintainer = await _match_player_gs(
                session, project_id, str(order_data["player_id"])
            )

            # 创建订单
            order = Order(
                project_id=project_id,
                order_no=order_data.get("order_no"),
                player_id=str(order_data["player_id"]),
                player_name=order_data.get("player_name"),
                server=order_data.get("server"),
                amount=order_data.get("amount", 0),
                order_time=order_data.get("order_time"),
                qgs__author=qgs_author,
                hgs_maintainer=hgs_maintainer,
                raw_data=raw_data if raw_data else None,
            )
            session.add(order)
            await session.flush()
            success_count += 1

        except Exception as e:
            fail_count += 1
            fail_details.append({
                "row": row_num,
                "error": str(e),
                "data": row.to_dict(),
            })

    # 更新导入日志
    import_log.success_rows = success_count
    import_log.fail_rows = fail_count
    import_log.fail_details = fail_details if fail_details else None
    import_log.status = "success" if fail_count == 0 else "completed"

    try:
        await session.commit()
    except Exception as e:
        # 回滚并返回错误
        await session.rollback()
        # 记录错误日志
        import_log.status = "failed"
        import_log.error_message = str(e)
        await session.commit()
        
        return success_json({
            "success": False,
            "total_rows": len(df),
            "success_rows": success_count,
            "fail_rows": fail_count,
            "log_id": import_log.id,
            "error": str(e),
        })

    return success_json({
        "success": fail_count == 0,
        "total_rows": len(df),
        "success_rows": success_count,
        "fail_rows": fail_count,
        "log_id": import_log.id,
        "fail_details": fail_details[:100],  # 限制返回数量
    })
