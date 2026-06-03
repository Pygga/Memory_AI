import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
from loguru import logger
import sys

from db.database import init_db, get_session_factory
from bot.handlers.text import register_text_handlers
from bot.handlers.voice import register_voice_handlers
from bot.handlers.photo import register_photo_handlers
from bot.handlers.commands import register_command_handlers
from bot.handlers.callbacks import register_callback_handlers
from bot.handlers.errors import register_error_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("logs/bot.log", rotation="10 MB", level="DEBUG")


async def main():
    """Main function to start the bot."""
    # Initialize database
    await init_db()
    logger.info("Database initialized successfully")
    
    from bot.config import settings
    token = settings.telegram_bot_token
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in settings")
        return
    
    # Create bot and dispatcher
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Set bot commands (Burger menu)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота и приветствие"),
        BotCommand(command="menu", description="Главное меню (управление)"),
        BotCommand(command="list", description="Последние воспоминания"),
        BotCommand(command="help", description="Справка и инструкции")
    ])
    logger.info("Telegram command menu set successfully")
    
    # Register handlers
    register_command_handlers(dp)
    register_text_handlers(dp)
    register_voice_handlers(dp)
    register_photo_handlers(dp)
    register_callback_handlers(dp)
    register_error_handlers(dp)
    
    logger.info("Bot handlers registered")
    
    # Start polling
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.session.close()
        logger.info("Bot session closed")


if __name__ == "__main__":
    asyncio.run(main())
