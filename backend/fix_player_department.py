#!/usr/bin/env python3
"""Fix Player department_id issue"""

import os
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')
match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
if match:
    user, password, host, port, dbname = match.groups()
else:
    print("Cannot parse DATABASE_URL")
    exit(1)

conn = psycopg2.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    dbname=dbname
)
conn.autocommit = False
cur = conn.cursor()

print("=" * 60)
print("Fixing Player department_id")
print("=" * 60)

# 1. First check what needs to be fixed
print("\n[Step 1] Checking records that need fixing...")
cur.execute('''
    SELECT p.id, p.owner_id, p.department_id as player_dept, 
           u.role as owner_role, u.department_id as owner_dept
    FROM "Player" p
    JOIN "User" u ON p.owner_id = u.id
    WHERE p.is_deleted = FALSE
    ORDER BY p.id
''')
rows = cur.fetchall()

print(f"{'PlayerID':<10} {'OwnerID':<10} {'Player.Dept':<12} {'Owner.Role':<20} {'Owner.Dept':<10}")
print("-" * 70)
fix_count = 0
for row in rows:
    player_id, owner_id, player_dept, owner_role, owner_dept = row
    needs_fix = owner_dept != player_dept
    status = "[NEEDS FIX]" if needs_fix else "[OK]"
    print(f"{player_id:<10} {owner_id:<10} {str(player_dept):<12} {owner_role:<20} {str(owner_dept):<10} {status}")
    if needs_fix:
        fix_count += 1

    print(f"\nTotal {fix_count} records need fixing")

# 2. 执行修复
if fix_count > 0:
    print("\n[Step 2] Executing fix...")
    cur.execute('''
        UPDATE "Player" p
        SET department_id = u.department_id
        FROM "User" u
        WHERE p.owner_id = u.id
          AND p.is_deleted = FALSE
          AND p.department_id != u.department_id
    ''')
    print(f"Fixed {cur.rowcount} records")
    
    # 3. 验证修复结果
    print("\n[Step 3] Verifying fix results...")
    cur.execute('''
        SELECT p.id, p.owner_id, p.department_id as player_dept, 
               u.role as owner_role, u.department_id as owner_dept
        FROM "Player" p
        JOIN "User" u ON p.owner_id = u.id
        WHERE p.is_deleted = FALSE
        ORDER BY p.id
    ''')
    rows = cur.fetchall()
    
    print(f"{'PlayerID':<10} {'OwnerID':<10} {'Player.Dept':<12} {'Owner.Role':<20} {'Owner.Dept':<10}")
    print("-" * 70)
    all_fixed = True
    for row in rows:
        player_id, owner_id, player_dept, owner_role, owner_dept = row
        status = "[OK]" if player_dept == owner_dept else "[ISSUE]"
        if player_dept != owner_dept:
            all_fixed = False
        print(f"{player_id:<10} {owner_id:<10} {str(player_dept):<12} {owner_role:<20} {str(owner_dept):<10} {status}")
    
    if all_fixed:
        print("\n=== All data fixed successfully! ===")
    else:
        print("\n=== Some data still has issues, please check ===")

    # 4. Show department_id distribution after fix
    print("\n[Step 4] Player department_id distribution after fix:")
    cur.execute('''
        SELECT department_id, COUNT(*) as cnt 
        FROM "Player" 
        WHERE is_deleted = FALSE 
        GROUP BY department_id 
        ORDER BY department_id
    ''')
    rows = cur.fetchall()
    print(f"{'DeptID':<10} {'Count'}")
    print("-" * 20)
    for row in rows:
        print(f"{row[0]}    {row[1]}")
else:
    print("\n=== No data needs fixing ===")

conn.commit()
cur.close()
conn.close()
print("\nScript completed!")
