import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from redis.asyncio import Redis

from bot.core.config import config
from bot.core.logging import setup_logging
from bot.services.db import Database
from bot.services.limiter import LimiterService
from bot.middlewares.db import DBMiddleware
from bot.middlewares.throttle import ThrottleMiddleware

from bot.handlers import start, solve, payment

logger = logging.getLogger(__name__)

async def on_startup(dispatcher: Dispatcher, bot: Bot):
    logger.info("Starting up...")
    
    db = Database()
    await db.connect(config.database_url)
    await db.init_models()
    
    redis_client = Redis.from_url(config.redis_url, decode_responses=True)
    
    limiter_service = LimiterService(redis_client, config.daily_cost_limit_usd)
    
    dispatcher["db_instance"] = db
    dispatcher["redis_instance"] = redis_client
    
    db_middleware = DBMiddleware(db, redis_client, limiter_service)
    throttle_middleware = ThrottleMiddleware()
    
    dispatcher.message.middleware(db_middleware)
    dispatcher.callback_query.middleware(db_middleware)
    
    dispatcher.message.middleware(throttle_middleware)
    dispatcher.callback_query.middleware(throttle_middleware)
    
    if config.webhook_url:
        webhook_url = f"{config.webhook_url}/webhook"
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to {webhook_url}")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    logger.info("Shutting down...")
    
    if config.webhook_url:
        await bot.delete_webhook()

    db: Database = dispatcher.get("db_instance")
    if db:
        await db.close()
        
    redis_client: Redis = dispatcher.get("redis_instance")
    if redis_client:
        await redis_client.aclose()

def main():
    setup_logging()
    
    bot = Bot(
        token=config.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="Markdown")
    )
    
    dp = Dispatcher()
    
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(solve.router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    if config.webhook_url:
        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
        setup_application(app, dp, bot=bot)
        web.run_app(app, host="0.0.0.0", port=8080)
    else:
        logger.info("Starting long polling...")
        asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    main()
