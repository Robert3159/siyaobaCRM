#!/usr/bin/env python3
"""查询用户和玩家数据"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import psycopg2
from psycopg2 import sql

# 获取数据库连接
DATABASE_URL = os.getenv('DATABASE_URL')
# 解析 DATABASE_URL
# postgresql://postgres.maeleuoxwoqtpvjijtte:mkEaNh7p2Fl7lkY6@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres

# 手动解析
import re
match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
if match:
    user, password, host, port, dbname = match.groups()
else:
    print("无法解析数据库URL")
    exit(1)

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname
    )
    cur = conn.cursor()
    
    print("=" * 60)
    print("1. 查询 HGS_* 用户的部门信息")
    print("=" * 60)
    cur.execute('''
        SELECT id, role, department_id, team_id, user, alias 
        FROM "User" 
        WHERE role LIKE 'HGS_%%' AND is_deleted = FALSE
        ORDER BY role, id
    ''')
    rows = cur.fetchall()
    if rows:
        print(f"{'ID':<5} {'Role':<20} {'DeptID':<8} {'TeamID':<8} {'Username':<15} {'Alias'}")
        print("-" * 80)
        for row in rows:
            print(f"{row[0]:<5} {row[1]:<20} {row[2]}    {row[3]}    {row[4]:<15} {row[5]}")
    else:
        print("没有找到 HGS_* 用户")
    
    print("\n" + "=" * 60)
    print("2. 查询 QGS_* 用户的部门信息（对比）")
    print("=" * 60)
    cur.execute('''
        SELECT id, role, department_id, team_id, user, alias 
        FROM "User" 
        WHERE role LIKE 'QGS_%%' AND is_deleted = FALSE
        ORDER BY role, id
    ''')
    rows = cur.fetchall()
    if rows:
        print(f"{'ID':<5} {'Role':<20} {'DeptID':<8} {'TeamID':<8} {'Username':<15} {'Alias'}")
        print("-" * 80)
        for row in rows:
            print(f"{row[0]:<5} {row[1]:<20} {row[2]}    {row[3]}    {row[4]:<15} {row[5]}")
    else:
        print("没有找到 QGS_* 用户")
    
    print("\n" + "=" * 60)
    print("3. 查询 Player 表中的 department_id 分布")
    print("=" * 60)
    cur.execute('''
        SELECT department_id, COUNT(*) as cnt 
        FROM "Player" 
        WHERE is_deleted = FALSE 
        GROUP BY department_id 
        ORDER BY department_id
    ''')
    rows = cur.fetchall()
    print(f"{'DeptID':<10} {'Count'}")
    print("-" * 30)
    for row in rows:
        print(f"{row[0]}    {row[1]}")
    
    print("\n" + "=" * 60)
    print("4. 查询 Player 表中是否有 department_id=2 的数据")
    print("=" * 60)
    cur.execute('''
        SELECT COUNT(*) FROM "Player" 
        WHERE department_id = 2 AND is_deleted = FALSE
    ''')
    count = cur.fetchone()[0]
    print(f"department_id=2 的 Player 数量: {count}")
    
    print("\n" + "=" * 60)
    print("5. 查询最近创建的 Player 数据（检查 department_id）")
    print("=" * 60)
    cur.execute('''
        SELECT id, owner_id, department_id, team_id, created_at 
        FROM "Player" 
        WHERE is_deleted = FALSE 
        ORDER BY id DESC 
        LIMIT 10
    ''')
    rows = cur.fetchall()
    print(f"{'ID':<5} {'OwnerID':<10} {'DeptID':<10} {'TeamID':<10} {'CreatedAt'}")
    print("-" * 50)
    for row in rows:
        print(f"{row[0]:<5} {row[1]:<10} {row[2]}       {row[3]}       {row[4]}")
    
    cur.close()
    conn.close()
    print("\n查询完成!")
    
except Exception as e:
    print(f"查询失败: {e}")
