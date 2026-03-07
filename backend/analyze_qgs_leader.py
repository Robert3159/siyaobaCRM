import asyncio
from sqlalchemy import select, and_
from app.core.database import get_async_session
from app.core.scope import build_scope_filter
from app.models import Player, User
from app.schemas.user import CurrentUser, Role


def _scope_conditions(model: type, scope: dict) -> list:
    return [getattr(model, key) == value for key, value in scope.items()]


async def analyze_qgs_leader():
    async for session in get_async_session():
        # 获取 QGS_LEADER (User 7)
        qgs_leader = (await session.execute(
            select(User).where(User.id == 7)
        )).scalar_one()
        
        print(f"=== QGS_LEADER 分析 ===")
        print(f"User ID: {qgs_leader.id}")
        print(f"Role: {qgs_leader.role}")
        print(f"Department ID: {qgs_leader.department_id}")
        print(f"Team ID: {qgs_leader.team_id}\n")
        
        # 获取该 LEADER 能看到的数据
        current_user = CurrentUser(
            id=qgs_leader.id,
            role=Role(qgs_leader.role),
            department_id=qgs_leader.department_id,
            team_id=qgs_leader.team_id,
            managed_team_ids=[],
            is_admin=qgs_leader.is_admin
        )
        
        scope = build_scope_filter(current_user, "player")
        base = and_(Player.is_deleted == False, *_scope_conditions(Player, scope))
        query = select(Player).where(base)
        visible_players = (await session.execute(query)).scalars().all()
        
        print(f"Scope 过滤条件: {scope}")
        print(f"可见 Player 数量: {len(visible_players)}")
        print(f"可见 Player IDs: {sorted([p.id for p in visible_players])}\n")
        
        # 获取所有 Player 数据
        all_players = (await session.execute(
            select(Player).where(Player.is_deleted == False)
        )).scalars().all()
        
        print(f"=== 所有 Player 数据 (共 {len(all_players)} 条) ===")
        visible_ids = {p.id for p in visible_players}
        
        for p in sorted(all_players, key=lambda x: x.id):
            owner = (await session.execute(
                select(User.id, User.role, User.alias).where(User.id == p.owner_id)
            )).first()
            
            is_visible = "[Y]" if p.id in visible_ids else "[N]"
            print(f"{is_visible} Player {p.id}: Owner={p.owner_id} ({owner.role if owner else 'N/A'}), "
                  f"Dept={p.department_id}, Team={p.team_id}")
        
        # 分析不可见的数据
        invisible_players = [p for p in all_players if p.id not in visible_ids]
        if invisible_players:
            print(f"\n=== 不可见的 {len(invisible_players)} 条数据分析 ===")
            for p in invisible_players:
                owner = (await session.execute(
                    select(User).where(User.id == p.owner_id)
                )).scalar_one_or_none()
                
                print(f"\nPlayer {p.id}:")
                print(f"  Owner: {p.owner_id} ({owner.role if owner else 'N/A'})")
                print(f"  Player.department_id: {p.department_id}")
                print(f"  Player.team_id: {p.team_id}")
                if owner:
                    print(f"  Owner.department_id: {owner.department_id}")
                    print(f"  Owner.team_id: {owner.team_id}")
                print(f"  原因: team_id={p.team_id} != {qgs_leader.team_id} (LEADER 的 team_id)")
        
        break


if __name__ == "__main__":
    asyncio.run(analyze_qgs_leader())
