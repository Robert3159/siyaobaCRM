"""
统计模块 Router - QGS 和 HGS 通用统计接口
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import CurrentUserDepRequired
from app.core.response import success_json
from app.services import statistics_service

router = APIRouter()


@router.get("/qgs/statistics")
async def get_qgs_statistics(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """
    QGS 统计聚合接口
    
    返回数据:
    {
        today: { new_registrations, paying_users, total_amount },
        yesterday: { new_registrations, paying_users, total_amount },
        last_7_days: { new_registrations, paying_users, total_amount },
        this_month: { new_registrations, paying_users, total_amount },
        all_time: { new_registrations, paying_users, total_amount }
    }
    """
    user_id = current_user.id
    
    today = await statistics_service.get_qgs_statistics(session, user_id, "today")
    yesterday = await statistics_service.get_qgs_statistics(session, user_id, "yesterday")
    last_7_days = await statistics_service.get_qgs_statistics(session, user_id, "last_7_days")
    this_month = await statistics_service.get_qgs_statistics(session, user_id, "this_month")
    all_time = await statistics_service.get_qgs_statistics(session, user_id, "all_time")
    
    return success_json({
        "today": today,
        "yesterday": yesterday,
        "last_7_days": last_7_days,
        "this_month": this_month,
        "all_time": all_time
    })


@router.get("/hgs/statistics")
async def get_hgs_statistics(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
):
    """
    HGS 统计聚合接口
    
    返回数据:
    {
        today: { connected_users, new_paying_users, total_amount },
        yesterday: { connected_users, new_paying_users, total_amount },
        last_7_days: { connected_users, new_paying_users, total_amount },
        this_month: { connected_users, new_paying_users, total_amount },
        all_time: { connected_users, new_paying_users, total_amount }
    }
    """
    user_id = current_user.id
    
    today = await statistics_service.get_hgs_statistics(session, user_id, "today")
    yesterday = await statistics_service.get_hgs_statistics(session, user_id, "yesterday")
    last_7_days = await statistics_service.get_hgs_statistics(session, user_id, "last_7_days")
    this_month = await statistics_service.get_hgs_statistics(session, user_id, "this_month")
    all_time = await statistics_service.get_hgs_statistics(session, user_id, "all_time")
    
    return success_json({
        "today": today,
        "yesterday": yesterday,
        "last_7_days": last_7_days,
        "this_month": this_month,
        "all_time": all_time
    })


@router.get("/qgs/statistics/daily")
async def get_qgs_daily_statistics(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    sort_field: str = Query("date", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    QGS 每日明细接口
    """
    user_id = current_user.id
    
    result = await statistics_service.get_qgs_daily_statistics(
        session=session,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        sort_field=sort_field,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    return success_json(result)


@router.get("/hgs/statistics/daily")
async def get_hgs_daily_statistics(
    current_user: CurrentUserDepRequired,
    session: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    sort_field: str = Query("date", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    HGS 每日明细接口
    """
    user_id = current_user.id
    
    result = await statistics_service.get_hgs_daily_statistics(
        session=session,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        sort_field=sort_field,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    return success_json(result)
