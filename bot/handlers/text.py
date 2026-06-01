"""Text message handlers."""
from aiogram import Dispatcher, F
from aiogram.types import Message, FSInputFile  # ✅ Добавлен FSInputFile
from loguru import logger
from db.database import get_session_factory
from db.models import Memory
from db.users import get_or_create_user
from utils.helpers import extract_tags
from bot.keyboards.main import get_main_keyboard, get_back_keyboard

from aiogram.fsm.context import FSMContext
from bot.states import StoryStates
from bot.handlers.callbacks import start_book_generation

async def handle_menu_button(message: Message, state: FSMContext) -> None:
    """Handle main menu button clicks."""
    text = message.text
    
    if text == "🆕 Начать новую книгу":
        await message.answer(
            "📝 <b>Новая книга</b>\n\n"
            "Как вы хотите назвать эту книгу? (например, 'Отпуск в горах 2026' или 'Мои выходные')\n\n"
            "<i>Все ваши дальнейшие воспоминания будут привязываться к ней.</i>",
            reply_markup=get_back_keyboard()
        )
        await state.set_state(StoryStates.waiting_for_story_title)
        logger.info(f"User {message.from_user.id} clicked 'New book' button")

    elif text in ["📚 Мои книги", "📚 Архив книг", "📖 Сгенерировать PDF"]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            from db.models import User, Story
            from sqlalchemy import select
            
            result = await session.execute(
                select(User.id).where(User.telegram_id == message.from_user.id)
            )
            user_record = result.scalar_one_or_none()
            
            if not user_record:
                await message.answer("Пожалуйста, сначала запустите бота командой /start")
                return
                
            result = await session.execute(
                select(Story)
                .where(Story.user_id == user_record)
                .order_by(Story.created_at.desc())
            )
            stories = result.scalars().all()
            
        if not stories:
            await message.answer("У вас пока нет книг. Сначала создайте новую!")
            return
            
        from bot.keyboards.main import get_stories_keyboard
        await message.answer(
            "📂 <b>Ваши книги:</b>\n"
            "<i>(выберите книгу для открытия Кабинета управления, редактирования глав и генерации PDF)</i>",
            reply_markup=get_stories_keyboard(stories)
        )
        logger.info(f"User {message.from_user.id} wants to select a story")
        
    elif text == "💎 Профиль (Подписка)":
        user_id_tg = message.from_user.id
        session_factory = get_session_factory()
        async with session_factory() as session:
            from db.models import User
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.telegram_id == user_id_tg))
            user_record = result.scalar_one_or_none()
            
        if user_record:
            tier = "👑 Premium" if user_record.subscription_tier == "premium" else "🆓 Бесплатный"
            credits = getattr(user_record, "generation_credits", 0)
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            pay_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="buy_credits")]])
            
            await message.answer(
                f"👤 <b>Ваш профиль:</b>\n\n"
                f"Уровень подписки: {tier}\n"
                f"Осталось генераций PDF: <b>{credits}</b>\n\n"
                f"<i>(Тестовый режим: у вас {credits} генераций)</i>",
                reply_markup=pay_kb
            )
        
    elif text == "❓ Помощь":
        await message.answer(
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
            reply_markup=get_main_keyboard()
        )
        logger.info(f"User {message.from_user.id} clicked 'Help' button")

async def handle_story_title_input(message: Message, state: FSMContext) -> None:
    """Handle input for new story title."""
    title = message.text.strip()
    if not title:
        return
        
    user_id_tg = message.from_user.id
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        from db.models import User, Story
        from sqlalchemy import select, update
        
        user = await get_or_create_user(
            session,
            telegram_id=user_id_tg,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Deactivate all existing stories
        await session.execute(
            update(Story).where(Story.user_id == user.id).values(is_active=0)
        )
        
        # Create new story
        new_story = Story(
            user_id=user.id,
            title=title,
            is_active=1
        )
        session.add(new_story)
        await session.commit()
        
    await state.clear()
    await message.answer(
        f"✅ <b>История «{title}» создана!</b>\n\n"
        f"Теперь все новые воспоминания будут сохраняться в неё.",
        reply_markup=get_main_keyboard()
    )
    logger.info(f"User {user_id_tg} created new story: {title}")

async def handle_signature_input(message: Message, state: FSMContext) -> None:
    """Handle text input for custom book signature and start generation."""
    signature = message.text.strip()
    
    state_data = await state.get_data()
    story_id = state_data.get("story_id")
    theme = state_data.get("theme")
    
    if not story_id or not theme:
        await message.answer("❌ Произошла ошибка. Пожалуйста, начните генерацию заново.")
        await state.clear()
        return
        
    await state.clear()
    
    # Start generation with custom signature
    await start_book_generation(message, message.from_user.id, story_id, theme, signature=signature)

async def handle_text_message(message: Message, state: FSMContext) -> None:
    """Handle regular text messages."""
    if not message.text or message.text.startswith('/'):
        return
    text = message.text
    user_id_tg = message.from_user.id
    
    # Extract tags
    tags = extract_tags(text)
    
    # Save to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        from db.models import User, Story
        from sqlalchemy import select
        
        # Get or create user (returns User with .id)
        user = await get_or_create_user(
            session,
            telegram_id=user_id_tg,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Get active story
        result = await session.execute(
            select(Story).where(Story.user_id == user.id, Story.is_active == 1)
        )
        active_story = result.scalar_one_or_none()
        
        # Create memory with INTERNAL user.id and active story_id
        memory = Memory(
            user_id=user.id,
            story_id=active_story.id if active_story else None,
            content=text,
            memory_type="text",
            tags=tags,
            file_id=None
        )
        session.add(memory)
        await session.commit()
    
    # Send confirmation
    story_context = f" в историю «{active_story.title}»" if active_story else ""
    response = f"✅ <b>Воспоминание сохранено{story_context}!</b>\n\n📝 {text}"
    if tags:
        response += f"\n🏷️ Теги: {', '.join(f'#{tag}' for tag in tags)}"
        
    await message.answer(response)
    logger.info(f"Saved text memory from user {user_id_tg} with tags: {tags}")

async def handle_chapter_edit_input(message: Message, state: FSMContext) -> None:
    """Handle text input for manual chapter editing."""
    new_content = message.text.strip()
    if not new_content:
        return
        
    state_data = await state.get_data()
    chapter_id = state_data.get("chapter_id")
    story_id = state_data.get("story_id")
    
    if not chapter_id:
        await message.answer("❌ Ошибка: не найден идентификатор главы. Пожалуйста, попробуйте сначала.")
        await state.clear()
        return
        
    session_factory = get_session_factory()
    async with session_factory() as session:
        from db.models import Chapter
        from sqlalchemy import update
        
        await session.execute(
            update(Chapter)
            .where(Chapter.id == chapter_id)
            .values(content=new_content)
        )
        await session.commit()
        
    await state.clear()
    
    # Reload updated chapter
    async with session_factory() as session:
        from db.models import Chapter
        from sqlalchemy import select
        result = await session.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        chapter = result.scalar_one_or_none()
        
    if not chapter:
        await message.answer("❌ Ошибка: глава не найдена после обновления.")
        return
        
    from bot.handlers.callbacks import md_to_telegram_html
    from bot.keyboards.main import get_chapter_editor_keyboard
    
    escaped_content = md_to_telegram_html(chapter.content)
    text_to_send = (
        f"✅ <b>Глава {chapter.chapter_number} успешно сохранена!</b>\n\n"
        f"📖 <b>Глава {chapter.chapter_number}. {chapter.title}</b>\n\n"
        f"{escaped_content}"
    )
    if len(text_to_send) > 4000:
        text_to_send = text_to_send[:3950] + "\n\n<i>[Текст сокращен из-за лимитов Telegram...]</i>"
        
    await message.answer(
        text_to_send,
        reply_markup=get_chapter_editor_keyboard(chapter.id, chapter.story_id)
    )

def register_text_handlers(dp: Dispatcher) -> None:
    """Register text message handlers."""
    # FSM state handler for manual chapter editing
    dp.message.register(handle_chapter_edit_input, StoryStates.waiting_for_chapter_edit)

    # FSM state handler for custom signature
    dp.message.register(handle_signature_input, StoryStates.waiting_for_signature)
    
    # FSM state handler for new story title
    dp.message.register(handle_story_title_input, StoryStates.waiting_for_story_title)
    
    # Register menu button handler first (higher priority)
    dp.message.register(
        handle_menu_button,
        F.text.in_(["🆕 Начать новую книгу", "📚 Мои книги", "📖 Сгенерировать PDF", "📚 Архив книг", "💎 Профиль (Подписка)", "❓ Помощь"])
    )
    # Then register regular text handler
    dp.message.register(handle_text_message, F.text & ~F.text.startswith('/'))
