import asyncio
from sqlalchemy import select
from app.core.database import get_async_session
from app.models import Player, User


async def check_data():
    async for session in get_async_session():
        # 检查 Player 数据
        players = (await session.execute(
            select(Player.id, Player.owner_id, Player.department_id, Player.team_id)
            .where(Player.is_deleted == False)
            .limit(20)
        )).all()
        
        print("=== Player 数据 ===")
        for p in players:
            print(f"ID: {p.id}, Owner: {p.owner_id}, Dept: {p.department_id}, Team: {p.team_id}")
        
        # 检查 User 数据
        users = (await session.execute(
            select(User.id, User.role, User.department_id, User.team_id)
            .where(User.is_deleted == False)
        )).all()
        
        print("\n=== User 数据 ===")
        for u in users:
            print(f"ID: {u.id}, Role: {u.role}, Dept: {u.department_id}, Team: {u.team_id}")
        
        break


if __name__ == "__main__":
    asyncio.run(check_data())
