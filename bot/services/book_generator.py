"""Book generation service using WeasyPrint and Jinja2."""
import markdown
from datetime import datetime, timedelta
from pathlib import Path
from jinja2 import Template
from loguru import logger
from weasyprint import HTML, CSS

from bot.config import settings
from bot.services.story_maker import generate_chapter_story, get_llm_client
from db.repositories import UserRepository, StoryRepository, MemoryRepository, ChapterRepository
from utils.text import extract_title_from_markdown


def group_memories_by_week(memories: list) -> dict:
    """Group memories by week for chapter organization."""
    weeks = {}
    
    for memory in memories:
        week_start = memory.created_at - timedelta(days=memory.created_at.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        
        if week_key not in weeks:
            weeks[week_key] = {
                'start_date': week_start,
                'end_date': week_start + timedelta(days=6),
                'memories': []
            }
        
        weeks[week_key]['memories'].append(memory)
    
    return dict(sorted(weeks.items(), reverse=True))


async def validate_story_memories(story_id: int, user_id_tg: int, session_factory, memories: list = None) -> tuple[bool, str]:
    """Validate if the user has enough memories in the story to generate a book."""
    if memories is None:
        async with session_factory() as session:
            user_repo = UserRepository(session)
            user_record = await user_repo.get_by_telegram_id(user_id_tg)
            if not user_record:
                return False, "Пользователь не найден в базе данных."
                
            memory_repo = MemoryRepository(session)
            memories = await memory_repo.get_by_user_and_story(user_record.id, story_id)
        
    if not memories:
        return False, (
            "📭 <b>В этой книге пока нет воспоминаний!</b>\n\n"
            "Пожалуйста, сначала отправьте боту несколько воспоминаний (текст, фото или голос), "
            "чтобы мы могли сгенерировать для вас книгу."
        )
        
    # Count words and details
    words = []
    for m in memories:
        if m.content:
            words.extend([w for w in m.content.split() if w.strip()])
    words_count = len(words)
    
    # If there is only one memory, check if it's a photo or a very short text/word
    if len(memories) == 1:
        m = memories[0]
        if m.memory_type == 'photo':
            return False, (
                "⚠️ <b>Слишком мало контента для генерации!</b>\n\n"
                "У вас добавлена всего одна фотография без описания. Пожалуйста, добавьте текстовые "
                "воспоминания, голосовые заметки или подробные описания к фото, чтобы мы могли составить рассказ."
            )
        elif words_count <= 2:
            return False, (
                "⚠️ <b>Слишком мало контента для генерации!</b>\n\n"
                "Ваше единственное воспоминание слишком короткое (всего пара слов). "
                "Пожалуйста, напишите более подробные истории или отправьте голосовое сообщение, "
                "чтобы ИИ смог составить полноценный рассказ."
            )
            
    # Check if the total word count across all memories is very small
    if words_count < 5:
        num_photos = sum(1 for m in memories if m.memory_type == 'photo')
        if num_photos <= 1:
            return False, (
                "⚠️ <b>Слишком мало контента для генерации!</b>\n\n"
                "Общий объем ваших воспоминаний слишком мал (всего несколько слов). "
                "Пожалуйста, добавьте больше подробностей, рассказов или фотографий с текстовым контекстом."
            )

    return True, ""


async def ensure_chapters_exist(story_id: int, user_id_tg: int, session_factory, memories: list = None, progress_callback=None) -> bool:
    """Ensure chapters are generated and saved to DB for the given story."""
    from bot.services.semantic_grouper import group_memories_semantically

    async with session_factory() as session:
        story_repo = StoryRepository(session)
        story_obj = await story_repo.get_by_id(story_id, load_chapters=True)
        
    if not story_obj:
        return False
        
    if story_obj.chapters:
        return False # Already exists
        
    # If memories are not passed, fetch them
    if not memories:
        async with session_factory() as session:
            user_repo = UserRepository(session)
            user_record = await user_repo.get_by_telegram_id(user_id_tg)
            if not user_record:
                return False
                
            memory_repo = MemoryRepository(session)
            memories = await memory_repo.get_by_user_and_story(user_record.id, story_id)
            
    # Validate the memories list
    is_valid, err_msg = await validate_story_memories(story_id, user_id_tg, session_factory, memories=memories)
    if not is_valid:
        raise ValueError(err_msg)
        
    llm_client = get_llm_client()
    
    semantic_groups = await group_memories_semantically(memories, client=llm_client)
    has_fallback = False
    
    # Log grouping LLM usage
    if semantic_groups:
        provider = settings.llm_provider.lower()
        model_name = "llama-3.3-70b-versatile" if provider == "groq" else "GigaChat"
        from bot.services.llm_logger import log_llm_usage
        await log_llm_usage(
            user_id_tg=user_id_tg,
            story_id=story_id,
            provider=provider,
            model_name=model_name,
            prompt_t=llm_client.last_prompt_tokens,
            completion_t=llm_client.last_completion_tokens,
            session_factory=session_factory
        )
    
    if not semantic_groups:
        # Fallback to week-based grouping
        weeks = group_memories_by_week(memories)
        semantic_groups = []
        for i, (week_key, week_data) in enumerate(weeks.items(), 1):
            week_date_str = week_data['start_date'].strftime('%d.%m.%Y')
            title = f"Неделя от {week_date_str}"
            m_ids = [m.id for m in week_data['memories']]
            semantic_groups.append({"title": title, "memory_ids": m_ids})
            
    # Generate stories for each group and save to DB
    async with session_factory() as session:
        chapter_repo = ChapterRepository(session)
        total_chapters = len(semantic_groups)
        for i, group in enumerate(semantic_groups, 1):
            if progress_callback:
                await progress_callback(i, total_chapters)
                
            chapter_title = group["title"]
            memory_ids = group["memory_ids"]
            
            # Filter memories in this group
            memories_in_chapter = [m for m in memories if m.id in memory_ids]
            if not memories_in_chapter:
                continue
                
            first_mem = min(memories_in_chapter, key=lambda m: m.created_at)
            week_date_str = first_mem.created_at.strftime('%d.%m.%Y')
            
            story_md, is_fallback = await generate_chapter_story(memories_in_chapter, week_date_str, client=llm_client)
            if is_fallback:
                has_fallback = True
            else:
                # Log chapter generation LLM usage
                provider = settings.llm_provider.lower()
                model_name = "llama-3.3-70b-versatile" if provider == "groq" else "GigaChat"
                from bot.services.llm_logger import log_llm_usage
                await log_llm_usage(
                    user_id_tg=user_id_tg,
                    story_id=story_id,
                    provider=provider,
                    model_name=model_name,
                    prompt_t=llm_client.last_prompt_tokens,
                    completion_t=llm_client.last_completion_tokens,
                    session_factory=session_factory
                )
                
            # Extract title from markdown using shared utility
            title_from_md, cleaned_md = extract_title_from_markdown(story_md)
            if title_from_md:
                story_md = cleaned_md
                chapter_title = title_from_md
                
            # Save Chapter to DB via repository
            await chapter_repo.create(
                story_id=story_id,
                title=chapter_title,
                content=story_md,
                chapter_number=i,
                memory_ids=",".join(map(str, memory_ids))
            )
            
        await session.commit()
        
    return has_fallback


async def generate_book(user_id_tg: int, session_factory, progress_callback=None, theme: str = 'classic', story_id: int = None, signature: str = None) -> tuple[str, bool]:
    """Generate a PDF book from user's memories."""
    logger.info(f"Starting book generation for user {user_id_tg} with theme {theme} and story {story_id}")
    
    # 1. Fetch data from DB
    async with session_factory() as session:
        user_repo = UserRepository(session)
        user_record = await user_repo.get_by_telegram_id(user_id_tg)
        if not user_record:
            raise ValueError("User not found in database")
            
        story_title = "Книга Воспоминаний"
        story_obj = None
        
        story_repo = StoryRepository(session)
        if story_id:
            story_obj = await story_repo.get_by_id(story_id, load_chapters=True)
            if story_obj:
                story_title = story_obj.title
        
        memory_repo = MemoryRepository(session)
        memories = await memory_repo.get_by_user_and_story(user_record.id, story_id)
    
    if not memories:
        raise ValueError("No memories found for this story")
    
    logger.info(f"Found {len(memories)} memories for user {user_id_tg}")
    
    # Base directory definitions
    base_dir = Path("/app")
    
    # Form absolute URL with file:// protocol for WeasyPrint
    for memory in memories:
        if memory.memory_type == "photo" and memory.file_id:
            full_check_path = Path("/app/static/uploads/photos") / f"{memory.file_id}.jpg"
            if full_check_path.exists():
                memory.local_img_url = f"file:///app/static/uploads/photos/{memory.file_id}.jpg"
                logger.info(f"🟢 Фото найдено и передано в HTML: {memory.local_img_url}")
            else:
                memory.local_img_url = None
                logger.warning(f"🔴 ФОТО НЕ НАЙДЕНО на диске: {full_check_path}")
        else:
            memory.local_img_url = None

    # 2. Get or generate chapters semantically
    has_fallback = False
    db_chapters = []
    
    if story_id and story_obj:
        has_fallback = await ensure_chapters_exist(story_id, user_id_tg, session_factory, memories, progress_callback)
        # Reload chapters from DB
        async with session_factory() as session:
            story_repo = StoryRepository(session)
            story_obj = await story_repo.get_by_id(story_id, load_chapters=True)
            db_chapters = story_obj.chapters if story_obj else []
            
    if not db_chapters:
        # Fallback for when there's no story_id/story_obj (e.g. tests)
        weeks = group_memories_by_week(memories)
        total_chapters = len(weeks)
        for i, (week_key, week_data) in enumerate(weeks.items(), 1):
            if progress_callback:
                await progress_callback(i, total_chapters)
            week_date_str = week_data['start_date'].strftime('%d.%m.%Y')
            story_md, is_fallback = await generate_chapter_story(week_data['memories'], week_date_str)
            if is_fallback:
                has_fallback = True
            
            # Simple Chapter instance for rendering
            from db.models import Chapter
            db_chapters.append(Chapter(
                title=f"Неделя от {week_date_str}",
                content=story_md,
                chapter_number=i
            ))
            
    # Sort chapters by chapter number
    db_chapters = sorted(db_chapters, key=lambda c: c.chapter_number)
    
    # 2.5 Format chapters for template render
    chapters_for_render = []
    for chapter in db_chapters:
        story_html = markdown.markdown(chapter.content)
        
        # Replace [PHOTO:id] with actual HTML
        for memory in memories:
            if memory.memory_type == 'photo' and memory.local_img_url:
                photo_tag = f"[PHOTO:{memory.id}]"
                caption_html = f'<div class="photo-caption">{memory.content}</div>' if memory.content and memory.content.strip() else ''
                date_str = memory.created_at.strftime('%d.%m.%Y')
                photo_html = (
                    f'<div class="memory-photo-fullpage" style="text-align:center; margin: 30px 0; page-break-inside: avoid;">'
                    f'<img src="{memory.local_img_url}" alt="Фотография" style="max-width:100%; max-height:400px;">'
                    f'{caption_html}'
                    f'<div class="photo-date" style="font-size: 9pt; color: #999; margin-top: 5px;">{date_str}</div>'
                    f'</div>'
                )
                # Markdown wraps standalone markers in paragraphs. Replace the whole paragraph first to keep HTML valid.
                p_photo_tag = f"<p>{photo_tag}</p>"
                if p_photo_tag in story_html:
                    story_html = story_html.replace(p_photo_tag, photo_html)
                elif photo_tag in story_html:
                    story_html = story_html.replace(photo_tag, photo_html)
                    
        chapters_for_render.append({
            'title': chapter.title,
            'story_html': story_html
        })
    
    # 3. Prepare paths
    template_path = base_dir / "templates" / "book.html"
    css_path = base_dir / "static" / "css" / "book.css"
    output_dir = base_dir / "static" / "books"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at {template_path}")
    
    output_dir.mkdir(exist_ok=True)
    
    # 4. Render HTML
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    template = Template(template_content)
    
    html_content = template.render(
        chapters=chapters_for_render,
        theme=theme,
        story_title=story_title,
        generated_at=datetime.now(),
        total_memories=len(memories),
        first_memory_date=min(m.created_at for m in memories),
        last_memory_date=max(m.created_at for m in memories),
        signature=signature,
    )
    
    logger.debug("HTML template rendered successfully")
    
    # 5. Generate PDF
    pdf_filename = f"memory_book_{user_id_tg}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = output_dir / pdf_filename
    
    try:
        logger.info("Converting HTML to PDF...")
        
        html_doc = HTML(string=html_content)
        
        stylesheets = []
        if css_path.exists():
            stylesheets.append(CSS(filename=str(css_path)))
        
        html_doc.write_pdf(
            target=str(pdf_path),
            stylesheets=stylesheets if stylesheets else None,
        )
            
        logger.info(f"Book successfully generated at {pdf_path}")
        return str(pdf_path), has_fallback
        
    except Exception as e:
        logger.error(f"Critical error during PDF generation: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate PDF: {str(e)}")