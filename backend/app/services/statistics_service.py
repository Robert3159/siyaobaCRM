"""
统计模块 Service
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Player
from app.models.base import User


async def get_beijing_now() -> datetime:
    """获取当前北京时间"""
    # UTC + 8 = 北京时间
    return datetime.utcnow() + timedelta(hours=8)


def get_date_range(period: str, reference_date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """
    获取指定时间范围的开始和结束时间（北京时间）
    
    Args:
        period: 时间范围标识 (today, yesterday, last_7_days, this_month, all_time)
        reference_date: 参考日期，默认为今天
    
    Returns:
        (start_datetime, end_datetime) 元组
    """
    # 同步计算基准日期（使用北京时间）
    if reference_date is None:
        # 同步方式获取北京时间
        reference_date = datetime.utcnow() + timedelta(hours=8)
    
    today = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if period == "today":
        # 今日：当天 00:00:00 ~ 23:59:59
        start = today
        end = today.replace(hour=23, minute=59, second=59)
    elif period == "yesterday":
        # 昨日
        yesterday = today - timedelta(days=1)
        start = yesterday
        end = yesterday.replace(hour=23, minute=59, second=59)
    elif period == "last_7_days":
        # 过去7天（含今天）
        start = today - timedelta(days=6)
        end = today.replace(hour=23, minute=59, second=59)
    elif period == "this_month":
        # 当月1日 ~ 当月最后一天
        start = today.replace(day=1)
        # 计算月末
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(seconds=1)
    else:
        # all_time - 无限制
        start = datetime(1970, 1, 1)
        end = datetime(2099, 12, 31, 23, 59, 59)
    
    return start, end


def build_order_paid_condition(start: datetime, end: datetime, author_field, user_id: int):
    """
    构建订单付费条件
    
    逻辑：
    - 如果 status 字段存在且不为空，使用 status = 'paid'
    - 否则使用 amount > 0 作为判断条件
    """
    from sqlalchemy import or_
    
    # 基础条件
    base_conditions = [
        author_field == user_id,
        Order.order_time >= start,
        Order.order_time <= end,
        Order.is_deleted == False
    ]
    
    # 付费条件：status = 'paid' OR (status IS NULL AND amount > 0)
    paid_condition = or_(
        Order.status == 'paid',
        and_(Order.status == None, Order.amount > 0)
    )
    
    return and_(*base_conditions, paid_condition)


async def get_qgs_statistics(session: AsyncSession, user_id: int, period: str) -> dict:
    """
    获取 QGS 统计指定时间段的数据
    
    Args:
        session: 数据库会话
        user_id: 当前用户 ID（QGS）
        period: 时间范围标识
    
    Returns:
        {
            "new_registrations": int,  # 新增注册数
            "paying_users": int,         # 付费人数
            "total_amount": float        # 付费金额
        }
    """
    start, end = get_date_range(period)
    
    # 1. 新增注册：COUNT(players) WHERE owner_id = user_id AND created_at BETWEEN start AND end
    new_registrations_stmt = select(func.count(Player.id)).where(
        and_(
            Player.owner_id == user_id,
            Player.created_at >= start,
            Player.created_at <= end,
            Player.is_deleted == False
        )
    )
    new_registrations_result = await session.execute(new_registrations_stmt)
    new_registrations = new_registrations_result.scalar() or 0
    
    # 2. 付费人数：COUNT(DISTINCT player_id) FROM orders WHERE qgs__author = user_id AND (status='paid' OR (status IS NULL AND amount > 0))
    order_condition = build_order_paid_condition(start, end, Order.qgs__author, user_id)
    paying_users_stmt = select(func.count(func.distinct(Order.player_id))).where(order_condition)
    paying_users_result = await session.execute(paying_users_stmt)
    paying_users = paying_users_result.scalar() or 0
    
    # 3. 付费金额：SUM(amount) FROM orders WHERE qgs__author = user_id AND (status='paid' OR (status IS NULL AND amount > 0))
    total_amount_stmt = select(func.sum(Order.amount)).where(order_condition)
    total_amount_result = await session.execute(total_amount_stmt)
    total_amount = total_amount_result.scalar() or 0.0
    
    return {
        "new_registrations": new_registrations,
        "paying_users": paying_users,
        "total_amount": float(total_amount)
    }


async def get_hgs_statistics(session: AsyncSession, user_id: int, period: str) -> dict:
    """
    获取 HGS 统计指定时间段的数据
    
    Args:
        session: 数据库会话
        user_id: 当前用户 ID（HGS）
        period: 时间范围标识
    
    Returns:
        {
            "connected_users": int,    # 对接数量
            "new_paying_users": int,   # 新增付费人数
            "total_amount": float      # 付费金额
        }
    """
    start, end = get_date_range(period)
    
    # 1. 对接数量：COUNT(DISTINCT player_id) FROM orders WHERE hgs_maintainer = user_id
    # 使用付费条件：status='paid' OR (status IS NULL AND amount > 0)
    hgs_order_condition = build_order_paid_condition(start, end, Order.hgs_maintainer, user_id)
    connected_users_stmt = select(func.count(func.distinct(Order.player_id))).where(
        and_(
            Order.hgs_maintainer == user_id,
            Order.order_time >= start,
            Order.order_time <= end,
            Order.is_deleted == False
        )
    )
    connected_users_result = await session.execute(connected_users_stmt)
    connected_users = connected_users_result.scalar() or 0
    
    # 2. 新增付费：首次付费时间在统计周期内的玩家数
    # 子查询：获取每个玩家的最早付费时间（使用付费条件）
    earliest_pay_subquery = select(
        Order.player_id,
        func.min(Order.order_time).label('first_pay_time')
    ).where(
        and_(
            Order.hgs_maintainer == user_id,
            or_(Order.status == 'paid', and_(Order.status == None, Order.amount > 0)),
            Order.is_deleted == False
        )
    ).group_by(Order.player_id).subquery()
    
    # 统计首次付费时间在查询范围内的玩家数
    new_paying_users_stmt = select(func.count(func.distinct(earliest_pay_subquery.c.player_id))).where(
        and_(
            earliest_pay_subquery.c.first_pay_time >= start,
            earliest_pay_subquery.c.first_pay_time <= end
        )
    )
    new_paying_users_result = await session.execute(new_paying_users_stmt)
    new_paying_users = new_paying_users_result.scalar() or 0
    
    # 3. 付费金额：SUM(amount) FROM orders WHERE hgs_maintainer = user_id AND (status='paid' OR (status IS NULL AND amount > 0))
    total_amount_stmt = select(func.sum(Order.amount)).where(hgs_order_condition)
    total_amount_result = await session.execute(total_amount_stmt)
    total_amount = total_amount_result.scalar() or 0.0
    
    return {
        "connected_users": connected_users,
        "new_paying_users": new_paying_users,
        "total_amount": float(total_amount)
    }


async def get_qgs_daily_statistics(
    session: AsyncSession,
    user_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_field: str = "date",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20
) -> dict:
    """
    获取 QGS 每日明细统计
    
    Args:
        session: 数据库会话
        user_id: 当前用户 ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        sort_field: 排序字段
        sort_order: 排序方向
        page: 页码
        page_size: 每页数量
    
    Returns:
        {
            "items": [...],
            "total": int,
            "summary": {...}
        }
    """
    from sqlalchemy import cast, Date
    
    # 解析日期
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
    else:
        start_dt = (datetime.utcnow() + timedelta(hours=8) - timedelta(days=30)).replace(hour=0, minute=0, second=0)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    else:
        end_dt = (datetime.utcnow() + timedelta(hours=8)).replace(hour=23, minute=59, second=59)
    
    # 构建基础查询条件
    base_condition = and_(
        Order.qgs__author == user_id,
        Order.amount > 0,
        Order.order_time >= start_dt,
        Order.order_time <= end_dt,
        Order.is_deleted == False
    )
    
    # 获取日期分组的数据
    # 1. 付费金额和付费人数（按日期分组）
    daily_orders_stmt = select(
        cast(Order.order_time, Date).label('date'),
        func.count(func.distinct(Order.player_id)).label('paying_users'),
        func.sum(Order.amount).label('total_amount')
    ).where(
        base_condition
    ).group_by(
        cast(Order.order_time, Date)
    ).order_by(
        cast(Order.order_time, Date).desc() if sort_order == "desc" else cast(Order.order_time, Date)
    )
    
    orders_result = await session.execute(daily_orders_stmt)
    order_data = {row.date: {"paying_users": row.paying_users, "total_amount": row.total_amount} 
                  for row in orders_result.fetchall()}
    
    # 2. 新增注册（按日期分组）
    player_base_condition = and_(
        Player.owner_id == user_id,
        Player.created_at >= start_dt,
        Player.created_at <= end_dt,
        Player.is_deleted == False
    )
    
    daily_players_stmt = select(
        cast(Player.created_at, Date).label('date'),
        func.count(Player.id).label('new_registrations')
    ).where(
        player_base_condition
    ).group_by(
        cast(Player.created_at, Date)
    )
    
    players_result = await session.execute(daily_players_stmt)
    player_data = {row.date: {"new_registrations": row.new_registrations} 
                   for row in players_result.fetchall()}
    
    # 合并数据
    all_dates = set(order_data.keys()) | set(player_data.keys())
    items = []
    
    for date in sorted(all_dates, reverse=(sort_order == "desc")):
        items.append({
            "date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
            "new_registrations": player_data.get(date, {}).get("new_registrations", 0),
            "paying_users": order_data.get(date, {}).get("paying_users", 0),
            "total_amount": float(order_data.get(date, {}).get("total_amount", 0) or 0)
        })
    
    # 计算分页
    total = len(items)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]
    
    # 计算汇总
    summary = {
        "total_new_registrations": sum(item["new_registrations"] for item in items),
        "total_paying_users": sum(item["paying_users"] for item in items),
        "total_amount": sum(item["total_amount"] for item in items)
    }
    
    return {
        "items": paginated_items,
        "total": total,
        "summary": summary
    }


async def get_hgs_daily_statistics(
    session: AsyncSession,
    user_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_field: str = "date",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20
) -> dict:
    """
    获取 HGS 每日明细统计
    """
    from sqlalchemy import cast, Date
    
    # 解析日期
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
    else:
        start_dt = (datetime.utcnow() + timedelta(hours=8) - timedelta(days=30)).replace(hour=0, minute=0, second=0)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    else:
        end_dt = (datetime.utcnow() + timedelta(hours=8)).replace(hour=23, minute=59, second=59)
    
    # 基础查询条件
    base_condition = and_(
        Order.hgs_maintainer == user_id,
        Order.amount > 0,
        Order.order_time >= start_dt,
        Order.order_time <= end_dt,
        Order.is_deleted == False
    )
    
    # 获取日期分组的数据（对接数量和付费金额）
    daily_orders_stmt = select(
        cast(Order.order_time, Date).label('date'),
        func.count(func.distinct(Order.player_id)).label('connected_users'),
        func.sum(Order.amount).label('total_amount')
    ).where(
        base_condition
    ).group_by(
        cast(Order.order_time, Date)
    ).order_by(
        cast(Order.order_time, Date).desc() if sort_order == "desc" else cast(Order.order_time, Date)
    )
    
    orders_result = await session.execute(daily_orders_stmt)
    order_data = {row.date: {"connected_users": row.connected_users, "total_amount": row.total_amount} 
                  for row in orders_result.fetchall()}
    
    # 获取新增付费（首次付费在当日）
    # 先获取每个玩家的首次付费时间
    earliest_pay_subquery = select(
        Order.player_id,
        func.min(Order.order_time).label('first_pay_time')
    ).where(
        and_(
            Order.hgs_maintainer == user_id,
            Order.amount > 0,
            Order.is_deleted == False
        )
    ).group_by(Order.player_id).subquery()
    
    # 统计每日新增付费
    daily_new_paying_stmt = select(
        cast(earliest_pay_subquery.c.first_pay_time, Date).label('date'),
        func.count(func.distinct(earliest_pay_subquery.c.player_id)).label('new_paying_users')
    ).where(
        and_(
            earliest_pay_subquery.c.first_pay_time >= start_dt,
            earliest_pay_subquery.c.first_pay_time <= end_dt
        )
    ).group_by(
        cast(earliest_pay_subquery.c.first_pay_time, Date)
    )
    
    new_paying_result = await session.execute(daily_new_paying_stmt)
    new_paying_data = {row.date: {"new_paying_users": row.new_paying_users} 
                        for row in new_paying_result.fetchall()}
    
    # 合并数据
    all_dates = set(order_data.keys()) | set(new_paying_data.keys())
    items = []
    
    for date in sorted(all_dates, reverse=(sort_order == "desc")):
        items.append({
            "date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
            "connected_users": order_data.get(date, {}).get("connected_users", 0),
            "new_paying_users": new_paying_data.get(date, {}).get("new_paying_users", 0),
            "total_amount": float(order_data.get(date, {}).get("total_amount", 0) or 0)
        })
    
    # 计算分页
    total = len(items)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]
    
    # 计算汇总
    summary = {
        "total_connected_users": sum(item["connected_users"] for item in items),
        "total_new_paying_users": sum(item["new_paying_users"] for item in items),
        "total_amount": sum(item["total_amount"] for item in items)
    }
    
    return {
        "items": paginated_items,
        "total": total,
        "summary": summary
    }
