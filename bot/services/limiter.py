import time
from datetime import datetime, timedelta, timezone
from redis.asyncio import Redis

class LimiterService:
    def __init__(self, redis: Redis, daily_cost_limit_usd: float):
        self.redis = redis
        self.daily_cost_limit_usd = daily_cost_limit_usd

    def _get_seconds_until_midnight_moscow(self) -> int:
        tz = timezone(timedelta(hours=3))
        now = datetime.now(tz)
        tomorrow = now + timedelta(days=1)
        midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=tz)
        return int((midnight - now).total_seconds())

    async def check_and_increment_free_requests(self, user_id: int, max_free: int = 5) -> bool:
        key = f"user:{user_id}:free_reqs_today"
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, self._get_seconds_until_midnight_moscow())
        
        if current > max_free:
            await self.redis.decr(key)
            return False
        return True

    async def reserve_budget(self, estimated_cost: float) -> bool:
        tz = timezone(timedelta(hours=3))
        now = datetime.now(tz)
        date_str = now.strftime("%Y-%m-%d")
        global_key = f"global_cost:{date_str}"
        
        current_global = await self.redis.incrbyfloat(global_key, estimated_cost)
        if current_global == estimated_cost:
            await self.redis.expire(global_key, 86400 * 2)

        if current_global > self.daily_cost_limit_usd:
            await self.redis.incrbyfloat(global_key, -estimated_cost)
            return False
            
        return True

    async def adjust_budget(self, estimated_cost: float, actual_cost: float):
        if actual_cost == estimated_cost:
            return
            
        tz = timezone(timedelta(hours=3))
        now = datetime.now(tz)
        date_str = now.strftime("%Y-%m-%d")
        global_key = f"global_cost:{date_str}"
        
        diff = actual_cost - estimated_cost
        await self.redis.incrbyfloat(global_key, diff)
