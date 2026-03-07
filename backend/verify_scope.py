import asyncio
from sqlalchemy import select, and_
from app.core.database import get_async_session
from app.core.scope import build_scope_filter
from app.models import Player, User
from app.schemas.user import CurrentUser, Role


def _scope_conditions(model: type, scope: dict) -> list:
    return [getattr(model, key) == value for key, value in scope.items()]


async def test_scope():
    async for session in get_async_session():
        # 获取测试用户
        users = (await session.execute(
            select(User).where(User.is_deleted == False)
        )).scalars().all()
        
        print("=== 测试不同角色的数据可见范围 ===\n")
        
        for user in users:
            current_user = CurrentUser(
                id=user.id,
                role=Role(user.role),
                department_id=user.department_id,
                team_id=user.team_id,
                managed_team_ids=[],
                is_admin=user.is_admin
            )
            
            scope = build_scope_filter(current_user, "player")
            base = and_(Player.is_deleted == False, *_scope_conditions(Player, scope))
            query = select(Player).where(base)
            
            players = (await session.execute(query)).scalars().all()
            
            print(f"User {user.id} ({user.role}, Dept={user.department_id}, Team={user.team_id}):")
            print(f"  Scope: {scope}")
            print(f"  可见 Player 数量: {len(players)}")
            print(f"  Player IDs: {[p.id for p in players]}")
            print()
        
        break


if __name__ == "__main__":
    asyncio.run(test_scope())
