"""Command handlers for the bot."""
from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.repositories import UserRepository, MemoryRepository, StoryRepository
from bot.keyboards.main import get_main_keyboard, get_help_keyboard


async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    # Ensure user exists in DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        user_repo = UserRepository(session)
        await user_repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        await session.commit()
    
    await message.answer(
        "👋 <b>Добро пожаловать в Memory Book Bot!</b>\n\n"
        "Я — ваш личный архивариус воспоминаний. Я помогу вам сохранить памятные моменты и превратить их в красивую книгу с помощью искусственного интеллекта.\n\n"
        "⚡️ <b>Наши ИИ-возможности:</b>\n"
        "• <b>Умные ИИ-главы</b>: Бот автоматически группирует воспоминания по смыслу и темам в 3–5 глав с красивыми названиями вместо сухой разбивки по неделям.\n"
        "• <b>Интерактивный редактор</b>: Вы можете читать главы прямо в Telegram, редактировать их вручную или перегенерировать одной кнопкой через ИИ в <i>Кабинете книги</i>.\n"
        "• <b>Красивый PDF-макет</b>: Поддержка изысканных шрифтов, книжных стандартов верстки, скругления фото и вашей финальной подписи.\n\n"
        "<b>Ваш план действий:</b>\n"
        "1️⃣ Нажмите <b>«🆕 Начать новую книгу»</b> и введите название (например, 'Отпуск' или 'Дневник 2026').\n"
        "2️⃣ Отправляйте мне текст, фото или голосовые сообщения. Я сохраню всё в вашу текущую книгу.\n"
        "3️⃣ Нажмите <b>«📖 Сгенерировать PDF»</b> или зайдите в <b>«📚 Архив книг»</b>, чтобы открыть <b>Кабинет книги</b>, отредактировать главы и скачать ваш шедевр!\n\n"
        "Готовы начать? Жмите <b>«🆕 Начать новую книгу»</b> в меню ниже!",
        reply_markup=get_main_keyboard()
    )
    logger.info(f"User {message.from_user.id} started the bot")


async def cmd_help(message: Message) -> None:
    """Handle /help command."""
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
        user_repo = UserRepository(session)
        user_record = await user_repo.get_by_telegram_id(user_id_tg)
        
        if not user_record:
            await message.answer("📭 У вас пока нет сохранённых воспоминаний.")
            return
        
        memory_repo = MemoryRepository(session)
        memories = await memory_repo.get_latest_by_user(user_record.id, limit=10)
    
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
        user_repo = UserRepository(session)
        user_record = await user_repo.get_by_telegram_id(message.from_user.id)
        
        if not user_record:
            await message.answer("Пожалуйста, сначала запустите бота командой /start")
            return
            
        story_repo = StoryRepository(session)
        stories = await story_repo.get_all_by_user_id(user_record.id)
        
    if not stories:
        await message.answer("У вас пока нет историй. Сначала создайте историю и добавьте воспоминания!")
        return
        
    from bot.keyboards.main import get_stories_keyboard
    await message.answer(
        "📚 <b>Выберите книгу для открытия Кабинета управления (редактирование глав и генерация PDF):</b>",
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