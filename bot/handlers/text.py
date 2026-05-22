"""Text message handlers."""
import re
from aiogram import Dispatcher, F
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.models import Memory


def extract_tags(text: str) -> list[str]:
    """Extract hashtags from text."""
    tags = re.findall(r'#(\w+)', text.lower())
    return tags


async def handle_text_message(message: Message) -> None:
    """Handle regular text messages."""
    if not message.text:
        return
    
    # Skip commands
    if message.text.startswith('/'):
        return
    
    text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Extract tags
    tags = extract_tags(text)
    
    # Save to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        memory = Memory(
            user_id=user_id,
            content=text,
            memory_type="text",
            tags=tags,
            file_id=None
        )
        session.add(memory)
        await session.commit()
    
    response = f"✅ <b>Воспоминание сохранено!</b>\n\n"
    if tags:
        response += f"🏷️ Теги: {', '.join(f'#{tag}' for tag in tags)}\n"
    response += f"\nОтправьте /list чтобы просмотреть все воспоминания."
    
    await message.answer(response)
    logger.info(f"Saved text memory from user {user_id} with tags: {tags}")


def register_text_handlers(dp: Dispatcher) -> None:
    """Register text message handlers."""
    dp.message.register(handle_text_message, F.text & ~F.text.startswith('/'))
