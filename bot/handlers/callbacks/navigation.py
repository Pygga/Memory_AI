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
        "1. Нажмите кнопку '📝 Добавить воспоминание'\n"
        "2. Отправьте текстовое сообщение, фото или голосовую заметку\n"
        "3. Добавьте теги через # (например: #лето #отпуск)\n"
        "4. Бот автоматически сохранит ваше воспоминание",
        reply_markup=get_back_to_help_keyboard()
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
        reply_markup=get_back_to_help_keyboard()
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


async def handle_callback_menu_help(callback: CallbackQuery) -> None:
    """Handle menu help callback."""
    await callback.message.edit_text(
        "ℹ️ <b>Как правильно пользоваться ботом:</b>\n\n"
        "<b>Шаг 1: Создание книги</b>\n"
        "Нажмите кнопку «🆕 Начать новую книгу» и задайте название. Бот начнет собирать все новые воспоминания в эту книгу.\n\n"
        "<b>Шаг 2: Наполнение воспоминаниями</b>\n"
        "Просто отправляйте боту фото, голосовые или текст. Вы можете редактировать/удалять отдельные воспоминания через команду /list.\n\n"
        "<b>Шаг 3: Кабинет книги и редактирование глав</b>\n"
        "Нажмите «📖 Сгенерировать PDF» или «📚 Архив книг» и выберите вашу книгу. Вы попадете в **Кабинет книги**:\n"
        "• Нажмите <i>«📖 Читать / Редактировать главы»</i> — ИИ разобьет ваши записи на 3–5 смысловых глав с красивыми заголовками.\n"
        "• Выберите главу, чтобы прочитать её. Вы можете нажать <i>«✏️ Изменить текст»</i> и отправить новые правки или нажать <i>«🔄 Перегенерировать ИИ»</i>, чтобы ИИ переписал главу заново.\n"
        "• Нажмите <i>«🔄 Пересобрать книгу заново»</i>, если хотите полностью изменить структуру и сбросить правки.\n\n"
        "<b>Шаг 4: Скачивание PDF</b>\n"
        "В Кабинете книги нажмите <i>«🖨️ Сгенерировать PDF-книгу»</i>, выберите стиль оформления (Классика, Модерн, Бизнес), введите финальную подпись для задней обложки, и бот соберет для вас готовый файл!",
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
        "📝 <b>Новая книга</b>\n\n"
        "Как вы хотите назвать эту книгу? (например, 'Отпуск в горах 2026' или 'Мои выходные')\n\n"
        "<i>Все ваши дальнейшие воспоминания будут привязываться к ней.</i>",
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
        f"Уровень подписки: {tier}\n"
        f"Осталось генераций PDF: <b>{credits}</b>\n\n"
        f"<i>(Тестовый режим: у вас {credits} генераций)</i>",
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

