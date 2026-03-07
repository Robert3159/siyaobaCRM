import asyncio
from app.core.database import async_session_factory
from app.services.notification_service import _build_schema_candidates, _extract_fields, _normalize_key
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
        
        # 构建候选
        merged_candidates = _build_schema_candidates(schema_fields)
        
        print("=== Merged Candidates ===")
        for field, keys in merged_candidates.items():
            print(f"{field}: {keys}")
        
        print("\n=== Test with actual content ===")
        content = {
            "fld_78959fae4078": "China",  # 国家
            "fld_e073e40f144d": "25",    # 年龄
            "fld_76076e69d48a": "US-1",   # 区服
            "fld_2a7326b789dd": "ABC123", # Token码
        }
        
        extracted = _extract_fields(content, "test_user", schema_fields)
        print(f"Extracted: {extracted}")

asyncio.run(main())
