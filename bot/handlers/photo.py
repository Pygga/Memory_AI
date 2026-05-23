"""Photo message handlers."""
import os
from aiogram import Dispatcher, F
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.models import Memory
from db.users import get_or_create_user
from utils.helpers import extract_tags


async def handle_photo_message(message: Message) -> None:
    """Handle photo messages."""
    user_id_tg = message.from_user.id
    
    # Get the best quality photo
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    
    # Create directory for photos
    photo_dir = "static/uploads/photos"
    os.makedirs(photo_dir, exist_ok=True)
    file_path = os.path.join(photo_dir, f"{file.file_id}.jpg")
    
    # Download the file
    await message.bot.download_file(file.file_path, file_path)
    
    # Get caption and extract tags
    caption = message.caption or ""
    tags = extract_tags(caption)
    
    # Save to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Get or create user
        user = await get_or_create_user(
            session,
            telegram_id=user_id_tg,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Create memory with INTERNAL user.id
        memory = Memory(
            user_id=user.id,  # ← ВАЖНО: внутренний ID из БД
            content=caption,
            memory_type="photo",
            tags=tags,
            file_id=file.file_id
        )
        session.add(memory)
        await session.commit()
    
    # Send confirmation
    response = f"✅ <b>Фотография сохранена!</b>"
    if caption:
        response += f"\n📝 Описание: {caption}"
    if tags:
        response += f"\n🏷️ Теги: {', '.join(f'#{tag}' for tag in tags)}"
    response += "\n\nФото будет включено в вашу книгу воспоминаний!"
    
    await message.answer(response)
    logger.info(f"Saved photo memory from user {user_id_tg}")


def register_photo_handlers(dp: Dispatcher) -> None:
    """Register photo message handlers."""
    dp.message.register(handle_photo_message, F.photo)