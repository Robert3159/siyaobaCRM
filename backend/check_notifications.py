import asyncio
from app.core.database import async_session_factory
from app.services.notification_service import notification_hub
from sqlalchemy import text

async def main():
    # 查看当前的通知消息
    messages = notification_hub._messages
    print(f"=== Current notification messages count: {len(messages)} ===")
    for msg in messages:
        print(f"ID: {msg.id}")
        print(f"Player ID: {msg.player_id}")
        print(f"Country: {msg.country}")
        print(f"Age: {msg.age}")
        print(f"Server: {msg.server}")
        print(f"Token: {msg.token}")
        print(f"Submitter: {msg.submitter}")
        print(f"Summary: {msg.summary}")
        print(f"Created at: {msg.created_at}")
        print('-' * 80)

asyncio.run(main())
