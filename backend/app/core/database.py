from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base

_db_url = settings.database_url or "postgresql+asyncpg://localhost/postgres"
if _db_url.startswith("postgresql://") and "asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    _db_url,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def _run_startup_migrations() -> None:
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE "Project" ALTER COLUMN department_id DROP NOT NULL'))
        await conn.execute(text('ALTER TABLE "Project" ALTER COLUMN team_id DROP NOT NULL'))
        await conn.execute(text('ALTER TABLE "Player" ALTER COLUMN department_id DROP NOT NULL'))
        await conn.execute(text('ALTER TABLE "Player" ALTER COLUMN team_id DROP NOT NULL'))
        await conn.execute(text('ALTER TABLE "User" ADD COLUMN IF NOT EXISTS avatar TEXT'))
        await conn.execute(text('ALTER TABLE "User" ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE'))
        await conn.execute(text(
            'ALTER TABLE "User" ADD COLUMN IF NOT EXISTS managed_team_ids JSONB NOT NULL DEFAULT \'[]\'::jsonb'
        ))
        await conn.execute(text('ALTER TABLE "User" ADD COLUMN IF NOT EXISTS manager_id INTEGER'))
        await conn.execute(text(
            'CREATE TABLE IF NOT EXISTS "SystemRole" ('
            'id SERIAL PRIMARY KEY, '
            'role_name VARCHAR(64) NOT NULL UNIQUE, '
            'home_route VARCHAR(64) NULL, '
            'created_at TIMESTAMP NOT NULL DEFAULT NOW(), '
            'updated_at TIMESTAMP NOT NULL DEFAULT NOW()'
            ')'
        ))
        await conn.execute(text('ALTER TABLE "SystemRole" ADD COLUMN IF NOT EXISTS home_route VARCHAR(64)'))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_startup_migrations()


async def dispose_db() -> None:
    await engine.dispose()
