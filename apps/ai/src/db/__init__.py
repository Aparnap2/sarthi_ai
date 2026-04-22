"""Database module for Sarthi AI."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Dict, List

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://iterateswarm:iterateswarm@localhost:5433/iterateswarm")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


class DB:
    @staticmethod
    async def fetch(query: str, *args) -> List[Dict]:
        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, args)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    async def fetchval(query: str, *args):
        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(query, args)
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None

    @staticmethod
    async def execute(query: str, *args) -> None:
        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(query, args)
        cur.close()
        conn.close()


db = DB()
