import asyncio
from app.core.database import async_session_factory
from app.services.notification_service import _extract_fields, _build_schema_candidates
from sqlalchemy import text

async def main():
    async with async_session_factory() as session:
        # 获取schema
        result = await session.execute(
            text('SELECT "fields" FROM "Form" WHERE "code" = :code'),
            {"code": "player_form"}
        )
        row = result.fetchone()
        schema_fields = row[0] if row else []
        
        # 获取真实玩家记录
        result = await session.execute(
            text('SELECT "id", "content" FROM "Player" ORDER BY "id" DESC LIMIT 1')
        )
        row = result.fetchone()
        if row:
            player_id = row[0]
            content = row[1]
            print(f"=== Player ID: {player_id} ===")
            print(f"Content keys: {list(content.keys())}")
            print()
            
            # 提取字段
            extracted = _extract_fields(content, f"Player{player_id}", schema_fields)
            print(f"Extracted fields:")
            for key, value in extracted.items():
                print(f"  {key}: '{value}'")

asyncio.run(main())
