"""Text message handlers."""
from aiogram import Dispatcher, F
from aiogram.types import Message, FSInputFile  # ✅ Добавлен FSInputFile
from loguru import logger
from db.database import get_session_factory
from db.models import Memory
from db.users import get_or_create_user
from utils.helpers import extract_tags
from bot.keyboards.main import get_main_keyboard

async def handle_menu_button(message: Message) -> None:
    """Handle main menu button clicks."""
    text = message.text
    
    if text == "📝 Добавить воспоминание":
        await message.answer(
            "📝 <b>Добавление воспоминания</b>\n\n"
            "Просто отправьте мне сообщение с вашим воспоминанием!\n"
            "Не забудьте добавить теги через #, например:\n"
            '"Отличный день на пляже #лето #отпуск"\n\n'
            "Вы также можете отправить голосовое сообщение или фото.",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"User {message.from_user.id} clicked 'Add memory' button")
    
    elif text == "📚 Мои воспоминания":
        # Trigger the list command logic
        from sqlalchemy import select
        
        user_id_tg = message.from_user.id
        session_factory = get_session_factory()
        
        async with session_factory() as session:
            from db.models import User
            result = await session.execute(
                select(User.id).where(User.telegram_id == user_id_tg)
            )
            user_record = result.scalar_one_or_none()
            
            if not user_record:
                await message.answer("📭 У вас пока нет сохранённых воспоминаний.")
                return
            
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
                response += f" 📅 {memory.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            
            await message.answer(response, reply_markup=get_main_keyboard())
            logger.info(f"User {user_id_tg} clicked 'My memories' button")
    
    elif text == "📖 Создать книгу":
        # Trigger the book generation logic
        await message.answer(
            "📚 <b>Генерация книги</b>\n\n"
            "Начинаю создание вашей книги воспоминаний...\n"
            "Это может занять несколько минут.\n\n"
            "⏳ Пожалуйста, подождите.",
            reply_markup=get_main_keyboard()
        )
        try:
            from bot.services.book_generator import generate_book
            
            session_factory = get_session_factory()
            pdf_path = await generate_book(message.from_user.id, session_factory)
            
            # ✅ ИСПРАВЛЕНО: Отправка через FSInputFile без open()
            document_to_send = FSInputFile(path=pdf_path, filename="memory_book.pdf")
            
            await message.answer_document(
                document=document_to_send,
                caption="📖 Ваша книга воспоминаний готова!\n\nПриятного чтения! 🌟",
                reply_markup=get_main_keyboard()
            )
            logger.info(f"Book generated for user {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Error generating book: {e}")
            await message.answer(
                "❌ Произошла ошибка при генерации книги.\n"
                "Пожалуйста, попробуйте позже или обратитесь к разработчику.",
                reply_markup=get_main_keyboard()
            )
    
    elif text == "❓ Помощь":
        await message.answer(
            "ℹ️ <b>Справка по использованию бота</b>\n\n"
            "<b>Как сохранить воспоминание:</b>\n"
            "1. Отправьте текстовое сообщение\n"
            "2. Отправьте голосовою заметку (будет транскрибирована)\n"
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
            reply_markup=get_main_keyboard()
        )
        logger.info(f"User {message.from_user.id} clicked 'Help' button")

async def handle_text_message(message: Message) -> None:
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
        # Get or create user (returns User with .id)
        user = await get_or_create_user(
            session,
            telegram_id=user_id_tg,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Create memory with INTERNAL user.id (not telegram_id!)
        memory = Memory(
            user_id=user.id,
            content=text,
            memory_type="text",
            tags=tags,
            file_id=None
        )
        session.add(memory)
        await session.commit()
    
    # Send confirmation
    response = f"✅ <b>Воспоминание сохранено!</b>\n\n📝 {text}"
    if tags:
        response += f"\n🏷️ Теги: {', '.join(f'#{tag}' for tag in tags)}"
        
    await message.answer(response)
    logger.info(f"Saved text memory from user {user_id_tg} with tags: {tags}")

def register_text_handlers(dp: Dispatcher) -> None:
    """Register text message handlers."""
    # Register menu button handler first (higher priority)
    dp.message.register(
        handle_menu_button,
        F.text.in_(["📝 Добавить воспоминание", "📚 Мои воспоминания", "📖 Создать книгу", "❓ Помощь"])
    )
    # Then register regular text handler
    dp.message.register(handle_text_message, F.text & ~F.text.startswith('/'))
