#!/usr/bin/env python3
"""Deep analysis of Player data and permissions"""

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
    exit(1)

conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
cur = conn.cursor()

print("=" * 70)
print("Analysis: Why HGS users see empty list")
print("=" * 70)

# Check 1: All users with their department_id
print("\n[Check 1] All Users:")
cur.execute('SELECT id, role, department_id, team_id FROM "User" WHERE is_deleted = FALSE ORDER BY id')
users = {row[0]: {'role': row[1], 'dept': row[2], 'team': row[3]} for row in cur.fetchall()}

print(f"{'ID':<5} {'Role':<20} {'DeptID':<8} {'TeamID'}")
print("-" * 50)
for uid, u in users.items():
    print(f"{uid:<5} {u['role']:<20} {u['dept']}     {u['team']}")

# Check 2: All Players with owner info
print("\n[Check 2] All Players with Owner Info:")
cur.execute('''
    SELECT p.id, p.owner_id, p.department_id as p_dept, p.team_id as p_team,
           u.role as owner_role, u.department_id as u_dept, u.team_id as u_team
    FROM "Player" p
    JOIN "User" u ON p.owner_id = u.id
    WHERE p.is_deleted = FALSE
    ORDER BY p.id
''')
players = cur.fetchall()

print(f"{'PID':<5} {'OwnerID':<10} {'P_Dept':<8} {'P_Team':<8} {'OwnerRole':<20} {'U_Dept':<8} {'U_Team'}")
print("-" * 85)
for row in players:
    pid, oid, p_dept, p_team, orole, u_dept, u_team = row
    print(f"{pid:<5} {oid:<10} {p_dept}     {p_team}     {orole:<20} {u_dept}     {u_team}")

# Check 3: Simulate HGS_DIRECTOR query
print("\n[Check 3] Simulating HGS_DIRECTOR (dept=2) query:")
cur.execute('''
    SELECT COUNT(*) FROM "Player" 
    WHERE is_deleted = FALSE AND department_id = 2
''')
hgs_count = cur.fetchone()[0]
print(f"HGS_DIRECTOR would see {hgs_count} records (department_id=2)")

# Check 4: What if we check by team_id?
print("\n[Check 4] Player team_id distribution:")
cur.execute('SELECT team_id, COUNT(*) FROM "Player" WHERE is_deleted = FALSE GROUP BY team_id ORDER BY team_id')
for row in cur.fetchall():
    print(f"  team_id={row[0]}: {row[1]} records")

# Check 5: Any players with owner_id in HGS users?
print("\n[Check 5] Players owned by HGS users:")
cur.execute('''
    SELECT p.id, p.owner_id, p.department_id 
    FROM "Player" p
    JOIN "User" u ON p.owner_id = u.id
    WHERE u.role LIKE 'HGS_%%' AND p.is_deleted = FALSE
''')
hgs_owned = cur.fetchall()
if hgs_owned:
    for row in hgs_owned:
        print(f"  Player {row[0]}: owner_id={row[1]}, dept={row[2]}")
else:
    print("  [NONE] No players owned by HGS users!")

# Check 6: What's the actual query would return?
print("\n[Check 6] What would HGS_DIRECTOR see if query worked differently:")
# If we query all non-deleted players
cur.execute('SELECT COUNT(*) FROM "Player" WHERE is_deleted = FALSE')
total = cur.fetchone()[0]
print(f"  Total players (no filter): {total}")

# If we query by team_id=7 (HGS team)
cur.execute('SELECT COUNT(*) FROM "Player" WHERE is_deleted = FALSE AND team_id = 7')
by_team = cur.fetchone()[0]
print(f"  By team_id=7: {by_team}")

cur.close()
conn.close()
print("\nDone!")
