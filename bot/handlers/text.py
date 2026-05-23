"""Text message handlers."""
from aiogram import Dispatcher, F
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.models import Memory
from db.users import get_or_create_user
from utils.helpers import extract_tags


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
            user_id=user.id,  # ← ВАЖНО: внутренний ID из БД
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
    dp.message.register(handle_text_message, F.text & ~F.text.startswith('/'))