import asyncio
from sqlalchemy import select
from app.core.database import get_async_session
from app.models import Player, User, Team


async def fix_data():
    async for session in get_async_session():
        # 1. 先修复 User 的 department_id（从 Team 表获取）
        print("=== 修复 User 的 department_id ===")
        users = (await session.execute(
            select(User).where(
                User.is_deleted == False,
                User.department_id == None,
                User.team_id != None
            )
        )).scalars().all()
        
        for user in users:
            team = (await session.execute(
                select(Team).where(Team.id == user.team_id)
            )).scalar_one_or_none()
            
            if team:
                user.department_id = team.department_id
                print(f"User {user.id} (Role: {user.role}): dept={team.department_id}, team={user.team_id}")
        
        await session.commit()
        print(f"修复了 {len(users)} 个用户的 department_id\n")
        
        # 2. 修复 Player 的 department_id 和 team_id
        print("=== 修复 Player 的 department_id 和 team_id ===")
        players = (await session.execute(
            select(Player).where(
                Player.is_deleted == False,
                (Player.department_id == None) | (Player.team_id == None)
            )
        )).scalars().all()
        
        for player in players:
            user = (await session.execute(
                select(User).where(User.id == player.owner_id)
            )).scalar_one_or_none()
            
            if user:
                player.department_id = user.department_id
                player.team_id = user.team_id
                print(f"Player {player.id} (Owner: {player.owner_id}): dept={user.department_id}, team={user.team_id}")
        
        await session.commit()
        print(f"\n修复了 {len(players)} 条 Player 记录")
        print("修复完成！")
        break


if __name__ == "__main__":
    asyncio.run(fix_data())
