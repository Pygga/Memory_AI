"""Chapter management callback handlers: view, edit, regenerate, rebuild."""
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from bot.config import settings
from bot.keyboards.main import (
    get_back_keyboard,
    get_story_actions_keyboard,
    get_chapters_list_keyboard,
    get_chapter_editor_keyboard,
)
from bot.states import StoryStates
from utils.text import md_to_telegram_html, extract_title_from_markdown


async def handle_view_chapters_list(callback: CallbackQuery) -> None:
    """Handle view chapters list button."""
    story_id = int(callback.data.replace("manage_chaps_", ""))
    from db.database import get_session_factory
    from db.repositories import StoryRepository
    from bot.services.book_generator import ensure_chapters_exist
    
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        story_repo = StoryRepository(session)
        story = await story_repo.get_by_id(story_id, load_chapters=True)
        
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
            story_repo = StoryRepository(session)
            story = await story_repo.get_by_id(story_id, load_chapters=True)
            
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
    from db.repositories import ChapterRepository
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        chapter_repo = ChapterRepository(session)
        chapter = await chapter_repo.get_by_id(chapter_id)
        
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
    from db.repositories import ChapterRepository
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        chapter_repo = ChapterRepository(session)
        chapter = await chapter_repo.get_by_id(chapter_id)
        
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
    from db.repositories import ChapterRepository, MemoryRepository
    from bot.services.story_maker import generate_chapter_story, get_llm_client
    
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        chapter_repo = ChapterRepository(session)
        chapter = await chapter_repo.get_by_id(chapter_id)
        
    if not chapter:
        await callback.answer("Глава не найдена", show_alert=True)
        return
        
    # Send temporary status
    status_msg = await callback.message.answer(
        "🧠 <b>ИИ переписывает главу...</b>\n\n"
        "Пожалуйста, подождите несколько секунд."
    )
    
    try:
        # Load memories via repository
        memory_ids = [int(x) for x in chapter.memory_ids.split(",") if x.strip()] if chapter.memory_ids else []
        if not memory_ids:
            await callback.answer("Не удалось найти воспоминания для этой главы", show_alert=True)
            await status_msg.delete()
            return
            
        async with session_factory() as session:
            memory_repo = MemoryRepository(session)
            memories = await memory_repo.get_by_ids(memory_ids)
            
        if not memories:
            await callback.answer("Воспоминания для этой главы не найдены в БД", show_alert=True)
            await status_msg.delete()
            return
            
        first_mem = min(memories, key=lambda m: m.created_at)
        week_date_str = first_mem.created_at.strftime('%d.%m.%Y')
        
        llm_client = get_llm_client()
        
        story_md, is_fallback = await generate_chapter_story(memories, week_date_str, client=llm_client, bypass_cache=True)
        
        # Log LLM usage
        if not is_fallback:
            provider = settings.llm_provider.lower()
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
        
        # Extract title from markdown using shared utility
        title_from_md, cleaned_md = extract_title_from_markdown(story_md)
        chapter_title = title_from_md if title_from_md else chapter.title
        story_md = cleaned_md
            
        # Update chapter in DB via repository
        async with session_factory() as session:
            chapter_repo = ChapterRepository(session)
            await chapter_repo.update_title_and_content(chapter_id, chapter_title, story_md)
            await session.commit()
            
        await status_msg.delete()
        await callback.answer("✨ Глава успешно перегенерирована!", show_alert=True)
        
        # Reload chapter data and redisplay detail message
        async with session_factory() as session:
            chapter_repo = ChapterRepository(session)
            updated_chap = await chapter_repo.get_by_id(chapter_id)
            
        if updated_chap:
            escaped_content = md_to_telegram_html(updated_chap.content)
            text_to_send = (
                f"📖 <b>Глава {updated_chap.chapter_number}. {updated_chap.title}</b>\n\n"
                f"{escaped_content}"
            )
            if len(text_to_send) > 4000:
                text_to_send = text_to_send[:3950] + "\n\n<i>[Текст сокращен из-за лимитов Telegram...]</i>"
                
            try:
                await callback.message.edit_text(
                    text_to_send,
                    reply_markup=get_chapter_editor_keyboard(updated_chap.id, updated_chap.story_id)
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
                logger.info("Regenerated chapter text matches current message content; skipped editing.")
            
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
    from db.repositories import StoryRepository, ChapterRepository
    from bot.services.book_generator import ensure_chapters_exist
    
    session_factory = get_session_factory()
    
    status_msg = await callback.message.answer(
        "🗑️ <b>Сбрасываю текущие главы...</b>\n\n"
        "ИИ заново проанализирует ваши воспоминания и перегруппирует их."
    )
    
    try:
        # Delete old chapters via repository
        async with session_factory() as session:
            chapter_repo = ChapterRepository(session)
            await chapter_repo.delete_all_for_story(story_id)
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
            story_repo = StoryRepository(session)
            story = await story_repo.get_by_id(story_id, load_chapters=True)
            
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


def register_chapters_handlers(dp: Dispatcher) -> None:
    """Register chapter-related callback handlers."""
    dp.callback_query.register(handle_view_chapters_list, F.data.startswith("manage_chaps_"))
    dp.callback_query.register(handle_view_chapter_detail, F.data.startswith("view_chap_"))
    dp.callback_query.register(handle_edit_chapter_button, F.data.startswith("edit_chap_"))
    dp.callback_query.register(handle_trigger_regenerate_chapter, F.data.startswith("regen_chap_"))
    dp.callback_query.register(handle_trigger_rebuild_story, F.data.startswith("rebuild_story_"))
