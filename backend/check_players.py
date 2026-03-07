import asyncio
from app.core.database import async_session_factory
from sqlalchemy import text
import json

async def main():
    async with async_session_factory() as session:
        # 查看最近提交的玩家记录
        result = await session.execute(
            text('SELECT "id", "content" FROM "Player" ORDER BY "id" DESC LIMIT 3')
        )
        rows = result.fetchall()
        for row in rows:
            print(f'Player ID: {row[0]}')
            print(f'Content: {json.dumps(row[1], indent=2, ensure_ascii=False)}')
            print('-' * 80)

asyncio.run(main())
