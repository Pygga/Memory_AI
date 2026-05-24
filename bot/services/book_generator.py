"""Book generation service using WeasyPrint and Jinja2."""
import os
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select
from jinja2 import Template
from loguru import logger

# ✅ ПРАВИЛЬНЫЙ ИМПОРТ: всегда импортируйте нужные классы явно
from weasyprint import HTML, CSS


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


async def generate_book(user_id_tg: int, session_factory) -> str:
    """Generate a PDF book from user's memories."""
    
    logger.info(f"Starting book generation for user {user_id_tg}")
    
    # 1. Fetch data from DB
    async with session_factory() as session:
        from db.models import User, Memory
        
        result = await session.execute(
            select(User.id).where(User.telegram_id == user_id_tg)
        )
        user_record = result.scalar_one_or_none()
        
        if not user_record:
            raise ValueError("User not found in database")
        
        result = await session.execute(
            select(Memory)
            .where(Memory.user_id == user_record)
            .order_by(Memory.created_at.desc())
        )
        memories = result.scalars().all()
    
    if not memories:
        raise ValueError("No memories found for this user")
    
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
        generated_at=datetime.now(),
        total_memories=len(memories),
        first_memory_date=min(m.created_at for m in memories),
        last_memory_date=max(m.created_at for m in memories),
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
        return str(pdf_path)
        
    except Exception as e:
        logger.error(f"Critical error during PDF generation: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate PDF: {str(e)}")