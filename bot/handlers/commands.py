"""Command handlers for the bot."""
from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.models import Memory, User
from sqlalchemy import select


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
        "Я помогу вам сохранить ваши воспоминания и создать красивую книгу.\n\n"
        "<b>Что я умею:</b>\n"
        "📝 Сохранять текстовые сообщения\n"
        "🎤 Транскрибировать голосовые заметки\n"
        "📷 Сохранять фотографии\n"
        "🏷️ Распознавать теги (#тег)\n"
        "📚 Генерировать PDF-книгу\n\n"
        "<b>Команды:</b>\n"
        "/help - показать справку\n"
        "/add - добавить воспоминание\n"
        "/list - список воспоминаний\n"
        "/book - сгенерировать книгу\n\n"
        "Просто отправьте мне сообщение, и я сохраню его!"
    )
    logger.info(f"User {message.from_user.id} started the bot")


async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
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
        "Книга будет разбита на главы по неделям."
    )
    logger.info(f"User {message.from_user.id} requested help")


async def cmd_add(message: Message) -> None:
    """Handle /add command - placeholder for manual add."""
    await message.answer(
        "📝 <b>Добавление воспоминания</b>\n\n"
        "Просто отправьте мне сообщение с вашим воспоминанием!\n"
        "Не забудьте добавить теги через #, например:\n"
        '"Отличный день на пляже #лето #отпуск"\n\n'
        "Вы также можете отправить голосовое сообщение или фото."
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
            "и я сохраню это как воспоминание!"
        )
        return
    
    response = "📚 <b>Ваши последние воспоминания:</b>\n\n"
    for i, memory in enumerate(memories, 1):
        content_preview = memory.content[:50] + "..." if len(memory.content) > 50 else memory.content
        tags = f" ({', '.join(memory.tags)})" if memory.tags else ""
        response += f"{i}. {content_preview}{tags}\n"
        response += f"   📅 {memory.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    await message.answer(response)
    logger.info(f"User {user_id_tg} listed memories")


async def cmd_book(message: Message) -> None:
    """Handle /book command - generate PDF book."""
    await message.answer(
        "📚 <b>Генерация книги</b>\n\n"
        "Начинаю создание вашей книги воспоминаний...\n"
        "Это может занять несколько минут.\n\n"
        "⏳ Пожалуйста, подождите."
    )
    try:
        from bot.services.book_generator import generate_book
        from db.database import get_session_factory
        
        session_factory = get_session_factory()
        pdf_path = await generate_book(message.from_user.id, session_factory)
        
        with open(pdf_path, 'rb') as f:
            await message.answer_document(
                document=f,
                caption="📖 Ваша книга воспоминаний готова!\n\nПриятного чтения! 🌟",
                filename="memory_book.pdf"
            )
        logger.info(f"Book generated for user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error generating book: {e}")
        await message.answer(
            "❌ Произошла ошибка при генерации книги.\n"
            "Пожалуйста, попробуйте позже или обратитесь к разработчику."
        )


def register_command_handlers(dp: Dispatcher) -> None:
    """Register all command handlers."""
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_add, Command("add"))
    dp.message.register(cmd_list, Command("list"))
    dp.message.register(cmd_book, Command("book"))