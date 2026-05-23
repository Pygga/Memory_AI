"""Book generation service using WeasyPrint and Jinja2."""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Template
from weasyprint import HTML, CSS
from loguru import logger

from db.models import Memory


def group_memories_by_week(memories: list[Memory]) -> dict:
    """Group memories by week for chapter organization."""
    weeks = {}
    
    for memory in memories:
        # Get the week start date (Monday)
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
    
    # Fetch all memories for the user
    async with session_factory() as session:
        # First get internal user.id by telegram_id
        from db.models import User
        from sqlalchemy import select
        
        result = await session.execute(
            select(User.id).where(User.telegram_id == user_id_tg)
        )
        user_record = result.scalar_one_or_none()
        
        if not user_record:
            raise ValueError("User not found")
        
        # Now fetch memories by internal user.id
        result = await session.execute(
            select(Memory)
            .where(Memory.user_id == user_record)
            .order_by(Memory.created_at.desc())
        )
        memories = result.scalars().all()
    
    if not memories:
        raise ValueError("No memories found for this user")
    
    # Group memories by week
    weeks = group_memories_by_week(memories)
    
    # Load template
    template_path = Path("templates/book.html")
    css_path = Path("static/css/book.css")
    
    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())
    
    # Render HTML
    html_content = template.render(
        weeks=weeks,
        generated_at=datetime.now(),
        total_memories=len(memories),
        first_memory_date=min(m.created_at for m in memories),
        last_memory_date=max(m.created_at for m in memories),
    )
    
    # Create output directory
    output_dir = Path("static/books")
    output_dir.mkdir(exist_ok=True)
    
    # Generate PDF
    pdf_path = output_dir / f"memory_book_{user_id_tg}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Convert to PDF with WeasyPrint
    html = HTML(string=html_content, base_url=str(Path.cwd()))
    
    # Load CSS if exists
    if css_path.exists():
        css = CSS(str(css_path))
        html.write_pdf(str(pdf_path), stylesheets=[css])
    else:
        html.write_pdf(str(pdf_path))
    
    logger.info(f"Generated book at {pdf_path}")
    return str(pdf_path)
