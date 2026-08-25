import os
import logging
import urllib.parse
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import asyncio
import re
from supabase import create_client

# Supabase Sozlamalari
SUPABASE_URL = "https://wtgtmeodtuimjvqoqfzc.supabase.co"
SUPABASE_KEY = "sb_publishable_rRnaaXbZYHD3ZOmz2pFsEA_31X9MzLz"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6606071265

VISA = "4023 0601 4330 7436"
MASTERCARD = "5476 3815 0507 5414"
CARD_NAME = "ASLBEK ZIYODULLAYEV"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Foydalanuvchilar ma'lumotlarini saqlash
user_data = {}

@dp.message(CommandStart())
async def start_handler(message: Message):
    args = message.text.split(maxsplit=1)
    
    amount = "5"
    cat = "other"
    url = "—"

    if len(args) > 1:
        payload = args[1]
        
        amount_match = re.search(r'bid_(\d+)', payload)
        cat_match = re.search(r'cat_([^_]+)', payload)
        url_match = re.search(r'url_(.+)', payload)

        if amount_match:
            amount = amount_match.group(1)
        if cat_match:
            cat = cat_match.group(1)
        if url_match:
            # URL'ni to'g'ri dekodlash (replace('_', ' ') xatosi tuzatildi)
            url = urllib.parse.unquote(url_match.group(1))

    user_data[message.from_user.id] = {
        "amount": amount,
        "cat": cat,
        "url": url
    }

    text = f"""Здравствуйте!

Вы хотите занять место в рейтинге <b>BIDmesto</b>.

Сумма к оплате: <b>${amount}</b>
Сайт: <b>{url}</b>

Переведите <b>точную сумму</b> на одну из карт:

<b>Visa:</b>
<code>{VISA}</code>

<b>Mastercard:</b>
<code>{MASTERCARD}</code>

Получатель: <b>{CARD_NAME}</b>

После оплаты отправьте сюда <b>чек</b> (скриншот или фото квитанции).

Мы проверим платёж в течение 5–15 минут."""

    await message.answer(text, parse_mode=ParseMode.HTML)


# Aiogram 3 filtri to'g'rilandi (F.photo | F.document)
@dp.message(F.photo | F.document)
async def check_handler(message: Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {"amount": "5", "cat": "other", "url": "—"})

    await message.answer("Чек получен ✅\n\nВаш платёж проверяется.\nОбычно это занимает 5–15 минут.\n\nПожалуйста, подождите.")

    caption = f"""🔔 <b>Новый платёж</b>

Сумма: <b>${data['amount']}</b>
Категория: <b>{data['cat']}</b>
Сайт: <b>{data['url']}</b>
Пользователь: @{message.from_user.username or 'нет'} (ID: {user_id})
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ])

    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("confirm_") | F.data.startswith("reject_"))
async def process_callback(callback: CallbackQuery):
    action, user_id = callback.data.split("_")
    user_id = int(user_id)

    if action == "confirm":
        data = user_data.get(user_id, {"amount": 5, "cat": "other", "url": "https://bidmesto.lol"})
        
        # SUPABASE BAZASIGA YOZISH (clicks: 0 qo'shildi)
        try:
            supabase.table('entries').insert({
                'url': data['url'],
                'cat': data['cat'],
                'bid': int(data['amount']),
                'name': data['url'],
                'clicks': 0
            }).execute()
            logging.info(f"Supabase success: {data['url']}")
        except Exception as e:
            logging.error(f"Supabase Error: {e}")

        await bot.send_message(user_id, 
            "Оплата успешно подтверждена! ✅\n\nВаше место добавлено в рейтинг BIDmesto.\n\nСпасибо за оплату!\nПроверить можно здесь: https://bidmesto.lol")
        
        old_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=old_caption + f"\n\n✅ <b>Подтверждено (${data['amount']})</b>", 
            parse_mode=ParseMode.HTML
        )
    else:
        await bot.send_message(user_id, 
            "К сожалению, платёж не подтверждён.\n\nВозможные причины:\n• Неверная сумма\n• Нечёткий чек\n• Оплата не поступила\n\nПожалуйста, отправьте чек ещё раз.")
        
        # Crash beradigan 'caption' xatoligi tuzatildi
        old_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=old_caption + "\n\n❌ <b>Отклонено</b>", 
            parse_mode=ParseMode.HTML
        )

    await callback.answer()


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
