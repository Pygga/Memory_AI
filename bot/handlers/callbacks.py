"""Callback query handlers for inline keyboards."""
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from loguru import logger
from bot.keyboards.main import get_back_keyboard, get_help_keyboard, get_main_menu_inline_keyboard
from bot.states import StoryStates


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
    """Handle menu book callback - show stories list first."""
    from db.database import get_session_factory
    session_factory = get_session_factory()
    async with session_factory() as session:
        from db.models import User, Story
        from sqlalchemy import select
        
        result = await session.execute(
            select(User.id).where(User.telegram_id == callback.from_user.id)
        )
        user_record = result.scalar_one_or_none()
        
        if not user_record:
            await callback.message.edit_text("Пожалуйста, сначала запустите бота командой /start")
            await callback.answer()
            return
            
        result = await session.execute(
            select(Story)
            .where(Story.user_id == user_record)
            .order_by(Story.created_at.desc())
        )
        stories = result.scalars().all()
        
    if not stories:
        await callback.message.edit_text("У вас пока нет историй. Сначала создайте историю и добавьте воспоминания!", reply_markup=get_back_keyboard())
        await callback.answer()
        return
        
    from bot.keyboards.main import get_stories_keyboard
    await callback.message.edit_text(
        "📚 <b>Выберите историю для генерации книги:</b>",
        reply_markup=get_stories_keyboard(stories)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} clicked menu_book and is selecting a story")

async def handle_select_story(callback: CallbackQuery) -> None:
    """Handle story selection - show themes."""
    story_id = int(callback.data.replace("select_story_", ""))
    from bot.keyboards.main import get_theme_selection_keyboard
    
    await callback.message.edit_text(
        "🎨 <b>Выберите дизайн вашей книги:</b>\n\n"
        "• <b>Классический</b> - строгий стиль, шрифты с засечками.\n"
        "• <b>Современный</b> - яркий, с градиентами и закруглениями.\n"
        "• <b>Деловой</b> - строгий минимализм.",
        reply_markup=get_theme_selection_keyboard(story_id)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected story {story_id} and is selecting a theme")

async def start_book_generation(message: Message, user_tg_id: int, story_id: int, theme: str, signature: str = None) -> None:
    """Helper to run book generation and send it to user."""
    from db.database import get_session_factory
    
    # Translate theme to Russian name for printing
    theme_names = {
        "classic": "Классический",
        "modern": "Современный",
        "business": "Деловой"
    }
    theme_name = theme_names.get(theme, theme)
    
    status_msg = await message.answer(
        f"📚 <b>Генерация книги (Дизайн: {theme_name})</b>\n\n"
        "Начинаю создание вашей книги...\n"
        "Это может занять несколько минут.\n\n"
        "⏳ Пожалуйста, подождите."
    )
    
    try:
        from bot.services.book_generator import generate_book
        
        async def update_progress(current: int, total: int):
            try:
                await status_msg.edit_text(
                    f"📚 <b>Генерация книги (Дизайн: {theme_name})</b>\n\n"
                    f"✍️ Пишу историю... Глава {current} из {total}\n\n"
                    f"⏳ Пожалуйста, подождите."
                )
            except Exception:
                pass
        
        session_factory = get_session_factory()
        pdf_path, has_fallback = await generate_book(
            user_tg_id, 
            session_factory, 
            progress_callback=update_progress,
            theme=theme,
            story_id=story_id,
            signature=signature
        )
        
        from aiogram.types import FSInputFile
        document_to_send = FSInputFile(path=pdf_path, filename="memory_book.pdf")
        
        caption = "📖 Ваша книга готова!\n\nПриятного чтения! 🌟"
        if has_fallback:
            caption = "⚠️ <b>Вы получили базовую генерацию книги без связанных историй (ошибка подключения к нейросети). Попробуйте позже.</b>\n\n" + caption
            
        await message.answer_document(
            document=document_to_send,
            caption=caption
        )
        await status_msg.delete()
        logger.info(f"Book generated for user {user_tg_id} with theme {theme}, story {story_id}, signature: {signature}")
        
    except ValueError as ve:
        logger.warning(f"Validation error during book generation: {ve}")
        await message.answer(f"❌ Невозможно создать книгу: {ve}")
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Error generating book: {e}")
        await message.answer(
            "❌ Произошла ошибка при генерации книги.\n"
            "Пожалуйста, попробуйте позже или обратитесь к разработчику."
        )
        try:
            await status_msg.delete()
        except Exception:
            pass

async def handle_generate_book_theme(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle theme selection and ask for custom signature."""
    # data is like 'generate_book_{story_id}_{theme}'
    parts = callback.data.split('_')
    story_id = int(parts[2])
    theme = parts[3]
    
    # Store in FSM state
    await state.update_data(story_id=story_id, theme=theme)
    await state.set_state(StoryStates.waiting_for_signature)
    
    from bot.keyboards.main import get_skip_signature_keyboard
    
    await callback.message.edit_text(
        "✍️ <b>Добавьте финальную подпись для вашей книги!</b>\n\n"
        "Она будет напечатана на последней странице вместо статистики.\n"
        "Например: <i>«С любовью, твоя семья»</i>, <i>«Жизнь измеряется не количеством вдохов, а моментами, от которых захватывает дух»</i> или просто ваши имена.\n\n"
        "<b>Напишите текст подписи прямо в чат</b> или нажмите кнопку ниже, чтобы пропустить этот шаг.",
        reply_markup=get_skip_signature_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected theme {theme} for story {story_id}, waiting for signature")

async def handle_skip_signature(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle skipping the custom signature and starting book generation."""
    state_data = await state.get_data()
    story_id = state_data.get("story_id")
    theme = state_data.get("theme")
    
    if not story_id or not theme:
        await callback.message.edit_text("❌ Произошла ошибка. Пожалуйста, начните генерацию заново.")
        await state.clear()
        await callback.answer()
        return
        
    await state.clear()
    
    # Delete the prompt message to keep chat clean
    await callback.message.delete()
    
    # Start generation with signature = None
    await start_book_generation(callback.message, callback.from_user.id, story_id, theme, signature=None)
    await callback.answer()

async def handle_callback_menu_help(callback: CallbackQuery) -> None:
    """Handle menu help callback."""
    await callback.message.edit_text(
        "ℹ️ <b>Как правильно пользоваться ботом:</b>\n\n"
        "<b>Шаг 1: Начать книгу</b>\n"
        "Нажмите кнопку «🆕 Начать новую книгу» и задайте название (например: 'Отпуск 2026'). Бот начнет собирать всё в эту книгу.\n\n"
        "<b>Шаг 2: Наполняйте книгу</b>\n"
        "Просто отправляйте боту фото, голосовые кружочки или текст. Они будут автоматически сохранены.\n\n"
        "<b>Шаг 3: Тегируйте (по желанию)</b>\n"
        "Используйте #теги в тексте (например: #море), чтобы воспоминания было легче находить.\n\n"
        "<b>Шаг 4: Сгенерируйте PDF!</b>\n"
        "Когда накопится достаточно моментов, нажмите «📖 Сгенерировать PDF». Бот попросит выбрать нужную книгу из списка, затем дизайн (Классика, Модерн, Бизнес) и сгенерирует для вас красивый PDF-файл.\n\n"
        "<i>Вы в любой момент можете просмотреть старые записи через меню «📚 Архив книг».</i>",
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
    dp.callback_query.register(handle_select_story, F.data.startswith("select_story_"))
    dp.callback_query.register(handle_generate_book_theme, F.data.startswith("generate_book_"))
    dp.callback_query.register(handle_skip_signature, F.data == "skip_signature")
    dp.callback_query.register(handle_buy_credits, F.data == "buy_credits")
    dp.callback_query.register(handle_callback_menu_help, F.data == "menu_help")
    dp.callback_query.register(handle_callback_confirm_yes, F.data == "confirm_yes")
    dp.callback_query.register(handle_callback_confirm_no, F.data == "confirm_no")
