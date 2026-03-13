"""
简单的内存缓存模块
用于缓存不经常变化的数据（如用户列表、项目列表）
"""

import asyncio
import time
from typing import Any, Callable, TypeVar, Optional
from functools import wraps

T = TypeVar('T')


class SimpleCache:
    """简单的内存缓存实现"""
    
    def __init__(self, ttl: int = 300, max_size: int = 100):
        """
        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
            max_size: 最大缓存条目数
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()
    
    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存 key"""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        return ":".join(key_parts)
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        async with self._lock:
            if key in self._cache:
                value, expire_at = self._cache[key]
                if time.time() < expire_at:
                    return value
                else:
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        async with self._lock:
            # 如果缓存已满，删除最早的条目
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            
            expire_at = time.time() + (ttl or self._ttl)
            self._cache[key] = (value, expire_at)
    
    async def delete(self, key: str) -> None:
        """删除缓存"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear(self) -> None:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
    
    def get_sync(self, key: str) -> Optional[Any]:
        """同步获取缓存（不推荐用于生产环境）"""
        if key in self._cache:
            value, expire_at = self._cache[key]
            if time.time() < expire_at:
                return value
            else:
                del self._cache[key]
        return None
    
    def set_sync(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """同步设置缓存（不推荐用于生产环境）"""
        expire_at = time.time() + (ttl or self._ttl)
        self._cache[key] = (value, expire_at)


# 全局缓存实例
_user_cache = SimpleCache(ttl=300, max_size=200)  # 用户缓存，5分钟过期
_project_cache = SimpleCache(ttl=300, max_size=100)  # 项目缓存，5分钟过期


def get_user_cache() -> SimpleCache:
    """获取用户缓存实例"""
    return _user_cache


def get_project_cache() -> SimpleCache:
    """获取项目缓存实例"""
    return _project_cache


async def cached_call(
    cache: SimpleCache,
    key: str,
    fetch_func: Callable[[], Any],
    ttl: Optional[int] = None,
) -> Any:
    """
    缓存调用包装器
    
    Args:
        cache: 缓存实例
        key: 缓存键
        fetch_func: 获取数据的异步函数
        ttl: 缓存过期时间（秒）
    
    Returns:
        缓存的数据或新获取的数据
    """
    # 尝试从缓存获取
    cached_value = await cache.get(key)
    if cached_value is not None:
        return cached_value
    
    # 缓存未命中，从数据库获取
    value = await fetch_func()
    
    # 存入缓存
    if value is not None:
        await cache.set(key, value, ttl)
    
    return value
