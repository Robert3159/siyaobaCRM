#!/usr/bin/env python3
"""进一步查询 Player 数据的 department_id 问题"""

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
    print("无法解析数据库URL")
    exit(1)

conn = psycopg2.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    dbname=dbname
)
cur = conn.cursor()

print("=" * 60)
print("1. 查询所有 Player 数据的完整信息")
print("=" * 60)
cur.execute('''
    SELECT id, owner_id, department_id, team_id, project_id, created_at 
    FROM "Player" 
    WHERE is_deleted = FALSE 
    ORDER BY id DESC
''')
rows = cur.fetchall()
print(f"{'ID':<5} {'OwnerID':<10} {'DeptID':<10} {'TeamID':<10} {'ProjectID':<10} {'CreatedAt'}")
print("-" * 65)
for row in rows:
    print(f"{row[0]:<5} {row[1]:<10} {str(row[2]):<10} {str(row[3]):<10} {row[4]:<10} {row[5]}")

print("\n" + "=" * 60)
print("2. 查询 OwnerID 对应的用户信息")
print("=" * 60)
cur.execute('''
    SELECT id, role, department_id, team_id, user 
    FROM "User" 
    WHERE is_deleted = FALSE
    ORDER BY id
''')
rows = cur.fetchall()
print(f"{'ID':<5} {'Role':<20} {'DeptID':<10} {'TeamID':<10} {'Username'}")
print("-" * 65)
for row in rows:
    print(f"{row[0]:<5} {row[1]:<20} {str(row[2]):<10} {str(row[3]):<10} {row[4]}")

cur.close()
conn.close()
print("\n查询完成!")
