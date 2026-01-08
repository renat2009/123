import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен из переменных окружения Railway
API_TOKEN = os.getenv("API_TOKEN")

# Проверка токена
if not API_TOKEN:
    logger.error("❌ ОШИБКА: API_TOKEN не найден!")
    logger.error("Добавь переменную API_TOKEN в настройках Railway")
    exit(1)

logger.info(f"✅ Токен найден: {API_TOKEN[:10]}...")

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ========== КОМАНДЫ БОТА ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🎉 Бот работает на Railway!\n"
                        "✅ Вебхуки: НЕТ (используем polling)\n"
                        "📞 Команды: /start /help /id /ping")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("ℹ️ Доступные команды:\n"
                        "/start - Проверка работы\n"
                        "/help - Эта справка\n"
                        "/id - Показать ID\n"
                        "/ping - Проверка связи")

@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"🆔 Ваш ID: {message.from_user.id}\n"
                        f"💬 Чат ID: {message.chat.id}")

@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 Pong! Бот жив!")

@dp.message()
async def echo(message: types.Message):
    if message.text.startswith('/'):
        return
    await message.answer(f"📝 Вы написали: {message.text}")

# ========== ЗАПУСК БОТА ==========
async def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск бота на Railway...")
    
    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        logger.info(f"🤖 Бот: @{bot_info.username} (ID: {bot_info.id})")
        
        # Запускаем polling
        logger.info("🔄 Начинаем polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
        logger.error("Возможно Railway блокирует соединение с Telegram")

if __name__ == "__main__":
    asyncio.run(main())
