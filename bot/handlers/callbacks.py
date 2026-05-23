"""Callback query handlers for inline keyboards."""
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from loguru import logger
from bot.keyboards.main import get_back_keyboard, get_help_keyboard, get_main_menu_inline_keyboard


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
        reply_markup=get_main_menu_inline_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} went back")


async def handle_callback_main_menu(callback: CallbackQuery) -> None:
    """Handle main_menu callback - return to main menu from help."""
    await callback.message.edit_text(
        "👋 <b>Memory Book Bot</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_inline_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} returned to main menu")


async def handle_callback_menu_add(callback: CallbackQuery) -> None:
    """Handle menu add callback."""
    await callback.message.edit_text(
        "📝 <b>Добавление воспоминания</b>\n\n"
        "Просто отправьте мне сообщение с вашим воспоминанием!\n"
        "Не забудьте добавить теги через #, например:\n"
        '"Отличный день на пляже #лето #отпуск"\n\n'
        "Вы также можете отправить голосовое сообщение или фото.",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} clicked menu_add")


async def handle_callback_menu_list(callback: CallbackQuery) -> None:
    """Handle menu list callback."""
    from sqlalchemy import select
    from db.database import get_session_factory
    from db.models import User, Memory
    
    user_id_tg = callback.from_user.id
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        result = await session.execute(
            select(User.id).where(User.telegram_id == user_id_tg)
        )
        user_record = result.scalar_one_or_none()
        
        if not user_record:
            await callback.message.edit_text(
                "📭 У вас пока нет сохранённых воспоминаний.",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        result = await session.execute(
            select(Memory)
            .where(Memory.user_id == user_record)
            .order_by(Memory.created_at.desc())
            .limit(10)
        )
        memories = result.scalars().all()
    
    if not memories:
        await callback.message.edit_text(
            "📭 У вас пока нет сохранённых воспоминаний.\n\n"
            "Отправьте мне сообщение, голосовую заметку или фото, "
            "и я сохраню это как воспоминание!",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    
    response = "📚 <b>Ваши последние воспоминания:</b>\n\n"
    for i, memory in enumerate(memories, 1):
        content_preview = memory.content[:50] + "..." if len(memory.content) > 50 else memory.content
        tags = f" ({', '.join(memory.tags)})" if memory.tags else ""
        response += f"{i}. {content_preview}{tags}\n"
        response += f"   📅 {memory.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    await callback.message.edit_text(response, reply_markup=get_back_keyboard())
    await callback.answer()
    logger.info(f"User {user_id_tg} clicked menu_list")


async def handle_callback_menu_book(callback: CallbackQuery) -> None:
    """Handle menu book callback."""
    from db.database import get_session_factory
    
    await callback.message.edit_text(
        "📚 <b>Генерация книги</b>\n\n"
        "Начинаю создание вашей книги воспоминаний...\n"
        "Это может занять несколько минут.\n\n"
        "⏳ Пожалуйста, подождите.",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()
    
    try:
        from bot.services.book_generator import generate_book
        
        session_factory = get_session_factory()
        pdf_path = await generate_book(callback.from_user.id, session_factory)
        
        with open(pdf_path, 'rb') as f:
            await callback.message.answer_document(
                document=f,
                caption="📖 Ваша книга воспоминаний готова!\n\nПриятного чтения! 🌟",
                filename="memory_book.pdf"
            )
        logger.info(f"Book generated for user {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error generating book: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при генерации книги.\n"
            "Пожалуйста, попробуйте позже или обратитесь к разработчику."
        )


async def handle_callback_menu_help(callback: CallbackQuery) -> None:
    """Handle menu help callback."""
    await callback.message.edit_text(
        "ℹ️ <b>Справка по использованию бота</b>\n\n"
        "<b>Как сохранить воспоминание:</b>\n"
        "1. Отправьте текстовое сообщение\n"
        "2. Отправьте голосовую заметку (будет транскрибирована)\n"
        "3. Отправьте фотографию\n\n"
        "<b>Теги:</b>\n"
        "Используйте #теги в сообщениях для организации:\n"
        '"Сегодня был прекрасный день #счастье #прогулка"\n\n'
        "<b>Команды:</b>\n"
        "/start - начать работу с ботом\n"
        "/add - добавить воспоминание вручную\n"
        "/list - просмотреть список воспоминаний\n"
        "/book - сгенерировать PDF-книгу\n\n"
        "<b>Генерация книги:</b>\n"
        "Отправьте /book и я создам PDF с вашими воспоминаниями!\n"
        "Книга будет разбита на главы по неделям.",
        reply_markup=get_help_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} clicked menu_help")


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
    dp.callback_query.register(handle_callback_main_menu, F.data == "main_menu")
    dp.callback_query.register(handle_callback_menu_add, F.data == "menu_add")
    dp.callback_query.register(handle_callback_menu_list, F.data == "menu_list")
    dp.callback_query.register(handle_callback_menu_book, F.data == "menu_book")
    dp.callback_query.register(handle_callback_menu_help, F.data == "menu_help")
    dp.callback_query.register(handle_callback_confirm_yes, F.data == "confirm_yes")
    dp.callback_query.register(handle_callback_confirm_no, F.data == "confirm_no")
