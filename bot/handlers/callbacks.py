"""Callback query handlers for inline keyboards."""
import os
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


async def handle_callback_back(callback: CallbackQuery, state: FSMContext = None) -> None:
    """Handle back callback - return to main menu."""
    if state:
        await state.clear()
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
        "📚 <b>Выберите книгу для открытия Кабинета управления (редактирование глав и генерация PDF):</b>",
        reply_markup=get_stories_keyboard(stories)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} clicked menu_book and is selecting a story")

async def handle_select_story(callback: CallbackQuery) -> None:
    """Handle story selection - show Book Cabinet (story actions)."""
    story_id = int(callback.data.replace("select_story_", ""))
    from db.database import get_session_factory
    from db.models import Story
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from bot.keyboards.main import get_story_actions_keyboard
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Story)
            .where(Story.id == story_id)
            .options(selectinload(Story.chapters))
        )
        story = result.scalar_one_or_none()
        
    if not story:
        await callback.answer("Книга не найдена", show_alert=True)
        return
        
    num_chapters = len(story.chapters)
    chapters_status = f"сформировано {num_chapters} глав" if num_chapters > 0 else "главы ещё не созданы (будут сформированы автоматически при переходе к редактированию)"
    
    await callback.message.edit_text(
        f"📖 <b>Кабинет книги: «{story.title}»</b>\n\n"
        f"Здесь вы можете подготовить и настроить вашу будущую книгу перед печатью в PDF:\n\n"
        f"• <b>Шаг 1: Настройка глав</b> — Нажмите <i>«📖 Читать / Редактировать главы»</i>, чтобы увидеть семантические ИИ-главы. Вы сможете прочитать их, изменить текст вручную или перегенерировать через ИИ.\n"
        f"• <b>Шаг 2: Генерация PDF</b> — Когда всё будет готово, нажмите <i>«🖨️ Сгенерировать PDF-книгу»</i>, чтобы выбрать дизайн, добавить финальную подпись и скачать PDF!\n\n"
        f"📌 <b>Статус глав:</b> {chapters_status}",
        reply_markup=get_story_actions_keyboard(story_id)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected story {story_id} in Cabinet")

async def start_book_generation(message: Message, user_tg_id: int, story_id: int, theme: str, signature: str = None) -> None:
    """Helper to enqueue book generation task using arq."""
    status_msg = await message.answer(
        "⏳ <b>Запрос поставлен в очередь...</b>\n\n"
        "Ожидаем освобождения ИИ-воркера на сервере сборки."
    )
    
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        arq_pool = await create_pool(redis_settings)
        
        # Enqueue the background task
        await arq_pool.enqueue_job(
            'generate_book_task',
            user_tg_id,
            story_id,
            theme,
            signature,
            status_msg.message_id
        )
        logger.info(f"Enqueued generate_book_task for user {user_tg_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue task: {e}")
        await status_msg.edit_text("❌ Ошибка при отправке книги в очередь. Попробуйте еще раз.")

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


import re

def md_to_telegram_html(text: str) -> str:
    """Escapes HTML characters and converts basic markdown bold/italic to HTML tags."""
    if not text:
        return ""
    # Escape HTML special chars
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convert bold **text** to <b>text</b>
    escaped = re.sub(r'\*\*(.*?)\*\*|__(.*?)__', lambda m: f"<b>{m.group(1) or m.group(2)}</b>", escaped)
    # Convert italic *text* to <i>text</i>
    escaped = re.sub(r'\*(.*?)\*|_(.*?)_', lambda m: f"<i>{m.group(1) or m.group(2)}</i>", escaped)
    return escaped

async def handle_select_theme(callback: CallbackQuery) -> None:
    """Handle selecting theme after choosing PDF generation."""
    story_id = int(callback.data.replace("select_theme_", ""))
    from bot.keyboards.main import get_theme_selection_keyboard, get_story_actions_keyboard
    from bot.services.book_generator import validate_story_memories
    from db.database import get_session_factory
    
    session_factory = get_session_factory()
    is_valid, err_msg = await validate_story_memories(story_id, callback.from_user.id, session_factory)
    if not is_valid:
        await callback.message.edit_text(
            err_msg,
            reply_markup=get_story_actions_keyboard(story_id)
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🎨 <b>Выберите дизайн вашей книги:</b>\n\n"
        "• <b>Классический</b> - строгий стиль, шрифты с засечками.\n"
        "• <b>Современный</b> - яркий, с градиентами и закруглениями.\n"
        "• <b>Деловой</b> - строгий минимализм.",
        reply_markup=get_theme_selection_keyboard(story_id)
    )
    await callback.answer()

async def handle_view_chapters_list(callback: CallbackQuery) -> None:
    """Handle view chapters list button."""
    story_id = int(callback.data.replace("manage_chaps_", ""))
    from db.database import get_session_factory
    from db.models import Story
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from bot.keyboards.main import get_chapters_list_keyboard, get_story_actions_keyboard
    from bot.services.book_generator import ensure_chapters_exist
    
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        result = await session.execute(
            select(Story)
            .where(Story.id == story_id)
            .options(selectinload(Story.chapters))
        )
        story = result.scalar_one_or_none()
        
    if not story:
        await callback.answer("Книга не найдена", show_alert=True)
        return
        
    if not story.chapters:
        # We need to tell the user that we are generating chapters
        status_msg = await callback.message.answer(
            "🧠 <b>Анализирую ваши воспоминания...</b>\n\n"
            "ИИ разбивает воспоминания на логические главы. "
            "Это может занять некоторое время."
        )
        
        async def progress_cb(current, total):
            try:
                await status_msg.edit_text(
                    f"🧠 <b>Анализирую воспоминания...</b>\n\n"
                    f"Генерирую текст главы {current} из {total}..."
                )
            except Exception:
                pass
                
        try:
            await ensure_chapters_exist(story_id, callback.from_user.id, session_factory, progress_callback=progress_cb)
            await status_msg.delete()
        except ValueError as ve:
            logger.warning(f"Validation error generating chapters: {ve}")
            await status_msg.edit_text(str(ve), reply_markup=get_story_actions_keyboard(story_id))
            await callback.answer()
            return
        except Exception as e:
            logger.error(f"Error generating chapters in callback: {e}")
            await status_msg.edit_text("❌ Произошла ошибка при создании глав.", reply_markup=get_story_actions_keyboard(story_id))
            await callback.answer()
            return
            
        # Re-fetch story with chapters
        async with session_factory() as session:
            result = await session.execute(
                select(Story)
                .where(Story.id == story_id)
                .options(selectinload(Story.chapters))
            )
            story = result.scalar_one_or_none()
            
    if not story or not story.chapters:
        await callback.message.edit_text(
            "📭 В этой книге пока нет воспоминаний или не удалось сгенерировать главы.",
            reply_markup=get_story_actions_keyboard(story_id)
        )
        await callback.answer()
        return
        
    # Sort chapters chronologically
    sorted_chapters = sorted(story.chapters, key=lambda c: c.chapter_number)
    
    await callback.message.edit_text(
        f"📖 <b>Главы книги «{story.title}»:</b>\n\n"
        f"Выберите главу для просмотра и редактирования её содержимого:",
        reply_markup=get_chapters_list_keyboard(sorted_chapters, story_id)
    )
    await callback.answer()

async def handle_view_chapter_detail(callback: CallbackQuery) -> None:
    """Handle viewing a single chapter detail."""
    chapter_id = int(callback.data.replace("view_chap_", ""))
    from db.database import get_session_factory
    from db.models import Chapter
    from sqlalchemy import select
    from bot.keyboards.main import get_chapter_editor_keyboard
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        chapter = result.scalar_one_or_none()
        
    if not chapter:
        await callback.answer("Глава не найдена", show_alert=True)
        return
        
    escaped_content = md_to_telegram_html(chapter.content)
    text_to_send = (
        f"📖 <b>Глава {chapter.chapter_number}. {chapter.title}</b>\n\n"
        f"{escaped_content}"
    )
    if len(text_to_send) > 4000:
        text_to_send = text_to_send[:3950] + "\n\n<i>[Текст сокращен из-за лимитов Telegram...]</i>"
        
    await callback.message.edit_text(
        text_to_send,
        reply_markup=get_chapter_editor_keyboard(chapter.id, chapter.story_id)
    )
    await callback.answer()

async def handle_edit_chapter_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle click on Edit Chapter button - set FSM state."""
    chapter_id = int(callback.data.replace("edit_chap_", ""))
    from db.database import get_session_factory
    from db.models import Chapter
    from sqlalchemy import select
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        chapter = result.scalar_one_or_none()
        
    if not chapter:
        await callback.answer("Глава не найдена", show_alert=True)
        return
        
    await state.update_data(chapter_id=chapter_id, story_id=chapter.story_id)
    await state.set_state(StoryStates.waiting_for_chapter_edit)
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование главы {chapter.chapter_number}: «{chapter.title}»</b>\n\n"
        f"Отправьте мне новое текстовое сообщение с содержанием этой главы. "
        f"Вы можете скопировать текущий текст, отредактировать его и отправить обратно.\n\n"
        f"<i>Текущий текст главы:</i>\n\n"
        f"<code>{chapter.content[:3500]}</code>",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()

async def handle_trigger_regenerate_chapter(callback: CallbackQuery) -> None:
    """Handle regenerating a single chapter with LLM."""
    chapter_id = int(callback.data.replace("regen_chap_", ""))
    from db.database import get_session_factory
    from db.models import Chapter, Memory
    from sqlalchemy import select
    from bot.services.story_maker import generate_chapter_story
    from bot.keyboards.main import get_chapter_editor_keyboard
    
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        result = await session.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        chapter = result.scalar_one_or_none()
        
    if not chapter:
        await callback.answer("Глава не найдена", show_alert=True)
        return
        
    # Send temporary status
    status_msg = await callback.message.answer(
        "🧠 <b>ИИ переписывает главу...</b>\n\n"
        "Пожалуйста, подождите несколько секунд."
    )
    
    try:
        # Load memories
        memory_ids = [int(x) for x in chapter.memory_ids.split(",") if x.strip()] if chapter.memory_ids else []
        if not memory_ids:
            await callback.answer("Не удалось найти воспоминания для этой главы", show_alert=True)
            await status_msg.delete()
            return
            
        async with session_factory() as session:
            result = await session.execute(
                select(Memory).where(Memory.id.in_(memory_ids)).order_by(Memory.created_at.asc())
            )
            memories = result.scalars().all()
            
        if not memories:
            await callback.answer("Воспоминания для этой главы не найдены в БД", show_alert=True)
            await status_msg.delete()
            return
            
        first_mem = min(memories, key=lambda m: m.created_at)
        week_date_str = first_mem.created_at.strftime('%d.%m.%Y')
        
        from bot.services.story_maker import get_llm_client
        llm_client = get_llm_client()
        
        story_md, is_fallback = await generate_chapter_story(memories, week_date_str, client=llm_client)
        
        # Log LLM usage
        if not is_fallback:
            provider = os.getenv("LLM_PROVIDER", "gigachat").lower()
            model_name = "llama-3.3-70b-versatile" if provider == "groq" else "GigaChat"
            from bot.services.llm_logger import log_llm_usage
            await log_llm_usage(
                user_id_tg=callback.from_user.id,
                story_id=chapter.story_id,
                provider=provider,
                model_name=model_name,
                prompt_t=llm_client.last_prompt_tokens,
                completion_t=llm_client.last_completion_tokens,
                session_factory=session_factory
            )
        
        # Extract title from markdown if possible
        chapter_title = chapter.title
        title_from_md = None
        lines = story_md.strip().split('\n')
        clean_lines = []
        found_title = False
        for line in lines:
            stripped_line = line.strip()
            if not found_title and stripped_line.startswith('# '):
                title_from_md = stripped_line[2:].strip().strip('*').strip('_').strip('"').strip("'")
                found_title = True
            elif not found_title and stripped_line.lower().startswith('title:'):
                title_from_md = stripped_line[6:].strip().strip('*').strip('_').strip('"').strip("'")
                found_title = True
            elif not found_title and stripped_line.lower().startswith('название:'):
                title_from_md = stripped_line[9:].strip().strip('*').strip('_').strip('"').strip("'")
                found_title = True
            else:
                clean_lines.append(line)
                
        if found_title:
            story_md = '\n'.join(clean_lines).strip()
            chapter_title = title_from_md
            
        # Update chapter in DB
        async with session_factory() as session:
            from sqlalchemy import update
            await session.execute(
                update(Chapter)
                .where(Chapter.id == chapter_id)
                .values(title=chapter_title, content=story_md)
            )
            await session.commit()
            
        await status_msg.delete()
        await callback.answer("✨ Глава успешно перегенерирована!", show_alert=True)
        
        # Reload chapter data and redisplay detail message
        async with session_factory() as session:
            result = await session.execute(
                select(Chapter).where(Chapter.id == chapter_id)
            )
            updated_chap = result.scalar_one_or_none()
            
        if updated_chap:
            escaped_content = md_to_telegram_html(updated_chap.content)
            text_to_send = (
                f"📖 <b>Глава {updated_chap.chapter_number}. {updated_chap.title}</b>\n\n"
                f"{escaped_content}"
            )
            if len(text_to_send) > 4000:
                text_to_send = text_to_send[:3950] + "\n\n<i>[Текст сокращен из-за лимитов Telegram...]</i>"
                
            await callback.message.edit_text(
                text_to_send,
                reply_markup=get_chapter_editor_keyboard(updated_chap.id, updated_chap.story_id)
            )
            
    except Exception as e:
        logger.error(f"Error regenerating chapter: {e}")
        await callback.answer("❌ Произошла ошибка при перегенерации главы.", show_alert=True)
        try:
            await status_msg.delete()
        except Exception:
            pass

async def handle_trigger_rebuild_story(callback: CallbackQuery) -> None:
    """Handle full rebuild of chapters for a story."""
    story_id = int(callback.data.replace("rebuild_story_", ""))
    from db.database import get_session_factory
    from db.models import Story, Chapter
    from sqlalchemy import delete, select
    from sqlalchemy.orm import selectinload
    from bot.services.book_generator import ensure_chapters_exist
    from bot.keyboards.main import get_chapters_list_keyboard, get_story_actions_keyboard
    
    session_factory = get_session_factory()
    
    status_msg = await callback.message.answer(
        "🗑️ <b>Сбрасываю текущие главы...</b>\n\n"
        "ИИ заново проанализирует ваши воспоминания и перегруппирует их."
    )
    
    try:
        # Delete old chapters
        async with session_factory() as session:
            await session.execute(
                delete(Chapter).where(Chapter.story_id == story_id)
            )
            await session.commit()
            
        async def progress_cb(current, total):
            try:
                await status_msg.edit_text(
                    f"🧠 <b>Анализирую воспоминания заново...</b>\n\n"
                    f"Генерирую главу {current} из {total}..."
                )
            except Exception:
                pass
                
        # Generate new chapters
        try:
            await ensure_chapters_exist(story_id, callback.from_user.id, session_factory, progress_callback=progress_cb)
            await status_msg.delete()
            await callback.answer("✨ Книга полностью пересобрана!", show_alert=True)
        except ValueError as ve:
            logger.warning(f"Validation error rebuilding chapters: {ve}")
            await status_msg.edit_text(str(ve), reply_markup=get_story_actions_keyboard(story_id))
            await callback.answer()
            return
        except Exception as e:
            logger.error(f"Error rebuilding chapters: {e}")
            await status_msg.edit_text("❌ Произошла ошибка при пересоздании глав.", reply_markup=get_story_actions_keyboard(story_id))
            await callback.answer()
            return
        
        # Load new chapters and display list
        async with session_factory() as session:
            result = await session.execute(
                select(Story).where(Story.id == story_id).options(selectinload(Story.chapters))
            )
            story = result.scalar_one_or_none()
            
        if not story or not story.chapters:
            await callback.message.edit_text(
                "📭 Не удалось сгенерировать новые главы.",
                reply_markup=get_story_actions_keyboard(story_id)
            )
            return
            
        sorted_chapters = sorted(story.chapters, key=lambda c: c.chapter_number)
        
        await callback.message.edit_text(
            f"📖 <b>Главы книги «{story.title}»:</b>\n\n"
            f"Выберите главу для просмотра и редактирования её содержимого:",
            reply_markup=get_chapters_list_keyboard(sorted_chapters, story_id)
        )
        
    except Exception as e:
        logger.error(f"Error rebuilding story: {e}")
        await callback.answer("❌ Произошла ошибка при пересборке книги.", show_alert=True)
        try:
            await status_msg.delete()
        except Exception:
            pass

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
    dp.callback_query.register(handle_select_theme, F.data.startswith("select_theme_"))
    dp.callback_query.register(handle_view_chapters_list, F.data.startswith("manage_chaps_"))
    dp.callback_query.register(handle_view_chapter_detail, F.data.startswith("view_chap_"))
    dp.callback_query.register(handle_edit_chapter_button, F.data.startswith("edit_chap_"))
    dp.callback_query.register(handle_trigger_regenerate_chapter, F.data.startswith("regen_chap_"))
    dp.callback_query.register(handle_trigger_rebuild_story, F.data.startswith("rebuild_story_"))
    dp.callback_query.register(handle_generate_book_theme, F.data.startswith("generate_book_"))
    dp.callback_query.register(handle_skip_signature, F.data == "skip_signature")
    dp.callback_query.register(handle_buy_credits, F.data == "buy_credits")
    dp.callback_query.register(handle_callback_menu_help, F.data == "menu_help")
    dp.callback_query.register(handle_callback_confirm_yes, F.data == "confirm_yes")
    dp.callback_query.register(handle_callback_confirm_no, F.data == "confirm_no")
