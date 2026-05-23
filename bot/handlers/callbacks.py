"""Callback query handlers for inline keyboards."""
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from loguru import logger
from bot.keyboards.main import get_back_keyboard, get_main_keyboard


async def handle_callback_help_add(callback: CallbackQuery) -> None:
    """Handle help_add callback."""
    await callback.message.edit_text(
        "📝 <b>Как добавить воспоминание:</b>\n\n"
        "1. Нажмите кнопку '📝 Добавить воспоминание'\n"
        "2. Отправьте текстовое сообщение, фото или голосовую заметку\n"
        "3. Добавьте теги через # (например: #лето #отпуск)\n"
        "4. Бот автоматически сохранит ваше воспоминание",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed help_add")


async def handle_callback_help_book(callback: CallbackQuery) -> None:
    """Handle help_book callback."""
    await callback.message.edit_text(
        "📖 <b>Как создать книгу:</b>\n\n"
        "1. Нажмите кнопку '📖 Создать книгу'\n"
        "2. Бот соберёт все ваши воспоминания\n"
        "3. Воспоминания будут сгруппированы по неделям\n"
        "4. Вы получите PDF-файл с вашей книгой",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed help_book")


async def handle_callback_help_tags(callback: CallbackQuery) -> None:
    """Handle help_tags callback."""
    await callback.message.edit_text(
        "🏷️ <b>Работа с тегами:</b>\n\n"
        "Теги помогают организовать воспоминания.\n\n"
        "Примеры:\n"
        "• 'Отличный день на пляже #лето #отпуск'\n"
        "• 'Встреча с друзьями #друзья #вечер'\n"
        "• 'Первый снег #зима #природа'\n\n"
        "Теги будут отображаться в книге и помогут найти нужные воспоминания.",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed help_tags")


async def handle_callback_back(callback: CallbackQuery) -> None:
    """Handle back callback - return to main menu."""
    await callback.message.edit_text(
        "👋 <b>Memory Book Bot</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} went back")


async def handle_callback_confirm_yes(callback: CallbackQuery) -> None:
    """Handle confirm yes callback."""
    await callback.answer("✅ Подтверждено!", show_alert=True)
    logger.info(f"User {callback.from_user.id} confirmed action")


async def handle_callback_confirm_no(callback: CallbackQuery) -> None:
    """Handle confirm no callback."""
    await callback.answer("❌ Отменено", show_alert=True)
    logger.info(f"User {callback.from_user.id} cancelled action")


def register_callback_handlers(dp: Dispatcher) -> None:
    """Register all callback query handlers."""
    dp.callback_query.register(handle_callback_help_add, F.data == "help_add")
    dp.callback_query.register(handle_callback_help_book, F.data == "help_book")
    dp.callback_query.register(handle_callback_help_tags, F.data == "help_tags")
    dp.callback_query.register(handle_callback_back, F.data == "back")
    dp.callback_query.register(handle_callback_confirm_yes, F.data == "confirm_yes")
    dp.callback_query.register(handle_callback_confirm_no, F.data == "confirm_no")
