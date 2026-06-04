"""Navigation callback handlers: help screens, back, main menu."""
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger
from bot.keyboards.main import get_back_keyboard, get_help_keyboard, get_main_menu_inline_keyboard, get_back_to_help_keyboard
from bot.states import StoryStates


async def handle_callback_help_add(callback: CallbackQuery) -> None:
    """Handle help_add callback."""
    await callback.message.edit_text(
        "📝 <b>Как добавить воспоминание:</b>\n\n"
        "• Просто отправьте в чат текстовое сообщение, фотографию или голосовую заметку.\n"
        "• Добавляйте хэштеги через # (например, <i>#лето #путешествие</i>) для группировки записей по темам.\n"
        "• Бот мгновенно сохранит материалы в текущую активную книгу.",
        reply_markup=get_back_to_help_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed help_add")


async def handle_callback_help_book(callback: CallbackQuery) -> None:
    """Handle help_book callback."""
    await callback.message.edit_text(
        "📖 <b>Как создать книгу:</b>\n\n"
        "• Убедитесь, что у вас есть активная книга и в неё добавлены воспоминания.\n"
        "• Перейдите в <b>«📚 Мои книги»</b>, откройте нужный проект и нажмите <b>«📖 Читать / Редактировать главы»</b>. ИИ автоматически объединит ваши записи в смысловые главы.\n"
        "• Нажмите <b>«🖨️ Сгенерировать PDF-книгу»</b> в Кабинете, выберите оформление и получите готовый макет.",
        reply_markup=get_back_to_help_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed help_book")


async def handle_callback_help_tags(callback: CallbackQuery) -> None:
    """Handle help_tags callback."""
    await callback.message.edit_text(
        "🏷️ <b>Работа с тегами:</b>\n\n"
        "Теги помогают структурировать воспоминания. Бот автоматически распознает слова с решеткой (например, <i>#семья</i> или <i>#праздник</i>) и использует их при компоновке книги.",
        reply_markup=get_back_to_help_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed help_tags")



async def get_main_menu_data(user_id_tg: int, username: str, first_name: str, last_name: str) -> str:
    """Fetch active book info and memories count to construct main menu text."""
    from db.database import get_session_factory
    from db.repositories import UserRepository, StoryRepository, MemoryRepository
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        user_repo = UserRepository(session)
        user_record = await user_repo.get_or_create(
            telegram_id=user_id_tg,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        story_repo = StoryRepository(session)
        active_story = await story_repo.get_active_by_user_id(user_record.id)
        
        memories_count = 0
        if active_story:
            memory_repo = MemoryRepository(session)
            memories = await memory_repo.get_by_user_and_story(user_record.id, active_story.id)
            memories_count = len(memories)
            
    if active_story:
        active_book_info = f"📖 <b>Текущая книга:</b> «{active_story.title}»\n"
        if memories_count > 0:
            active_book_info += f"✍️ <b>Накоплено воспоминаний:</b> {memories_count}\n"
        else:
            active_book_info += "✍️ <b>Воспоминаний пока нет.</b> Отправьте мне текст, фото или голосовое сообщение, чтобы добавить их!\n"
    else:
        active_book_info = "📖 <b>Текущая книга:</b> <i>Не выбрана</i>\n💡 Нажмите <b>«🆕 Начать новую книгу»</b> ниже, чтобы начать запись воспоминаний!\n"
        
    menu_text = (
        "👋 <b>Главное меню Memory Book Bot</b>\n\n"
        f"{active_book_info}\n"
        "Выберите действие:"
    )
    return menu_text


async def handle_callback_back(callback: CallbackQuery, state: FSMContext = None) -> None:
    """Handle back callback - return to main menu."""
    if state:
        await state.clear()
    menu_text = await get_main_menu_data(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
        callback.from_user.last_name
    )
    await callback.message.edit_text(
        menu_text,
        reply_markup=get_main_menu_inline_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} went back")


async def handle_callback_main_menu(callback: CallbackQuery) -> None:
    """Handle main_menu callback - return to main menu from help."""
    menu_text = await get_main_menu_data(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
        callback.from_user.last_name
    )
    await callback.message.edit_text(
        menu_text,
        reply_markup=get_main_menu_inline_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} returned to main menu")


async def handle_callback_menu_add(callback: CallbackQuery) -> None:
    """Handle menu add callback."""
    await callback.message.edit_text(
        "📝 <b>Как добавить воспоминание в текущую книгу:</b>\n\n"
        "Просто отправьте в чат текстовое сообщение, фото или голосовую заметку.\n"
        "Для удобной сортировки вы можете добавлять хэштеги (например, <i>#семья #путешествие</i>).\n\n"
        "<i>Каждое ваше сообщение сразу сохраняется в текущую активную книгу.</i>",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} clicked menu_add")


async def handle_callback_menu_list(callback: CallbackQuery) -> None:
    """Handle menu list callback."""
    from db.database import get_session_factory
    from db.repositories import UserRepository, MemoryRepository
    
    user_id_tg = callback.from_user.id
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        user_repo = UserRepository(session)
        user_record = await user_repo.get_by_telegram_id(user_id_tg)
        
        if not user_record:
            await callback.message.edit_text(
                "📭 У вас пока нет сохранённых воспоминаний.",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return
        
        memory_repo = MemoryRepository(session)
        memories = await memory_repo.get_latest_by_user(user_record.id, limit=10)
    
    if not memories:
        await callback.message.edit_text(
            "📭 У вас пока нет сохранённых воспоминаний.\n\n"
            "Отправьте мне сообщение, и я сохраню это как воспоминание!",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    
    response = "📚 <b>Последние записи:</b>\n\n"
    for i, memory in enumerate(memories, 1):
        content_preview = memory.content[:50] + "..." if len(memory.content) > 50 else memory.content
        tags = f" ({', '.join(memory.tags)})" if memory.tags else ""
        response += f"{i}. {content_preview}{tags}\n"
        response += f"   📅 {memory.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    await callback.message.edit_text(response, reply_markup=get_back_keyboard())
    await callback.answer()
    logger.info(f"User {user_id_tg} clicked menu_list")


async def handle_callback_menu_help(callback: CallbackQuery) -> None:
    """Handle menu help callback."""
    await callback.message.edit_text(
        "ℹ️ <b>Краткое руководство по созданию вашей книги:</b>\n\n"
        "• <b>Начало работы</b>: Создайте новую книгу через меню. Все ваши новые записи, голосовые сообщения и фото будут автоматически попадать в неё.\n"
        "• <b>Кабинет книги</b>: Перейдите в <b>«📚 Мои книги»</b> и выберите нужный проект. Там вы можете запустить ИИ-генерацию глав, отредактировать их вручную или полностью пересобрать.\n"
        "• <b>Скачивание PDF</b>: В Кабинете нажмите <b>«🖨️ Сгенерировать PDF»</b>, выберите стиль верстки и получите готовый макет для печати.\n\n"
        "<i>Используйте команду /menu, чтобы вернуться на главный экран.</i>",
        reply_markup=get_help_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} clicked menu_help")


async def handle_buy_credits(callback: CallbackQuery) -> None:
    """Handle buy credits button (dummy for now)."""
    await callback.answer(
        "💳 Функция оплаты (Telegram Stars) находится в разработке! Архитектура БД уже готова.", 
        show_alert=True
    )
    logger.info(f"User {callback.from_user.id} clicked buy_credits")


async def handle_callback_confirm_yes(callback: CallbackQuery) -> None:
    """Handle confirm yes callback."""
    await callback.answer("✅ Подтверждено!", show_alert=True)
    logger.info(f"User {callback.from_user.id} confirmed action")


async def handle_callback_confirm_no(callback: CallbackQuery) -> None:
    """Handle confirm no callback."""
    await callback.answer("❌ Отменено", show_alert=True)
    logger.info(f"User {callback.from_user.id} cancelled action")


async def handle_callback_menu_new_book(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle menu_new_book callback."""
    await callback.message.edit_text(
        "📝 <b>Создание новой книги</b>\n\n"
        "Введите название для новой книги (например, <i>«Отпуск в горах 2026»</i> или <i>«Мои выходные»</i>).\n\n"
        "<i>Все ваши дальнейшие воспоминания будут автоматически привязываться к ней.</i>",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(StoryStates.waiting_for_story_title)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} triggered new book creation via callback")


async def handle_callback_menu_profile(callback: CallbackQuery) -> None:
    """Handle menu_profile callback."""
    from db.database import get_session_factory
    from db.repositories import UserRepository
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id_tg = callback.from_user.id
    session_factory = get_session_factory()
    async with session_factory() as session:
        user_repo = UserRepository(session)
        user_record = await user_repo.get_by_telegram_id(user_id_tg)
        
    if not user_record:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return
        
    tier = "👑 Premium" if user_record.subscription_tier == "premium" else "🆓 Бесплатный"
    credits = getattr(user_record, "generation_credits", 0)
    
    profile_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить баланс (Stars)", callback_data="buy_credits")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back")]
    ])
    
    await callback.message.edit_text(
        f"👤 <b>Ваш профиль:</b>\n\n"
        f"• Подписка: <b>{tier}</b>\n"
        f"• Доступно генераций PDF: <b>{credits}</b>\n\n"
        f"Вы можете пополнить баланс генераций с помощью Telegram Stars.",
        reply_markup=profile_kb
    )
    await callback.answer()
    logger.info(f"User {user_id_tg} viewed profile via callback")


def register_navigation_handlers(dp: Dispatcher) -> None:
    """Register navigation-related callback handlers."""
    dp.callback_query.register(handle_callback_help_add, F.data == "help_add")
    dp.callback_query.register(handle_callback_help_book, F.data == "help_book")
    dp.callback_query.register(handle_callback_help_tags, F.data == "help_tags")
    dp.callback_query.register(handle_callback_back, F.data == "back")
    dp.callback_query.register(handle_callback_main_menu, F.data == "main_menu")
    dp.callback_query.register(handle_callback_menu_add, F.data == "menu_add")
    dp.callback_query.register(handle_callback_menu_list, F.data == "menu_list")
    dp.callback_query.register(handle_callback_menu_help, F.data == "menu_help")
    dp.callback_query.register(handle_callback_menu_new_book, F.data == "menu_new_book")
    dp.callback_query.register(handle_callback_menu_profile, F.data == "menu_profile")
    dp.callback_query.register(handle_buy_credits, F.data == "buy_credits")
    dp.callback_query.register(handle_callback_confirm_yes, F.data == "confirm_yes")
    dp.callback_query.register(handle_callback_confirm_no, F.data == "confirm_no")

