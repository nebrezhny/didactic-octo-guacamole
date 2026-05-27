import asyncpg
from typing import Optional

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self, dsn: str):
        self.pool = await asyncpg.create_pool(dsn)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def init_models(self):
        query = """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            country TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            free_requests_today INT DEFAULT 0,
            last_reset_date DATE DEFAULT CURRENT_DATE,
            plan TEXT DEFAULT 'free',
            plan_requests_left INT DEFAULT 0,
            plan_expires_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id BIGINT REFERENCES users(user_id),
            subject TEXT,
            input_type TEXT,
            question TEXT,
            answer TEXT,
            tokens_used INT,
            cost_usd FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS payments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id BIGINT REFERENCES users(user_id),
            stars_amount INT,
            plan TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)
