from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from bot.services.db import Database
from datetime import datetime, timedelta, timezone

router = Router()

PACK_50_PRICE = 100
UNLIM_1_PRICE = 300
UNLIM_3_PRICE = 500

@router.message(Command("premium"))
async def cmd_premium(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"50 запросов — {PACK_50_PRICE} ⭐", callback_data="buy_pack_50")],
        [InlineKeyboardButton(text=f"Безлимит на месяц — {UNLIM_1_PRICE} ⭐", callback_data="buy_unlim_1")],
        [InlineKeyboardButton(text=f"Безлимит на 3 месяца — {UNLIM_3_PRICE} ⭐", callback_data="buy_unlim_3")]
    ])
    
    text = (
        "💎 Расширить доступ\n\n"
        "Выбери подходящий вариант:"
    )
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    action = callback.data
    if action == "buy_pack_50":
        title = "Пакет 50 запросов"
        price = PACK_50_PRICE
        payload = "pack_50"
    elif action == "buy_unlim_1":
        title = "Безлимит на 1 месяц"
        price = UNLIM_1_PRICE
        payload = "unlim_1"
    elif action == "buy_unlim_3":
        title = "Безлимит на 3 месяца"
        price = UNLIM_3_PRICE
        payload = "unlim_3"
    else:
        return
        
    prices = [LabeledPrice(label=title, amount=price)]
    
    await callback.message.answer_invoice(
        title=title,
        description="Оплата подписки для Study Helper Bot",
        payload=payload,
        currency="XTR",
        prices=prices,
        provider_token="" 
    )
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, db: Database):
    payment = message.successful_payment
    payload = payment.invoice_payload
    user_id = message.from_user.id
    stars = payment.total_amount
    
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if not user:
            return
            
        now = datetime.now(timezone.utc)
        
        if payload == "pack_50":
            plan = "pack_50"
            current_left = user["plan_requests_left"] if user["plan"] == "pack_50" else 0
            await conn.execute("UPDATE users SET plan = $1, plan_requests_left = $2 WHERE user_id = $3", plan, current_left + 50, user_id)
        elif payload == "unlim_1":
            plan = "unlimited"
            current_expires = user["plan_expires_at"] if user["plan"] == "unlimited" and user["plan_expires_at"] else now
            if current_expires.tzinfo is None:
                current_expires = current_expires.replace(tzinfo=timezone.utc)
            new_expires = current_expires + timedelta(days=30)
            await conn.execute("UPDATE users SET plan = $1, plan_expires_at = $2 WHERE user_id = $3", plan, new_expires.replace(tzinfo=None), user_id)
        elif payload == "unlim_3":
            plan = "unlimited"
            current_expires = user["plan_expires_at"] if user["plan"] == "unlimited" and user["plan_expires_at"] else now
            if current_expires.tzinfo is None:
                current_expires = current_expires.replace(tzinfo=timezone.utc)
            new_expires = current_expires + timedelta(days=90)
            await conn.execute("UPDATE users SET plan = $1, plan_expires_at = $2 WHERE user_id = $3", plan, new_expires.replace(tzinfo=None), user_id)
            
        await conn.execute("INSERT INTO payments (user_id, stars_amount, plan) VALUES ($1, $2, $3)", user_id, stars, plan)
        
    await message.answer("Оплата прошла успешно! План обновлен. Спасибо за поддержку! 💎")
