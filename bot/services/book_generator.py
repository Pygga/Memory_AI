"""Book generation service using WeasyPrint and Jinja2."""
import os
import markdown
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select
from jinja2 import Template
from loguru import logger

# ✅ ПРАВИЛЬНЫЙ ИМПОРТ: всегда импортируйте нужные классы явно
from weasyprint import HTML, CSS
from bot.services.story_maker import generate_chapter_story


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


async def generate_book(user_id_tg: int, session_factory, progress_callback=None, theme: str = 'classic', story_id: int = None, signature: str = None) -> str:
    """Generate a PDF book from user's memories."""
    
    logger.info(f"Starting book generation for user {user_id_tg} with theme {theme} and story {story_id}")
    
    # 1. Fetch data from DB
    async with session_factory() as session:
        from db.models import User, Memory, Story
        
        result = await session.execute(
            select(User.id).where(User.telegram_id == user_id_tg)
        )
        user_record = result.scalar_one_or_none()
        
        if not user_record:
            raise ValueError("User not found in database")
            
        story_title = "Книга Воспоминаний"
        story_filter = True
        
        if story_id:
            result = await session.execute(
                select(Story.title).where(Story.id == story_id, Story.user_id == user_record)
            )
            story_title_db = result.scalar_one_or_none()
            if story_title_db:
                story_title = story_title_db
            story_filter = Memory.story_id == story_id
        
        result = await session.execute(
            select(Memory)
            .where(Memory.user_id == user_record)
            .where(story_filter)
            .order_by(Memory.created_at.desc())
        )
        memories = result.scalars().all()
    
    if not memories:
        raise ValueError("No memories found for this story")
    
    logger.info(f"Found {len(memories)} memories for user {user_id_tg}")
    
    # Base directory definitions
    base_dir = Path("/app")
    
# ✅ ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ: Формируем абсолютный URL с протоколом file:// для WeasyPrint
    for memory in memories:
        if memory.memory_type == "photo" and memory.file_id:
            # Путь для проверки кода Python
            full_check_path = Path("/app/static/uploads/photos") / f"{memory.file_id}.jpg"
            
            if full_check_path.exists():
                # Передаем в HTML сразу ГОТОВЫЙ абсолютный путь для WeasyPrint (3 слэша обязательны!)
                memory.local_img_url = f"file:///app/static/uploads/photos/{memory.file_id}.jpg"
                logger.info(f"🟢 Фото найдено и передано в HTML: {memory.local_img_url}")
            else:
                memory.local_img_url = None
                logger.warning(f"🔴 ФОТО НЕ НАЙДЕНО на диске: {full_check_path}")
        else:
            memory.local_img_url = None

    
    # 2. Group memories
    weeks = group_memories_by_week(memories)
    
    # 2.5 Generate stories for each week
    total_weeks = len(weeks)
    has_fallback = False
    for i, (week_key, week_data) in enumerate(weeks.items(), 1):
        if progress_callback:
            await progress_callback(i, total_weeks)
            
        week_date_str = week_data['start_date'].strftime('%d.%m.%Y')
        story_md, is_fallback = await generate_chapter_story(week_data['memories'], week_date_str)
        if is_fallback:
            has_fallback = True
            
        # Extract title from markdown if possible
        title = f"Неделя от {week_date_str}"
        if not is_fallback:
            lines = story_md.strip().split('\n')
            clean_lines = []
            found_title = False
            for line in lines:
                stripped_line = line.strip()
                if not found_title and stripped_line.startswith('# '):
                    title = stripped_line[2:].strip().strip('*').strip('_').strip('"').strip("'")
                    found_title = True
                elif not found_title and stripped_line.lower().startswith('title:'):
                    title = stripped_line[6:].strip().strip('*').strip('_').strip('"').strip("'")
                    found_title = True
                elif not found_title and stripped_line.lower().startswith('название:'):
                    title = stripped_line[9:].strip().strip('*').strip('_').strip('"').strip("'")
                    found_title = True
                else:
                    clean_lines.append(line)
            if found_title:
                story_md = '\n'.join(clean_lines).strip()
        
        week_data['title'] = title
            
        # Convert markdown story to HTML
        story_html = markdown.markdown(story_md)
        
        # Replace [PHOTO:id] with actual HTML
        for memory in week_data['memories']:
            if memory.memory_type == 'photo' and memory.local_img_url:
                photo_tag = f"[PHOTO:{memory.id}]"
                caption_html = f'<div class="photo-caption">{memory.content}</div>' if memory.content and memory.content.strip() else ''
                date_str = memory.created_at.strftime('%d.%m.%Y')
                photo_html = (
                    f'<div class="memory-photo-fullpage" style="text-align:center; margin: 30px 0; page-break-inside: avoid;">'
                    f'<img src="{memory.local_img_url}" alt="Фотография" style="max-width:100%; max-height:400px; border-radius:var(--photo-border-radius);">'
                    f'{caption_html}'
                    f'<div class="photo-date" style="font-size: 9pt; color: #999; margin-top: 5px;">{date_str}</div>'
                    f'</div>'
                )
                if photo_tag in story_html:
                    story_html = story_html.replace(photo_tag, photo_html)
                else:
                    # Append at the end if LLM missed it
                    story_html += photo_html
                    
        week_data['story_html'] = story_html
    
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
        weeks=weeks,
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
            # base_url="file:///app/"
        )
            
        logger.info(f"Book successfully generated at {pdf_path}")
        return str(pdf_path), has_fallback
        
    except Exception as e:
        logger.error(f"Critical error during PDF generation: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate PDF: {str(e)}")