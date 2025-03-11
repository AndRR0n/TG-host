import logging
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Проверка обязательных параметров
if not BOT_TOKEN or not ADMIN_ID:
    logger.error("Отсутствуют обязательные переменные окружения: BOT_TOKEN или ADMIN_ID")
    exit(1)

# Жестко закодированные сообщения
WELCOME_MESSAGE = (
"Здравствуйте!\n\n<b>Здесь Вы можете анонимно сообщить о противоправных действиях сотрудников правоохранительных органов Крыма.</b>\nВаша информация будет рассмотрена в кратчайшие сроки!\n\nМожете оставить свои контактные данные для обратной связи."
)
INACTIVITY_MESSAGE = (
"Информация получена и будет направлена по компетенции.\nЕсли хотите что-то добавить, просто напишите сюда.\nПожалуйста, оставьте свои контактные данные для обратной связи."
)

THANK_YOU_DELAY = 30
user_activity = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_info = (
        f"Имя: {user.first_name or 'Не указано'}\n"
        f"Фамилия: {user.last_name or 'Не указано'}\n"
        f"Никнейм: @{user.username or 'Не указан'}\n"
        f"ID: {user.id}"
    )

    # Отправка сообщения администратору
    try:
        if update.message.text:
            await context.bot.send_message(
                ADMIN_ID,
                f"<b>Новое сообщение от пользователя:</b>\n{user_info}\n\n"
                f"<b>Сообщение:</b>\n{update.message.text}",
                parse_mode=ParseMode.HTML
            )
        # Для всех медиа-типов (включая голосовые, файлы, фото, видео и т.д.)
        else:
            # Формируем описание контента
            content_type = "Файл"
            if update.message.voice: content_type = "Голосовое сообщение"
            elif update.message.document: content_type = "Документ"
            elif update.message.photo: content_type = "Фото"
            elif update.message.video: content_type = "Видео"

            # Отправляем уведомление администратору
            await context.bot.send_message(
                ADMIN_ID,
                f"<b>Новое {content_type} от пользователя:</b>\n{user_info}",
                parse_mode=ParseMode.HTML
            )
            
            # Пересылаем оригинальное сообщение
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
    except Exception as e:
        logger.error(f"Ошибка при пересылке сообщения: {e}")

    # Обновление активности пользователя
    if user.id in user_activity:
        user_activity[user.id].cancel()
    
    new_task = context.application.create_task(
        handle_inactivity(context, user.id)
    )
    user_activity[user.id] = new_task

async def handle_inactivity(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    try:
        await asyncio.sleep(THANK_YOU_DELAY)
        if user_id in user_activity:
            del user_activity[user_id]
            await context.bot.send_message(
                chat_id=user_id,
                text=INACTIVITY_MESSAGE
            )
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")

async def run_bot():
    while True:
        try:
            async with Application.builder().token(BOT_TOKEN).build() as app:
                app.add_handler(CommandHandler("start", start))
                app.add_handler(MessageHandler(filters.ALL, handle_message))
                
                await app.initialize()
                await app.start()
                await app.updater.start_polling()
                logger.info("Бот запущен")
                await asyncio.Event().wait()

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}. Перезапуск...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_bot())
