import asyncio
import logging
import base64
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from supabase import create_client, Client

BOT_TOKEN = "8834826569:AAFmNoXbXDIrFUmTWvXeqOyv1RhnUhUalYE"
SUPABASE_URL = "https://wtgtmeodtuimjvqoqfzc.supabase.co"
SUPABASE_KEY = "sb_secret_5IvU05B2_YifdnV9Vi6u4A_Pk7rCuGa"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Pastki doimiy tugmalar oynasi (Menu Keyboard)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌐 Перейти на сайт"), KeyboardButton(text="ℹ️ О проекте")]
    ],
    resize_keyboard=True
)

def decode_url(safe_url: str) -> str:
    try:
        safe_url = safe_url.replace('-', '+').replace('_', '/')
        padding = len(safe_url) % 4
        if padding:
            safe_url += '=' * (4 - padding)
        decoded_bytes = base64.b64decode(safe_url)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        logging.error(f"Oshibka dekodirovaniya URL: {e}")
        return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    args = command.args

    # Gar saytdan kelmagan bo'lsa (Oddiy /start)
    if not args or not args.startswith("p_"):
        await message.answer(
            "👋 **Добро пожаловать в бота BIDmesto!**\n\n"
            "Чтобы занять место в рейтинге и сделать ставку, перейдите на сайт **BIDmesto.lol**.",
            reply_markup=main_keyboard,
            parse_mode="Markdown"
        )
        return

    # Saytdan havolali kelganda:
    try:
        parts = args.split('_', 3)
        if len(parts) < 4:
            await message.answer("❌ Неверный формат ссылки.", reply_markup=main_keyboard)
            return

        _, amount_str, cat, encoded_url = parts
        amount = int(amount_str)
        real_url = decode_url(encoded_url)

        if not real_url:
            await message.answer("❌ Ошибка при чтении ссылки.", reply_markup=main_keyboard)
            return

        caption = (
            f"🛒 **Новый заказ на размещение!**\n\n"
            f"🔗 **Ссылка:** {real_url}\n"
            f"📂 **Категория:** {cat}\n"
            f"💰 **Сумма ставки:** {amount:,} so'm\n\n"
            f"Подтвердите оплату, чтобы опубликовать объявление на сайте:"
        )

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=f"💳 Оплатить {amount:,} so'm", 
                        callback_data=f"pay_{amount}_{cat}_{encoded_url}"
                    )
                ]
            ]
        )

        await message.answer(caption, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Oshibka v start handler: {e}")
        await message.answer("❌ Произошла ошибка при обработке заказа.", reply_markup=main_keyboard)

@dp.message(F.text == "🌐 Перейти на сайт")
async def open_site(message: types.Message):
    await message.answer("Наш сайт: https://bidmesto.lol")

@dp.message(F.text == "ℹ️ О проекте")
async def about_project(message: types.Message):
    await message.answer("BIDmesto.lol — открытый рейтинг со ставками за места.")

@dp.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery):
    try:
        parts = callback.data.split('_', 3)
        _, amount_str, cat, encoded_url = parts
        amount = int(amount_str)
        real_url = decode_url(encoded_url)

        data = {
            "url": real_url,
            "cat": cat,
            "bid": amount,
            "clicks": 0
        }
        
        response = supabase.table("entries").insert(data).execute()

        await callback.message.edit_text(
            f"✅ **Оплата успешно подтверждена!**\n\n"
            f"🌐 **Ссылка:** {real_url}\n"
            f"💰 **Ставка:** {amount:,} so'm\n\n"
            f"Ваше объявление уже опубликовано и отображается на **BIDmesto.lol** в режиме реального времени!",
            parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Oshibka zapisi v Supabase: {e}")
        await callback.answer("❌ Ошибка при записи в базу данных!", show_alert=True)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
