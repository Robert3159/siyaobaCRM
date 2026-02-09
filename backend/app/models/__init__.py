"""
Prisma Client 及模型引用。

注意：
- 所有数据库访问必须通过 Service 层封装；
- Router 层禁止直接使用 Prisma Client。
"""

from prisma import Prisma

prisma = Prisma()


