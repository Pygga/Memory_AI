"""Global error handler for the bot to catch Telegram exceptions and prevent crashes."""
from aiogram import Dispatcher
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

async def global_error_handler(event: ErrorEvent) -> bool:
    """Handle all errors in the bot and prevent crashes."""
    exception = event.exception
    
    if isinstance(exception, TelegramBadRequest):
        err_msg = str(exception)
        
        # 1. Message not modified (harmless user double-click)
        if "message is not modified" in err_msg:
            logger.debug("TelegramBadRequest: message is not modified, ignoring.")
            if event.update.callback_query:
                try:
                    await event.update.callback_query.answer()
                except Exception:
                    pass
            return True
            
        # 2. Message to edit/delete not found (outdated buttons)
        if "message to edit not found" in err_msg or "message to delete not found" in err_msg:
            logger.warning(f"TelegramBadRequest: message not found to edit/delete: {err_msg}")
            
            chat_id = None
            if event.update.callback_query:
                chat_id = event.update.callback_query.message.chat.id
                try:
                    await event.update.callback_query.answer()
                except Exception:
                    pass
            elif event.update.message:
                chat_id = event.update.message.chat.id
                
            if chat_id:
                try:
                    await event.update.bot.send_message(
                        chat_id=chat_id,
                        text="❌ <b>Эта кнопка устарела или меню было удалено.</b>\n\n"
                             "Пожалуйста, откройте меню заново с помощью команды /book или воспользуйтесь главным меню ниже."
                    )
                except Exception as e:
                    logger.error(f"Failed to send session timeout warning: {e}")
            return True
            
        # 3. Callback query too old
        if "query is too old" in err_msg:
            logger.warning("TelegramBadRequest: callback query too old.")
            return True
            
    # For other errors, log them and prevent crashing
    logger.error(f"Unhandled exception in bot update: {exception}", exc_info=exception)
    
    # Try to notify user about unknown system error
    chat_id = None
    if event.update.callback_query:
        chat_id = event.update.callback_query.message.chat.id
        try:
            await event.update.callback_query.answer()
        except Exception:
            pass
    elif event.update.message:
        chat_id = event.update.message.chat.id
        
    if chat_id:
        try:
            await event.update.bot.send_message(
                chat_id=chat_id,
                text="❌ <b>Произошла внутренняя ошибка системы.</b>\nПожалуйста, попробуйте еще раз."
            )
        except Exception as e:
            logger.error(f"Failed to send generic error warning: {e}")
            
    return True

def register_error_handlers(dp: Dispatcher) -> None:
    """Register the global error handler."""
    dp.errors.register(global_error_handler)
