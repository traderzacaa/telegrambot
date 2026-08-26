import os
import base64
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# Настройки логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 1. НАСТРОЙКИ И КЛЮЧИ
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Вставьте сюда токен вашего бота от @BotFather
ADMIN_ID = 123456789                  # Вставьте ваш личный Telegram ID (узнать в @userinfobot)

SUPABASE_URL = "https://wtgtmeodtuimjvqoqfzc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0Z3RtZW9kdHVpbWp2cW9xZnpjIiwicm9sZSI6ImF2b24iLCJpYXQiOjE3ODc2MDM3NDYsImV4cCI6MjEwMzE3OTc0Nn0.XiW-O2-TQ5m_7yyj7ZNAWJwPHZYMXekpZ9AaaZyfnRg"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Категории
CATS = {
    'all': 'Все категории',
    'ai': '🤖 ИИ и боты',
    'market': '📣 Маркетинг и PR',
    'biz': '💼 Бизнес',
    'dev': '💻 Разработка',
    'social': '📱 Соцсети и каналы',
    'other': '✨ Разное'
}

# Функция безопасного декодирования URL
def safe_b64decode(str_to_decode: str) -> str:
    try:
        rem = len(str_to_decode) % 4
        if rem > 0:
            str_to_decode += '=' * (4 - rem)
        
        str_to_decode = str_to_decode.replace('-', '+').replace('_', '/')
        decoded_bytes = base64.b64decode(str_to_decode)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        logging.error(f"Ошибка декодирования: {e}")
        return ""

# Форматирование суммы (например: 15 000)
def format_money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")

# ОБРАБОТЧИК КОМАНДЫ /start И DEEP-LINK ИЗ САЙТА
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if args and len(args) > 0:
        param = args[0]
        
        # Разбор параметров сайта: p_СУММА_КАТЕГОРИЯ_URL
        if param.startswith("p_"):
            try:
                parts = param.split("_", 3)
                if len(parts) == 4:
                    _, amount_str, cat_key, safe_url = parts
                    
                    amount = int(amount_str)
                    url = safe_b64decode(safe_url)
                    cat_name = CATS.get(cat_key, '✨ Разное')

                    if not url:
                        await update.message.reply_text("❌ Ошибка при чтении ссылки. Попробуйте еще раз с сайта.")
                        return

                    # Сохраняем детали заказа в сессию пользователя
                    context.user_data['order'] = {
                        'bid': amount,
                        'cat': cat_key,
                        'url': url
                    }

                    text = (
                        f"👋 **Здравствуйте, {user.first_name}!**\n\n"
                        f"📌 **Детали вашего заказа:**\n"
                        f"🌐 **Ссылка:** `{url}`\n"
                        f"📂 **Категория:** {cat_name}\n"
                        f"💰 **Сумма оплаты:** `{format_money(amount)} so'm`\n\n"
                        f"💳 **Карта для оплаты:**\n"
                        f"`8600 0000 0000 0000` (Имя владельца)\n\n"
                        f"⚠️ *После оплаты отправьте скриншот или фото чека прямо в этот чат.*"
                    )

                    await update.message.reply_text(text, parse_mode="Markdown")
                    return
            except Exception as e:
                logging.error(f"Ошибка параметров /start: {e}")

    await update.message.reply_text(
        "👋 **Добро пожаловать!**\n\n"
        "Чтобы занять место в рейтинге, перейдите на наш сайт [BIDmesto.lol](https://bidmesto.lol) и оформите заявку.",
        parse_mode="Markdown"
    )

# ОБРАБОТКА ЧЕКА ОБ ОПЛАТЕ ОТ ПОЛЬЗОВАТЕЛЯ (ФОТО ИЛИ ДОКУМЕНТ)
async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    order = context.user_data.get('order')

    if not order:
        await update.message.reply_text(
            "⚠️ **Заказ не найден.**\nПожалуйста, сначала перейдите на сайт [BIDmesto.lol](https://bidmesto.lol) и выберите ставку.",
            parse_mode="Markdown"
        )
        return

    # Подтверждаем пользователю получение
    await update.message.reply_text("✅ **Чек получен!** После проверки администратором ваша ссылка появиться в рейтинге.")

    # Сохраняем данные для администратора
    order_id = f"{user.id}_{order['bid']}"
    context.bot_data[order_id] = {
        'user_id': user.id,
        'user_name': user.full_name,
        'username': user.username,
        'bid': order['bid'],
        'cat': order['cat'],
        'url': order['url']
    }

    # Кнопки для администратора
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{order_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    admin_text = (
        f"📥 **Новый чек об оплате!**\n\n"
        f"👤 **Пользователь:** {user.full_name} (@{user.username})\n"
        f"🌐 **URL:** `{order['url']}`\n"
        f"📂 **Категория:** {CATS.get(order['cat'], order['cat'])}\n"
        f"💰 **Сумма:** `{format_money(order['bid'])} so'm`"
    )

    # Пересылаем чек администратору
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=admin_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif update.message.document:
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=update.message.document.file_id,
            caption=admin_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# ДЕЙСТВИЯ АДМИНИСТРАТОРА (ПОДТВЕРЖДЕНИЕ / ОТКЛОНЕНИЕ)
async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("approve_"):
        order_id = data.replace("approve_", "")
        order_info = context.bot_data.get(order_id)

        if not order_info:
            await query.edit_message_caption(caption="❌ Данные заказа не найдены или уже обработаны.")
            return

        # 1. Добавляем запись в базу данных Supabase
        try:
            res = supabase.from_('entries').insert({
                'url': order_info['url'],
                'cat': order_info['cat'],
                'bid': order_info['bid'],
                'clicks': 0
            }).execute()

            # 2. Обновляем сообщение администратора
            await query.edit_message_caption(
                caption=f"✅ **ПОДТВЕРЖДЕНО И ДОБАВЛЕНО НА САЙТ!**\n\n"
                        f"🌐 `{order_info['url']}`\n"
                        f"💰 `{format_money(order_info['bid'])} so'm`",
                parse_mode="Markdown"
            )

            # 3. Уведомляем пользователя
            await context.bot.send_message(
                chat_id=order_info['user_id'],
                text=f"🎉 **Ваша оплата подтверждена!**\n\nСсылка [{order_info['url']}]({order_info['url']}) успешно добавлена в рейтинг на [BIDmesto.lol](https://bidmesto.lol)!",
                parse_mode="Markdown"
            )

            # Удаляем обработанный заказ
            del context.bot_data[order_id]

        except Exception as e:
            logging.error(f"Ошибка при записи в Supabase: {e}")
            await query.message.reply_text(f"❌ Ошибка добавления в базу: {e}")

    elif data.startswith("reject_"):
        order_id = data.replace("reject_", "")
        order_info = context.bot_data.get(order_id)

        if order_info:
            await query.edit_message_caption(caption="❌ **Заказ отклонен.**", parse_mode="Markdown")
            await context.bot.send_message(
                chat_id=order_info['user_id'],
                text="❌ **Ваша оплата не подтверждена.** Попробуйте снова или обратитесь в службу поддержки."
            )
            del context.bot_data[order_id]

# ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрация хэндлеров
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_receipt))
    app.add_handler(CallbackQueryHandler(handle_admin_action))

    print("🤖 Бот успешно запущен...")
    app.run_polling()

if __name__ == '__main__':
    main()
