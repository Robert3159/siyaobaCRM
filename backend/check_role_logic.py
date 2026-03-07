import asyncio
from sqlalchemy import select
from app.core.database import get_async_session
from app.models import User


async def check_roles():
    async for session in get_async_session():
        users = (await session.execute(
            select(User).where(User.is_deleted == False)
            .order_by(User.id)
        )).scalars().all()
        
        print("=== 用户角色和归属 ===\n")
        for u in users:
            print(f"User {u.id}: {u.role:20s} Dept={u.department_id}, Team={u.team_id}")
        
        print("\n=== 问题分析 ===")
        print("User 9 (QGS_DIRECTOR) 的 team_id=5")
        print("User 7 (QGS_LEADER) 的 team_id=5")
        print("\n按照当前逻辑:")
        print("- DIRECTOR 提交数据时，Player.team_id = 5")
        print("- LEADER 查询时，WHERE team_id = 5")
        print("- 结果：LEADER 能看到 DIRECTOR 的数据")
        print("\n这是否符合业务需求？")
        print("选项1: DIRECTOR 虽然属于某个 team，但提交的数据应该只有 department_id，不应有 team_id")
        print("选项2: LEADER 只能看到 MEMBER 提交的数据，不能看到同 team 的 DIRECTOR 数据")
        
        break

asyncio.run(check_roles())
