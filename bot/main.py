import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
import sys

from db.database import init_db, get_session_factory
from bot.handlers.text import register_text_handlers
from bot.handlers.voice import register_voice_handlers
from bot.handlers.photo import register_photo_handlers
from bot.handlers.commands import register_command_handlers

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
    
    # Get bot token from environment
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment")
        return
    
    # Create bot and dispatcher
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Register handlers
    register_command_handlers(dp)
    register_text_handlers(dp)
    register_voice_handlers(dp)
    register_photo_handlers(dp)
    
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
