import os
import logging
import re
import asyncio
import base64
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.enums import ParseMode
from supabase import create_client, Client

# ================== SOZLAMALAR VA KALITLAR ==================
BOT_TOKEN = "8834826569:AAFmNoXbXDIrFUmTWvXeqOyv1RhnUhUalYE"
SUPABASE_URL = "https://wtgtmeodtuimjvqoqfzc.supabase.co"
SUPABASE_KEY = "sb_secret_5IvU05B2_YifdnV9Vi6u4A_Pk7rCuGa"

ADMIN_ID = 6606071265

# Sizning karta raqamlaringiz:
VISA = "4023 0601 4330 7436"
MASTERCARD = "5476 3815 0507 5414"
CARD_NAME = "ASLBEK ZIYODULLAYEV"
# ============================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Foydalanuvchilarning vaqtinchalik buyurtma ma'lumotlarini saqlash
user_data = {}

# URL funksiyasi (Saytdan kelgan URLni dekodlash)
def decode_url(safe_url: str) -> str:
    try:
        safe_url = safe_url.replace('-', '+').replace('_', '/')
        padding = len(safe_url) % 4
        if padding:
            safe_url += '=' * (4 - padding)
        decoded_bytes = base64.b64decode(safe_url)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        logging.error(f"URL Decode error: {e}")
        return safe_url

@dp.message(CommandStart())
async def start_handler(message: Message):
    args = message.text.split(maxsplit=1)
    
    amount = "0"
    category = "general"
    url = "—"

    if len(args) > 1:
        payload = args[1]
        
        # Saytdan kelgan 2 xil formatni ham qo'llab-quvvatlaydi:
        # 1-format: p_10000_dev_aHR0c... (yangi format)
        if payload.startswith("p_"):
            parts = payload.split('_', 3)
            if len(parts) >= 4:
                _, amount_str, category, encoded_url = parts
                amount = amount_str
                url = decode_url(encoded_url)
        
        # 2-format: amount_10000_url_... (eski format)
        else:
            amount_match = re.search(r'amount_(\d+)', payload)
            url_match = re.search(r'url_(.+)', payload)
            if amount_match:
                amount = amount_match.group(1)
            if url_match:
                url = url_match.group(1).replace('%20', ' ').replace('_', ' ')

    try:
        formatted_amount = f"{int(amount):,}"
    except ValueError:
        formatted_amount = amount

    user_data[message.from_user.id] = {
        "amount": amount,
        "formatted_amount": formatted_amount,
        "category": category,
        "url": url
    }

    text = f"""Здравствуйте!

Вы хотите занять место в рейтинге <b>BIDmesto</b>.

Сайт: <b>{url}</b>
Сумма к оплате: <b>{formatted_amount} so'm</b>

Переведите <b>точную сумму</b> на одну из карт:

<b>Visa:</b>
<code>{VISA}</code>

<b>Mastercard:</b>
<code>{MASTERCARD}</code>

Получатель: <b>{CARD_NAME}</b>

После оплаты отправьте сюда <b>чек</b> (скриншот или фото квитанции).

Мы проверим платёж в течение 5–15 минут."""

    await message.answer(text, parse_mode=ParseMode.HTML)


# Chek yuborilganda (Rasm yoki Fayl)
@dp.message(F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT}))
async def check_handler(message: Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {"amount": "0", "formatted_amount": "0", "category": "general", "url": "—"})

    await message.answer(
        "Чек получен ✅\n\nВаш платёж проверяется.\nОбычно это занимает 5–15 минут.\n\nПожалуйста, подождите."
    )

    caption = f"""🔔 <b>Новый платёж!</b>

Сумма: <b>{data['formatted_amount']} so'm</b>
Категория: <b>{data['category']}</b>
Сайт: <b>{data['url']}</b>
Пользователь: @{message.from_user.username or 'нет'} (ID: <code>{user_id}</code>)
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ])

    # Admin interfeysiga jo'natish
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        elif message.document:
            await bot.send_document(chat_id=ADMIN_ID, document=message.document.file_id, caption=caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Adminga jo'natishda xatolik: {e}")


# Admin "Подтвердить" tugmasini bosganda (MUSTAHKAMLANGAN VA XATOLIKLARSIZ)
@dp.callback_query(F.data.startswith("confirm_"))
async def admin_confirm(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    data = user_data.get(user_id)

    if not data:
        await callback.answer("⚠️ Данные заказа не найдены!", show_alert=True)
        return

    try:
        # Summani xavfsiz songa o'tkazish
        try:
            bid_val = int(data["amount"])
        except ValueError:
            bid_val = 0

        # Supabase-ga e'lonni joylash
        db_data = {
            "url": str(data["url"]),
            "cat": str(data["category"]),
            "bid": bid_val,
            "clicks": 0
        }
        
        # Bazaga kiritish buyrug'i
        supabase.table("entries").insert(db_data).execute()

        # Adminga xabar va tugmalarni o'chirish
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n✅ <b>Платёж подтверждён и опубликован на сайте!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=None
        )

        # Foydalanuvchiga xabar
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>Ваш платёж подтверждён!</b>\n\nОбъявление <b>{data['url']}</b> успешно опубликовано на сайте BIDmesto.lol!",
            parse_mode=ParseMode.HTML
        )
        await callback.answer("Успешно добавлено в базу!")

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Bazaga yozishda xatolik: {error_msg}")
        # Xatolik yuz berganda ekranga aniq sababini chiqarish
        await callback.answer(f"❌ Ошибка записи: {error_msg[:60]}", show_alert=True)


# Admin "Отклонить" tugmasini bosganda
@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>Платёж отклонен.</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=None
    )

    await bot.send_message(
        chat_id=user_id,
        text="❌ <b>Ваш платёж не подтверждён.</b>\nЕсли произошла ошибка, свяжитесь с поддержкой."
    )
    await callback.answer("Отклонено.")


async def main():
    print("🤖 Бот успешно запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
