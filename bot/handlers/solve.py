import base64
from aiogram import Router, F
from aiogram.types import Message
from openai import AsyncOpenAI
from bot.services.db import Database
from bot.services.limiter import LimiterService
from bot.services.classifier import classify_subject
from bot.services.solver import solve_task
from bot.core.config import config

router = Router()

async def download_image_as_base64(message: Message) -> str | None:
    if not message.photo:
        return None
    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)
    if downloaded_file:
        return base64.b64encode(downloaded_file.read()).decode('utf-8')
    return None

@router.message(F.text | F.photo)
async def process_task(message: Message, db: Database, limiter: LimiterService):
    async with db.pool.acquire() as conn:
        user_record = await conn.fetchrow("SELECT country FROM users WHERE user_id = $1", message.from_user.id)
    
    country = user_record["country"] if user_record else "Russia"
    text = message.text or message.caption or ""
    
    client = AsyncOpenAI(api_key=config.openai_api_key.get_secret_value())
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    is_photo = bool(message.photo)
    estimated_cost = 0.05 if is_photo else 0.005 
    
    if not await limiter.reserve_budget(estimated_cost):
        await message.answer("Сервис временно недоступен, попробуй позже.")
        return

    image_base64 = await download_image_as_base64(message) if is_photo else None

    subject = await classify_subject(client, text, image_base64)
    
    answer_text, tokens_used, actual_cost = await solve_task(client, country, subject, text, image_base64)
    
    await limiter.adjust_budget(estimated_cost, actual_cost)
    
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO requests (user_id, subject, input_type, question, answer, tokens_used, cost_usd)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, message.from_user.id, subject, "photo" if is_photo else "text", text, answer_text, tokens_used, actual_cost)
        
    await message.answer(answer_text, parse_mode="Markdown")
