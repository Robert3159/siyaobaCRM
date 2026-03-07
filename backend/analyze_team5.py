import asyncio
from sqlalchemy import select
from app.core.database import get_async_session
from app.models import Player, User


async def analyze_team5_data():
    async for session in get_async_session():
        print("=== Team 5 的所有数据分析 ===\n")
        
        # 获取 Team 5 的所有 Player
        players = (await session.execute(
            select(Player).where(
                Player.is_deleted == False,
                Player.team_id == 5
            )
        )).scalars().all()
        
        print(f"Team 5 共有 {len(players)} 条 Player 记录:\n")
        
        for p in sorted(players, key=lambda x: x.id):
            owner = (await session.execute(
                select(User).where(User.id == p.owner_id)
            )).scalar_one_or_none()
            
            print(f"Player {p.id}:")
            print(f"  Owner: {p.owner_id} ({owner.role if owner else 'N/A'})")
            print(f"  Owner Team: {owner.team_id if owner else 'N/A'}")
            print(f"  Player Team: {p.team_id}")
            
            # 判断 LEADER 是否应该看到
            if owner and owner.role in ('QGS_DIRECTOR', 'HGS_DIRECTOR'):
                print(f"  ⚠️ 这是 DIRECTOR 提交的，LEADER 不应该看到！")
            print()
        
        break


if __name__ == "__main__":
    asyncio.run(analyze_team5_data())
