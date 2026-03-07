import asyncio
from sqlalchemy import select
from app.core.database import get_async_session
from app.models import Player, User
from app.schemas.user import Role


async def fix_director_team_id():
    async for session in get_async_session():
        print("=== 修复 DIRECTOR 提交数据的 team_id ===\n")
        
        # 查找所有 DIRECTOR 及以上角色提交的 Player
        players = (await session.execute(
            select(Player).where(Player.is_deleted == False)
        )).scalars().all()
        
        fixed_count = 0
        
        for player in players:
            owner = (await session.execute(
                select(User).where(User.id == player.owner_id)
            )).scalar_one_or_none()
            
            if not owner:
                continue
            
            # DIRECTOR 及以上角色的数据不应该有 team_id
            if owner.role in ('QGS_DIRECTOR', 'HGS_DIRECTOR', 'SUB_ADMIN', 'ADMIN'):
                if player.team_id is not None:
                    print(f"Player {player.id} (Owner: {owner.id}, {owner.role}):")
                    print(f"  修复前: team_id={player.team_id}")
                    player.team_id = None
                    print(f"  修复后: team_id=None")
                    fixed_count += 1
        
        await session.commit()
        print(f"\n共修复 {fixed_count} 条记录")
        break


if __name__ == "__main__":
    asyncio.run(fix_director_team_id())
