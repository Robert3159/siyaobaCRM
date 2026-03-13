"""
系统配置 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.core.response import success_json
from app.models.base import SystemConfig
from app.schemas.user import CurrentUser

router = APIRouter(prefix="/system-config", tags=["系统配置"])


class SystemConfigSchema(BaseModel):
    key: str
    value: Optional[dict] = None
    description: Optional[str] = None


class SystemConfigUpdate(BaseModel):
    value: dict


@router.get("/{key}")
async def get_config(key: str, session: AsyncSession = Depends(get_async_session)):
    """获取系统配置"""
    result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return success_json(config)


@router.put("/{key}")
async def update_config(
    key: str,
    config_update: SystemConfigUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """更新系统配置（仅 ADMIN 可操作）"""
    # 检查权限：仅 ADMIN 可以修改系统配置
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权限操作")

    result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    
    if not config:
        # 创建新配置
        config = SystemConfig(key=key, value=config_update.value)
        session.add(config)
    else:
        config.value = config_update.value

    await session.commit()
    await session.refresh(config)
    return success_json(config)
