import asyncio
from app.core.database import async_session_factory
from sqlalchemy import text
import json

async def main():
    async with async_session_factory() as session:
        result = await session.execute(
            text('SELECT "code", "fields" FROM "Form" WHERE "code" = :code'),
            {"code": "player_form"}
        )
        row = result.fetchone()
        if row:
            print(f'Code: {row[0]}')
            print(f'Fields:\n{json.dumps(row[1], indent=2, ensure_ascii=False)}')
        else:
            print("No player_form found")

asyncio.run(main())
