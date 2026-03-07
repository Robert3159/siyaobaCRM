"""清理未使用的团队"""
import asyncio
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.base import Team, User

async def cleanup_unused_teams():
    async with async_session_factory() as session:
        # 查询所有团队
        teams_result = await session.execute(select(Team).where(Team.is_deleted == False))
        teams = teams_result.scalars().all()
        
        print(f"\n找到 {len(teams)} 个团队:")
        for team in teams:
            print(f"  ID: {team.id}, 名称: {team.name}, 部门ID: {team.department_id}")
        
        # 查询所有用户使用的团队ID
        users_result = await session.execute(
            select(User.team_id).where(User.team_id.isnot(None), User.is_deleted == False)
        )
        used_team_ids = set(row[0] for row in users_result.all())
        
        print(f"\n正在使用的团队ID: {used_team_ids}")
        
        # 找出未使用的团队
        unused_teams = [t for t in teams if t.id not in used_team_ids]
        
        if not unused_teams:
            print("\n没有未使用的团队")
            return
        
        print(f"\n未使用的团队 ({len(unused_teams)} 个):")
        for team in unused_teams:
            print(f"  ID: {team.id}, 名称: {team.name}")
        
        # 直接删除
        for team in unused_teams:
            team.is_deleted = True
        await session.commit()
        print(f"\n已删除 {len(unused_teams)} 个未使用的团队")

if __name__ == "__main__":
    asyncio.run(cleanup_unused_teams())
