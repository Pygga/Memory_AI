import asyncio
from arq.connections import RedisSettings
from bot.config import settings
from bot.services.book_generator import generate_book
from db.database import get_session_factory
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

async def generate_book_task(ctx, user_id_tg: int, story_id: int, theme: str, signature: str, status_msg_id: int):
    """Background arq task for rendering PDF book and sending to the user."""
    logger.info(f"Worker picked up PDF task for user {user_id_tg}, story {story_id}")
    
    bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    session_factory = get_session_factory()
    
    # Callback to update progress in chat in real-time
    async def update_progress(current: int, total: int):
        try:
            await bot.edit_message_text(
                chat_id=user_id_tg,
                message_id=status_msg_id,
                text=f"📚 <b>Генерация книги</b>\n\n✍️ Пишу историю... Глава {current} из {total}\n\n⏳ Пожалуйста, подождите."
            )
        except Exception as e:
            logger.debug(f"Progress update edit failed: {e}")
            
    try:
        # Generate the PDF book
        # Run Weasyprint inside asyncio.to_thread to keep worker process event loop fully non-blocking!
        pdf_path, has_fallback = await generate_book(
            user_id_tg=user_id_tg,
            session_factory=session_factory,
            progress_callback=update_progress,
            theme=theme,
            story_id=story_id,
            signature=signature
        )
        
        # Send PDF document to user
        from aiogram.types import FSInputFile
        document_to_send = FSInputFile(path=pdf_path, filename="memory_book.pdf")
        caption = "📖 Ваша книга готова!\n\nПриятного чтения! 🌟"
        if has_fallback:
            caption = "⚠️ <b>Получена базовая генерация (ИИ временно недоступен).</b>\n\n" + caption
            
        await bot.send_document(chat_id=user_id_tg, document=document_to_send, caption=caption)
        
        # Delete progress message
        try:
            await bot.delete_message(chat_id=user_id_tg, message_id=status_msg_id)
        except Exception:
            pass
            
        logger.info(f"Successfully generated and sent book PDF for user {user_id_tg}")
        
    except Exception as e:
        logger.error(f"Error in arq task generate_book_task: {e}", exc_info=True)
        try:
            await bot.send_message(
                chat_id=user_id_tg,
                text="❌ Произошла ошибка при сборке книги.\nПожалуйста, попробуйте позже или обратитесь к разработчику."
            )
            await bot.delete_message(chat_id=user_id_tg, message_id=status_msg_id)
        except Exception:
            pass
    finally:
        await bot.session.close()

class WorkerSettings:
    """arq worker configuration settings."""
    functions = [generate_book_task]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    # Concurrency limit: max 2 simultaneous PDF generations
    max_jobs = 2
