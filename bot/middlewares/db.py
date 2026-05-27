from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.services.db import Database
from redis.asyncio import Redis
from bot.services.limiter import LimiterService

class DBMiddleware(BaseMiddleware):
    def __init__(self, db: Database, redis: Redis, limiter: LimiterService):
        self.db = db
        self.redis = redis
        self.limiter = limiter

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db
        data["redis"] = self.redis
        data["limiter"] = self.limiter
        return await handler(event, data)
