"""
用户管理重构 V2 - 数据迁移脚本

使用方法：
    cd backend && python migration_user_refactor_v2.py
"""

import asyncio
import os
import sys
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 从环境变量或.env文件获取数据库URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    try:
        from app.core.config import settings
        DATABASE_URL = settings.DATABASE_URL
    except:
        print("❌ 错误：无法获取数据库URL")
        print("请设置 DATABASE_URL 环境变量或确保 app.core.config 可用")
        sys.exit(1)


async def run_migration():
    """执行迁移"""
    print("=" * 60)
    print("🚀 用户管理重构 V2 - 数据迁移")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # 步骤1：固化部门数据
            print("📋 步骤1：固化部门数据...")
            await session.execute(text("""
                INSERT INTO "Department" (id, name, code, is_deleted, created_at, updated_at)
                VALUES (1, 'QGS', 'QGS', false, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET name='QGS', code='QGS', is_deleted=false
            """))
            await session.execute(text("""
                INSERT INTO "Department" (id, name, code, is_deleted, created_at, updated_at)
                VALUES (2, 'HGS', 'HGS', false, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET name='HGS', code='HGS', is_deleted=false
            """))
            await session.commit()
            print("  ✅ QGS和HGS部门已确保存在\n")
            
            # 步骤2：自动设置 department_id
            print("📋 步骤2：自动设置 department_id...")
            result = await session.execute(text("""
                UPDATE "User" SET department_id = 1 
                WHERE role LIKE 'QGS_%' AND is_deleted = false
            """))
            qgs_count = result.rowcount
            print(f"  ✅ 更新 {qgs_count} 个 QGS 用户")
            
            result = await session.execute(text("""
                UPDATE "User" SET department_id = 2 
                WHERE role LIKE 'HGS_%' AND is_deleted = false
            """))
            hgs_count = result.rowcount
            print(f"  ✅ 更新 {hgs_count} 个 HGS 用户")
            await session.commit()
            print(f"  ✅ 共更新 {qgs_count + hgs_count} 个用户\n")
            
            # 步骤3：清空 managed_team_ids
            print("📋 步骤3：清空 managed_team_ids...")
            result = await session.execute(text("""
                UPDATE "User" SET managed_team_ids = '[]'::jsonb 
                WHERE is_deleted = false
            """))
            print(f"  ✅ 清空 {result.rowcount} 个用户的 managed_team_ids\n")
            await session.commit()
            
            # 步骤4：验证数据
            print("📋 步骤4：数据一致性验证...")
            
            # 验证 department_id
            result = await session.execute(text("""
                SELECT COUNT(*) FROM "User" 
                WHERE is_deleted = false 
                AND ((role LIKE 'QGS_%' AND department_id != 1) 
                     OR (role LIKE 'HGS_%' AND department_id != 2))
            """))
            inconsistent = result.scalar()
            if inconsistent > 0:
                print(f"  ⚠️  发现 {inconsistent} 个用户的 department_id 与 role 不一致")
            else:
                print("  ✅ 所有用户的 department_id 与 role 一致")
            
            # 验证 managed_team_ids
            result = await session.execute(text("""
                SELECT COUNT(*) FROM "User" 
                WHERE is_deleted = false 
                AND managed_team_ids != '[]'::jsonb
            """))
            non_empty = result.scalar()
            if non_empty > 0:
                print(f"  ⚠️  发现 {non_empty} 个用户的 managed_team_ids 非空")
            else:
                print("  ✅ 所有用户的 managed_team_ids 为空")
            
            print("\n" + "=" * 60)
            if inconsistent == 0 and non_empty == 0:
                print("✅ 迁移成功完成！")
            else:
                print("⚠️  迁移完成，但存在数据不一致")
            print("=" * 60)
            print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            return 0 if (inconsistent == 0 and non_empty == 0) else 1
            
        except Exception as e:
            print(f"\n❌ 迁移失败: {e}")
            await session.rollback()
            return 1
        finally:
            await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(run_migration())
    sys.exit(exit_code)
