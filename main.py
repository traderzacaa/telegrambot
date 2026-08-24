import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.enums import ParseMode
import asyncio
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6606071265

VISA = "4023 0601 4330 7436"
MASTERCARD = "5476 3815 0507 5414"
CARD_NAME = "ASLBEK ZIYODULLAYEV"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data = {}

@dp.message(CommandStart())
async def start_handler(message: Message):
    args = message.text.split(maxsplit=1)
    
    amount = "5"
    position = "?"
    url = "—"

    if len(args) > 1:
        payload = args[1]
        # amount_12_pos_3_url_example.com
        amount_match = re.search(r'amount_(\d+)', payload)
        pos_match = re.search(r'pos_(\d+)', payload)
        url_match = re.search(r'url_(.+)', payload)

        if amount_match:
            amount = amount_match.group(1)
        if pos_match:
            position = pos_match.group(1)
        if url_match:
            url = url_match.group(1).replace('_', ' ')

    user_data[message.from_user.id] = {
        "amount": amount,
        "position": position,
        "url": url
    }

    text = f"""Здравствуйте!

Вы хотите занять место в рейтинге <b>BIDmesto</b>.

Место: <b>#{position}</b>
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


@dp.message(lambda message: message.content_type == ContentType.PHOTO or message.content_type == ContentType.DOCUMENT)
async def check_handler(message: Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {"amount": "5", "position": "?", "url": "—"})

    await message.answer("Чек получен ✅\n\nВаш платёж проверяется.\nОбычно это занимает 5–15 минут.\n\nПожалуйста, подождите.")

    caption = f"""🔔 <b>Новый платёж</b>

Сумма: <b>${data['amount']}</b>
Место: <b>#{data['position']}</b>
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


@dp.callback_query(lambda c: c.data.startswith("confirm_") or c.data.startswith("reject_"))
async def process_callback(callback: CallbackQuery):
    action, user_id = callback.data.split("_")
    user_id = int(user_id)

    if action == "confirm":
        await bot.send_message(user_id, 
            "Оплата успешно подтверждена! ✅\n\nВаше место добавлено в рейтинг BIDmesto.\n\nСпасибо за оплату!\nПроверить можно здесь: https://bidmesto.lol")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>Подтверждено</b>", parse_mode=ParseMode.HTML)
    else:
        await bot.send_message(user_id, 
            "К сожалению, платёж не подтверждён.\n\nВозможные причины:\n• Неверная сумма\n• Нечёткий чек\n• Оплата не поступила\n\nПожалуйста, отправьте чек ещё раз.")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ <b>Отклонено</b>", parse_mode=ParseMode.HTML)

    await callback.answer()


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
