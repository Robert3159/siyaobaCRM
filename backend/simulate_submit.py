import asyncio
from app.core.database import async_session_factory
from app.models import Player
from app.services.notification_service import build_notification_message, notification_hub
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
        
        print("Schema fields count:", len(schema_fields))
        
        # 模拟提交的content
        content = {
            "fld_78959fae4078": "中国",  # 国家
            "fld_e073e40f144d": "25",    # 年龄
            "fld_76076e69d48a": "美服1",  # 区服
            "fld_2a7326b789dd": "TOKEN123", # Token码
        }
        
        # 构建通知消息
        message = build_notification_message(
            content=content,
            submitter="测试用户",
            player_id=999,
            schema_fields=schema_fields
        )
        
        print("\n=== Built Notification Message ===")
        print(f"ID: {message.id}")
        print(f"Player ID: {message.player_id}")
        print(f"Country: '{message.country}'")
        print(f"Age: '{message.age}'")
        print(f"Server: '{message.server}'")
        print(f"Token: '{message.token}'")
        print(f"Submitter: '{message.submitter}'")
        print(f"Summary: '{message.summary}'")
        print(f"Created at: {message.created_at}")
        
        # 检查消息dict
        print("\n=== Message to_dict() ===")
        msg_dict = message.to_dict()
        for key, value in msg_dict.items():
            print(f"{key}: '{value}'")

asyncio.run(main())
