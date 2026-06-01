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

    elif text == "📚 Архив книг" or text == "📖 Сгенерировать PDF":
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
        if text == "📖 Сгенерировать PDF":
            await message.answer(
                "📚 <b>Выберите книгу для генерации PDF:</b>",
                reply_markup=get_stories_keyboard(stories)
            )
        else:
            await message.answer(
                "📂 <b>Ваш архив книг:</b>\n"
                "<i>(выберите книгу для генерации PDF)</i>",
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
            "<b>Шаг 1: Начать книгу</b>\n"
            "Нажмите кнопку «🆕 Начать новую книгу» и задайте название (например: 'Отпуск 2026'). Бот начнет собирать всё в эту книгу.\n\n"
            "<b>Шаг 2: Наполняйте книгу</b>\n"
            "Просто отправляйте боту фото, голосовые кружочки или текст. Они будут автоматически сохранены.\n\n"
            "<b>Шаг 3: Тегируйте (по желанию)</b>\n"
            "Используйте #теги в тексте (например: #море), чтобы воспоминания было легче находить.\n\n"
            "<b>Шаг 4: Сгенерируйте PDF!</b>\n"
            "Когда накопится достаточно моментов, нажмите «📖 Сгенерировать PDF». Бот попросит выбрать нужную книгу из списка, затем дизайн (Классика, Модерн, Бизнес) и сгенерирует для вас красивый PDF-файл.\n\n"
            "<i>Вы в любой момент можете просмотреть старые записи через меню «📚 Архив книг».</i>",
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

def register_text_handlers(dp: Dispatcher) -> None:
    """Register text message handlers."""
    # FSM state handler for custom signature
    dp.message.register(handle_signature_input, StoryStates.waiting_for_signature)
    
    # FSM state handler for new story title
    dp.message.register(handle_story_title_input, StoryStates.waiting_for_story_title)
    
    # Register menu button handler first (higher priority)
    dp.message.register(
        handle_menu_button,
        F.text.in_(["🆕 Начать новую книгу", "📖 Сгенерировать PDF", "📚 Архив книг", "💎 Профиль (Подписка)", "❓ Помощь"])
    )
    # Then register regular text handler
    dp.message.register(handle_text_message, F.text & ~F.text.startswith('/'))
