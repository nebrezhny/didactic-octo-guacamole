from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.services.db import Database
from redis.asyncio import Redis

router = Router()

class Registration(StatesGroup):
    waiting_for_country = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database):
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name
        """, message.from_user.id, message.from_user.username, message.from_user.first_name)
        
        user_record = await conn.fetchrow("SELECT country FROM users WHERE user_id = $1", message.from_user.id)

    if not user_record or not user_record["country"]:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Россия", callback_data="country_russia"),
             InlineKeyboardButton(text="🇺🇦 Украина", callback_data="country_ukraine")],
            [InlineKeyboardButton(text="🇩🇪 Германия", callback_data="country_germany"),
             InlineKeyboardButton(text="🇺🇸 США", callback_data="country_usa")]
        ])
        await message.answer("Выбери страну обучения, чтобы я мог адаптировать решения под твою программу:", reply_markup=keyboard)
        await state.set_state(Registration.waiting_for_country)
    else:
        await send_welcome(message)

@router.callback_query(Registration.waiting_for_country, F.data.startswith("country_"))
async def process_country_selection(callback: CallbackQuery, state: FSMContext, db: Database):
    country_map = {
        "country_russia": "Russia",
        "country_ukraine": "Ukraine",
        "country_germany": "Germany",
        "country_usa": "USA"
    }
    selected_country = country_map.get(callback.data)
    
    async with db.pool.acquire() as conn:
        await conn.execute("UPDATE users SET country = $1 WHERE user_id = $2", selected_country, callback.from_user.id)
    
    await state.clear()
    await callback.message.edit_text("Страна сохранена!")
    await send_welcome(callback.message)
    await callback.answer()

async def send_welcome(message: Message):
    text = (
        "Привет! Я помогу решить любое учебное задание.\n"
        "Просто отправь:\n"
        "- фото задачи из учебника\n"
        "- или напиши задачу текстом\n\n"
        "Поддерживаю: математику, физику, химию, программирование, русский, английский и другие предметы.\n"
        "У тебя 5 бесплатных запросов в день.\n\n"
        "/status — посмотреть остаток\n"
        "/premium — расширить лимит"
    )
    await message.answer(text)

@router.message(Command("help"))
async def cmd_help(message: Message):
    await send_welcome(message)

@router.message(Command("status"))
async def cmd_status(message: Message, db: Database, redis: Redis):
    async with db.pool.acquire() as conn:
        user_record = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", message.from_user.id)
        
    if not user_record:
        return
        
    plan = user_record["plan"]
    plan_ru = {"free": "Бесплатный", "pack_50": "Пакет 50", "unlimited": "Безлимит"}.get(plan, plan)
    country = user_record["country"] or "Не указана"
    
    if plan == "free":
        key = f"user:{message.from_user.id}:free_reqs_today"
        used = await redis.get(key)
        used = int(used) if used else 0
        left = max(0, 5 - used)
        status_text = f"Осталось сегодня: {left} из 5"
    elif plan == "pack_50":
        status_text = f"Осталось запросов: {user_record['plan_requests_left']}"
    else:
        status_text = f"Действует до: {user_record['plan_expires_at'].strftime('%d.%m.%Y') if user_record['plan_expires_at'] else 'Неизвестно'}"

    text = (
        "📊 Твой аккаунт:\n"
        f"План: {plan_ru}\n"
        f"{status_text}\n"
        f"Страна обучения: {country}"
    )
    await message.answer(text)
