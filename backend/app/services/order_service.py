"""
订单模块 Service 层
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models import Order, OrderFieldMapping, OrderImportLog, OrderSystemField, Project, User, Player
from app.schemas.user import CurrentUser, Role

logger = logging.getLogger(__name__)

# 玩家ID字段的key（从player_form schema配置）
PLAYER_ID_KEY = "fld_69f9b1e5c01d"
QGS_AUTHOR_KEY = "qgs_author"
HGS_MAINTAINER_KEY = "hgs_maintainer"


async def list_orders(
    session: AsyncSession,
    user: CurrentUser,
    page: int = 1,
    page_size: int = 50,
    project_id: Optional[int] = None,
    player_id: Optional[str] = None,
    qgs__author: Optional[int] = None,
    hgs_maintainer: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    sort_field: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[dict], int]:
    """获取订单列表"""
    # 基础过滤条件
    base_conditions = [Order.is_deleted == False]

    # 基于角色的数据权限过滤
    if user.role in (Role.ADMIN, Role.SUB_ADMIN):
        pass  # 查看全部
    elif user.role in (Role.QGS_DIRECTOR, Role.HGS_DIRECTOR):
        if user.department_id is not None:
            base_conditions.append(Order.qgs__author.in_(
                select(User.id).where(
                    and_(User.department_id == user.department_id, User.is_deleted == False)
                )
            ))
    elif user.role in (Role.QGS_LEADER, Role.HGS_LEADER):
        if user.team_id is not None:
            base_conditions.append(Order.qgs__author.in_(
                select(User.id).where(
                    and_(User.team_id == user.team_id, User.is_deleted == False)
                )
            ))
    else:  # MEMBER
        base_conditions.append(Order.qgs__author == user.id)

    # 构建查询
    query = select(Order).where(and_(*base_conditions))

    # 添加筛选条件
    if project_id is not None:
        query = query.where(Order.project_id == project_id)
    if player_id and player_id.strip():
        query = query.where(Order.player_id.ilike(f"%{player_id.strip()}%"))
    if qgs__author is not None:
        query = query.where(Order.qgs__author == qgs__author)
    if hgs_maintainer is not None:
        query = query.where(Order.hgs_maintainer == hgs_maintainer)
    if start_time is not None:
        query = query.where(Order.order_time >= start_time)
    if end_time is not None:
        query = query.where(Order.order_time <= end_time)

    # 排序
    sort_column = getattr(Order, sort_field, Order.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # 获取总数
    total_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_stmt)).scalar() or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    orders = list(result.scalars().all())

    # 转换为响应格式，添加关联信息
    items = []
    for order in orders:
        item = {
            "id": order.id,
            "project_id": order.project_id,
            "order_no": order.order_no,
            "player_id": order.player_id,
            "player_name": order.player_name,
            "server": order.server,
            "amount": float(order.amount) if order.amount else 0,
            "order_time": order.order_time,
            "qgs__author": order.qgs__author,
            "hgs_maintainer": order.hgs_maintainer,
            "raw_data": order.raw_data,
            "fail_reason": order.fail_reason,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "project_name": None,
            "qgs__author_name": None,
            "hgs_maintainer_name": None,
        }
        items.append(item)

    # 批量获取项目名称
    project_ids = list(set([o.project_id for o in orders]))
    if project_ids:
        project_stmt = select(Project).where(Project.id.in_(project_ids))
        project_result = await session.execute(project_stmt)
        project_map = {p.id: p.name for p in project_result.scalars().all()}
        for item in items:
            item["project_name"] = project_map.get(item["project_id"])

    # 批量获取玩家表中的GS归属（根据player_id查询）
    # 玩家表中玩家ID存储在content字段的fld_69f9b1e5c01d中
    player_ids = list(set([o.player_id for o in orders if o.player_id]))
    player_gs_map = {}
    if player_ids:
        # 查询玩家表，根据content->>fld_69f9b1e5c01d匹配player_id
        player_stmt = select(Player).where(
            and_(
                Player.is_deleted == False,
                Player.content[PLAYER_ID_KEY].astext.in_(player_ids)
            )
        )
        player_result = await session.execute(player_stmt)
        for player in player_result.scalars().all():
            player_id = player.content.get(PLAYER_ID_KEY)
            if player_id:
                player_gs_map[player_id] = {
                    "qgs_author": player.content.get(QGS_AUTHOR_KEY),
                    "hgs_maintainer": player.content.get(HGS_MAINTAINER_KEY)
                }
        
        # 将玩家表中的GS归属设置到订单项
        for item in items:
            if item["player_id"] in player_gs_map:
                gs_info = player_gs_map[item["player_id"]]
                if gs_info["qgs_author"]:
                    item["qgs__author_name"] = gs_info["qgs_author"]
                if gs_info["hgs_maintainer"]:
                    item["hgs_maintainer_name"] = gs_info["hgs_maintainer"]

    # 如果玩家表中没有找到对应的GS归属，则使用订单表中存储的用户ID查询用户表（兼容旧数据）
    # 找出仍未设置名称的订单
    orders_without_player_gs = [
        item for item in items 
        if (item["qgs__author"] and not item["qgs__author_name"]) or 
           (item["hgs_maintainer"] and not item["hgs_maintainer_name"])
    ]
    
    if orders_without_player_gs:
        author_ids = list(set([item["qgs__author"] for item in orders_without_player_gs if item["qgs__author"]]))
        maintainer_ids = list(set([item["hgs_maintainer"] for item in orders_without_player_gs if item["hgs_maintainer"]]))
        all_user_ids = set(author_ids) | set(maintainer_ids)
        
        if all_user_ids:
            user_stmt = select(User).where(User.id.in_(all_user_ids))
            user_result = await session.execute(user_stmt)
            user_map = {u.id: u.alias or u.user for u in user_result.scalars().all()}
            
            for item in orders_without_player_gs:
                if item["qgs__author"] and not item["qgs__author_name"]:
                    item["qgs__author_name"] = user_map.get(item["qgs__author"])
                if item["hgs_maintainer"] and not item["hgs_maintainer_name"]:
                    item["hgs_maintainer_name"] = user_map.get(item["hgs_maintainer"])

    return items, total


async def get_field_mappings(
    session: AsyncSession,
    project_id: int,
) -> list[OrderFieldMapping]:
    """获取字段映射配置"""
    stmt = select(OrderFieldMapping).where(
        and_(
            OrderFieldMapping.project_id == project_id,
            OrderFieldMapping.is_deleted == False,
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def save_field_mappings(
    session: AsyncSession,
    project_id: int,
    mappings: list[dict],
) -> list[OrderFieldMapping]:
    """保存字段映射配置"""
    # 先删除旧的映射
    stmt = select(OrderFieldMapping).where(
        and_(
            OrderFieldMapping.project_id == project_id,
            OrderFieldMapping.is_deleted == False,
        )
    )
    result = await session.execute(stmt)
    old_mappings = list(result.scalars().all())
    for mapping in old_mappings:
        mapping.is_deleted = True
        mapping.deleted_at = datetime.utcnow()

    # 创建新的映射
    new_mappings = []
    for m in mappings:
        mapping = OrderFieldMapping(
            project_id=project_id,
            file_field=m["file_field"],
            system_field=m["system_field"],
        )
        session.add(mapping)
        new_mappings.append(mapping)

    await session.flush()
    return new_mappings


async def delete_field_mapping(
    session: AsyncSession,
    mapping_id: int,
) -> bool:
    """删除字段映射"""
    stmt = select(OrderFieldMapping).where(
        and_(
            OrderFieldMapping.id == mapping_id,
            OrderFieldMapping.is_deleted == False,
        )
    )
    result = await session.execute(stmt)
    mapping = result.scalars().first()
    if mapping:
        mapping.is_deleted = True
        mapping.deleted_at = datetime.utcnow()
        await session.flush()
        return True
    return False


async def get_system_fields(
    session: AsyncSession,
) -> list[OrderSystemField]:
    """获取系统字段定义"""
    stmt = select(OrderSystemField)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_import_logs(
    session: AsyncSession,
    user: CurrentUser,
    page: int = 1,
    page_size: int = 50,
    project_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> tuple[list[dict], int]:
    """获取导入日志列表"""
    base_conditions = [OrderImportLog.is_deleted == False]

    # 基于角色的数据权限过滤
    user_role = str(user.role) if user.role else ""
    if user_role not in ("ADMIN", "SUB_ADMIN"):
        base_conditions.append(OrderImportLog.import_user == user.id)

    if project_id is not None:
        base_conditions.append(OrderImportLog.project_id == project_id)
    if start_date is not None:
        base_conditions.append(OrderImportLog.created_at >= start_date)
    if end_date is not None:
        base_conditions.append(OrderImportLog.created_at <= end_date)

    query = select(OrderImportLog).where(and_(*base_conditions))
    query = query.order_by(OrderImportLog.id.desc())

    # 总数
    total_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_stmt)).scalar() or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    logs = list(result.scalars().all())

    # 转换为响应格式
    items = []
    for log in logs:
        item = {
            "id": log.id,
            "project_id": log.project_id,
            "filename": log.filename,
            "total_rows": log.total_rows,
            "success_rows": log.success_rows,
            "fail_rows": log.fail_rows,
            "fail_details": log.fail_details,
            "import_user": log.import_user,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at,
            "updated_at": log.updated_at,
            "project_name": None,
            "import_user_name": None,
        }
        items.append(item)

    # 批量获取项目名称
    project_ids = list(set([log.project_id for log in logs]))
    if project_ids:
        project_stmt = select(Project.id, Project.name).where(Project.id.in_(project_ids))
        project_result = await session.execute(project_stmt)
        project_map = {p.id: p.name for p in project_result.scalars().all()}
        for item in items:
            item["project_name"] = project_map.get(item["project_id"])

    # 批量获取用户名称
    user_ids = list(set([log.import_user for log in logs if log.import_user]))
    if user_ids:
        user_stmt = select(User.id, User.alias, User.user).where(User.id.in_(user_ids))
        user_result = await session.execute(user_stmt)
        user_map = {u.id: u.alias or u.user for u in user_result.scalars().all()}
        for item in items:
            if item["import_user"]:
                item["import_user_name"] = user_map.get(item["import_user"])

    return items, total


async def get_import_log(
    session: AsyncSession,
    log_id: int,
) -> Optional[dict]:
    """获取导入日志详情"""
    stmt = select(OrderImportLog).where(
        and_(
            OrderImportLog.id == log_id,
            OrderImportLog.is_deleted == False,
        )
    )
    result = await session.execute(stmt)
    log = result.scalars().first()
    if not log:
        return None

    return {
        "id": log.id,
        "project_id": log.project_id,
        "filename": log.filename,
        "total_rows": log.total_rows,
        "success_rows": log.success_rows,
        "fail_rows": log.fail_rows,
        "fail_details": log.fail_details,
        "import_user": log.import_user,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": log.created_at,
        "updated_at": log.updated_at,
    }
