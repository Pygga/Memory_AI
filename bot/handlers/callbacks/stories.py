"""Story management callback handlers: story list, selection, cabinet."""
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from loguru import logger

from bot.keyboards.main import get_back_keyboard, get_story_actions_keyboard


async def handle_callback_menu_book(callback: CallbackQuery) -> None:
    """Handle menu book callback - show stories list first."""
    from db.database import get_session_factory
    from db.repositories import UserRepository, StoryRepository
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        user_repo = UserRepository(session)
        user_record = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user_record:
            await callback.message.edit_text("Пожалуйста, сначала запустите бота командой /start")
            await callback.answer()
            return
            
        story_repo = StoryRepository(session)
        stories = await story_repo.get_all_by_user_id(user_record.id)
        
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
    from db.repositories import StoryRepository
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        story_repo = StoryRepository(session)
        story = await story_repo.get_by_id(story_id, load_chapters=True)
        
    if not story:
        await callback.answer("Книга не найдена", show_alert=True)
        return
        
    num_chapters = len(story.chapters)
    chapters_status = f"сформировано {num_chapters} глав" if num_chapters > 0 else "главы ещё не созданы (будут сформированы автоматически при переходе к редактированию)"
    active_status = "🟢 Текущая (активная) книга" if story.is_active else "⚪ В архиве"
    
    await callback.message.edit_text(
        f"📖 <b>Кабинет книги: «{story.title}»</b>\n\n"
        f"📌 <b>Статус книги:</b> {active_status}\n"
        f"📌 <b>Статус глав:</b> {chapters_status}\n\n"
        f"Здесь вы можете подготовить и настроить вашу будущую книгу перед печатью в PDF:\n\n"
        f"• <b>Шаг 1: Настройка глав</b> — Нажмите <i>«📖 Читать / Редактировать главы»</i>, чтобы увидеть семантические ИИ-главы. Вы сможете прочитать их, изменить текст вручную или перегенерировать через ИИ.\n"
        f"• <b>Шаг 2: Генерация PDF</b> — Когда всё будет готово, нажмите <i>«🖨️ Сгенерировать PDF-книгу»</i>, чтобы выбрать дизайн, добавить финальную подпись и скачать PDF!",
        reply_markup=get_story_actions_keyboard(story_id, is_active=bool(story.is_active))
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected story {story_id} in Cabinet")


async def handle_set_active_story(callback: CallbackQuery) -> None:
    """Handle setting a story as active/current."""
    story_id = int(callback.data.replace("set_active_", ""))
    from db.database import get_session_factory
    from db.repositories import UserRepository, StoryRepository
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        user_repo = UserRepository(session)
        user_record = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user_record:
            await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
            return
            
        story_repo = StoryRepository(session)
        story = await story_repo.get_by_id(story_id, load_chapters=True)
        if not story:
            await callback.answer("Книга не найдена", show_alert=True)
            return
            
        # Deactivate all other stories
        await story_repo.deactivate_all_for_user(user_record.id)
        # Activate this story
        story.is_active = 1
        await session.commit()
        
    await callback.answer(f"✅ Книга «{story.title}» теперь активна!")
    
    # Reload and refresh the Cabinet view
    num_chapters = len(story.chapters)
    chapters_status = f"сформировано {num_chapters} глав" if num_chapters > 0 else "главы ещё не созданы (будут сформированы автоматически при переходе к редактированию)"
    active_status = "🟢 Текущая (активная) книга"
    
    await callback.message.edit_text(
        f"📖 <b>Кабинет книги: «{story.title}»</b>\n\n"
        f"📌 <b>Статус книги:</b> {active_status}\n"
        f"📌 <b>Статус глав:</b> {chapters_status}\n\n"
        f"Здесь вы можете подготовить и настроить вашу будущую книгу перед печатью в PDF:\n\n"
        f"• <b>Шаг 1: Настройка глав</b> — Нажмите <i>«📖 Читать / Редактировать главы»</i>, чтобы увидеть семантические ИИ-главы. Вы сможете прочитать их, изменить текст вручную или перегенерировать через ИИ.\n"
        f"• <b>Шаг 2: Генерация PDF</b> — Когда всё будет готово, нажмите <i>«🖨️ Сгенерировать PDF-книгу»</i>, чтобы выбрать дизайн, добавить финальную подпись и скачать PDF!",
        reply_markup=get_story_actions_keyboard(story_id, is_active=True)
    )
    logger.info(f"User {callback.from_user.id} set story {story_id} as active")


def register_stories_handlers(dp: Dispatcher) -> None:
    """Register story-related callback handlers."""
    dp.callback_query.register(handle_callback_menu_book, F.data == "menu_book")
    dp.callback_query.register(handle_select_story, F.data.startswith("select_story_"))
    dp.callback_query.register(handle_set_active_story, F.data.startswith("set_active_"))

