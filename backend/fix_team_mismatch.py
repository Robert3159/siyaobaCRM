import asyncio
from sqlalchemy import select, and_
from app.core.database import get_async_session
from app.models import Player, User


async def fix_team_mismatch():
    async for session in get_async_session():
        print("=== 修复 Player 与 Owner 的 team_id 不一致问题 ===\n")
        
        # 查找所有 Player
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
            
            # 检查是否需要更新
            needs_update = False
            old_dept = player.department_id
            old_team = player.team_id
            
            if player.department_id != owner.department_id:
                player.department_id = owner.department_id
                needs_update = True
            
            if player.team_id != owner.team_id:
                player.team_id = owner.team_id
                needs_update = True
            
            if needs_update:
                print(f"Player {player.id} (Owner: {owner.id}, {owner.role}):")
                print(f"  修复前: dept={old_dept}, team={old_team}")
                print(f"  修复后: dept={player.department_id}, team={player.team_id}")
                fixed_count += 1
        
        await session.commit()
        print(f"\n共修复 {fixed_count} 条记录")
        break


if __name__ == "__main__":
    asyncio.run(fix_team_mismatch())
