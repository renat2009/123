import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import nest_asyncio

# Применяем nest_asyncio для Replit
nest_asyncio.apply()

# Токен бота
API_TOKEN = os.getenv("TELEGRAM_TOKEN", "8284654414:AAFRf1ZqFRDT5TKa0wl2KI4Vh6hn8cODoes")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🎉 Бот работает на Replit!\n"
                        "📞 Напиши /help")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("ℹ️ Команды:\n"
                        "/start - Проверка\n"
                        "/help - Помощь\n"
                        "/id - Твой ID\n"
                        "/test - Тест")

@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"🆔 Твой ID: {message.from_user.id}\n"
                        f"💬 Чат ID: {message.chat.id}")

@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    await message.answer("✅ Тест пройден! Бот жив!")

@dp.message()
async def echo(message: types.Message):
    if message.text.startswith('/'):
        return
    await message.answer(f"📝 Вы сказали: {message.text}")

# ========== ЗАПУСК ==========
async def main():
    """Запуск бота"""
    logger.info("🚀 Запускаем бота...")
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    
    # Запускаем
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Ошибка: {e}")
