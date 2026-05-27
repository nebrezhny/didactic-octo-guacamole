from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from bot.services.db import Database
from bot.services.limiter import LimiterService
from datetime import datetime, timezone

class ThrottleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
            text = event.text or ""
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            text = ""
        else:
            return await handler(event, data)

        if not user:
            return await handler(event, data)

        db: Database = data["db"]
        limiter: LimiterService = data["limiter"]

        async with db.pool.acquire() as conn:
            user_record = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user.id)
            
            if isinstance(event, Message) and text.startswith("/start"):
                return await handler(event, data)

            if not user_record or not user_record["country"]:
                if isinstance(event, Message):
                    await event.answer("Пожалуйста, отправь /start для завершения регистрации и выбора страны.")
                return

            if isinstance(event, Message) and text.startswith("/"):
                return await handler(event, data)

            plan = user_record["plan"]
            
            if plan == "unlimited":
                expires_at = user_record["plan_expires_at"]
                if expires_at and expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                    return await handler(event, data)
                plan = "free"
                await conn.execute("UPDATE users SET plan = 'free' WHERE user_id = $1", user.id)

            if plan == "pack_50":
                if user_record["plan_requests_left"] > 0:
                    await conn.execute(
                        "UPDATE users SET plan_requests_left = plan_requests_left - 1 WHERE user_id = $1",
                        user.id
                    )
                    return await handler(event, data)
                else:
                    plan = "free"
                    await conn.execute("UPDATE users SET plan = 'free' WHERE user_id = $1", user.id)

            if plan == "free":
                can_request = await limiter.check_and_increment_free_requests(user.id)
                if can_request:
                    return await handler(event, data)
                else:
                    msg = (
                        "Дневной лимит исчерпан (5/5).\n"
                        "Продолжить можно с /premium:\n"
                        "- 50 запросов за 100 ⭐\n"
                        "- Безлимит за 300 ⭐/мес"
                    )
                    if isinstance(event, Message):
                        await event.answer(msg)
                    elif isinstance(event, CallbackQuery):
                        await event.message.answer(msg)
                    return

        return await handler(event, data)
