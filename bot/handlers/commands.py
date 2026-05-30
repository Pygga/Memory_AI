"""Command handlers for the bot."""
from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.models import Memory, User
from sqlalchemy import select
from bot.keyboards.main import get_main_keyboard, get_help_keyboard


async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    # Ensure user exists in DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        from db.users import get_or_create_user
        await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        await session.commit()
    
    await message.answer(
        "👋 <b>Добро пожаловать в Memory Book Bot!</b>\n\n"
        "Я — ваш личный архивариус воспоминаний. Я помогу вам сохранить памятные моменты и превратить их в красивую книгу.\n\n"
        "<b>Ваш план действий:</b>\n"
        "1️⃣ Нажмите <b>«🆕 Начать новую книгу»</b> и введите название (например, 'Отпуск' или 'Дневник 2026').\n"
        "2️⃣ Отправляйте мне текст, фото или голосовые сообщения. Я сохраню всё в вашу текущую книгу.\n"
        "3️⃣ Добавляйте #теги к сообщениям для удобства.\n"
        "4️⃣ Нажмите <b>«📖 Сгенерировать PDF»</b>, когда накопите достаточно моментов, и я создам для вас файл!\n\n"
        "Готовы начать? Жмите <b>«🆕 Начать новую книгу»</b> в меню ниже!",
        reply_markup=get_main_keyboard()
    )
    logger.info(f"User {message.from_user.id} started the bot")


async def cmd_help(message: Message) -> None:
    """Handle /help command."""
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
        reply_markup=get_help_keyboard()
    )
    logger.info(f"User {message.from_user.id} requested help")


async def cmd_add(message: Message) -> None:
    """Handle /add command - placeholder for manual add."""
    await message.answer(
        "📝 <b>Добавление воспоминания</b>\n\n"
        "Просто отправьте мне сообщение с вашим воспоминанием!\n"
        "Не забудьте добавить теги через #, например:\n"
        '"Отличный день на пляже #лето #отпуск"\n\n'
        "Вы также можете отправить голосовое сообщение или фото.",
        reply_markup=get_main_keyboard()
    )
    logger.info(f"User {message.from_user.id} used /add command")


async def cmd_list(message: Message) -> None:
    """Handle /list command - show memories list."""
    user_id_tg = message.from_user.id
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # First get internal user.id by telegram_id
        result = await session.execute(
            select(User.id).where(User.telegram_id == user_id_tg)
        )
        user_record = result.scalar_one_or_none()
        
        if not user_record:
            await message.answer("📭 У вас пока нет сохранённых воспоминаний.")
            return
        
        # Now fetch memories by internal user.id
        result = await session.execute(
            select(Memory)
            .where(Memory.user_id == user_record)
            .order_by(Memory.created_at.desc())
            .limit(10)
        )
        memories = result.scalars().all()
    
    if not memories:
        await message.answer(
            "📭 У вас пока нет сохранённых воспоминаний.\n\n"
            "Отправьте мне сообщение, голосовую заметку или фото, "
            "и я сохраню это как воспоминание!",
            reply_markup=get_main_keyboard()
        )
        return
    
    response = "📚 <b>Ваши последние воспоминания:</b>\n\n"
    for i, memory in enumerate(memories, 1):
        content_preview = memory.content[:50] + "..." if len(memory.content) > 50 else memory.content
        tags = f" ({', '.join(memory.tags)})" if memory.tags else ""
        response += f"{i}. {content_preview}{tags}\n"
        response += f"   📅 {memory.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    await message.answer(response, reply_markup=get_main_keyboard())
    logger.info(f"User {user_id_tg} listed memories")


async def cmd_book(message: Message) -> None:
    """Handle /book command - show stories selection."""
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
        await message.answer("У вас пока нет историй. Сначала создайте историю и добавьте воспоминания!")
        return
        
    from bot.keyboards.main import get_stories_keyboard
    await message.answer(
        "📚 <b>Выберите историю для генерации книги:</b>",
        reply_markup=get_stories_keyboard(stories)
    )
    logger.info(f"User {message.from_user.id} used /book and is selecting a story")


def register_command_handlers(dp: Dispatcher) -> None:
    """Register all command handlers."""
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_add, Command("add"))
    dp.message.register(cmd_list, Command("list"))
    dp.message.register(cmd_book, Command("book"))