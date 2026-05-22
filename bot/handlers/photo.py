"""Photo message handlers."""
import os
from aiogram import Dispatcher, F
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.models import Memory


async def handle_photo_message(message: Message) -> None:
    """Handle photo messages."""
    user_id = message.from_user.id
    
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
    import re
    tags = re.findall(r'#(\w+)', caption.lower())
    
    # Save to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        memory = Memory(
            user_id=user_id,
            content=caption,
            memory_type="photo",
            tags=tags,
            file_id=file.file_id
        )
        session.add(memory)
        await session.commit()
    
    response = f"✅ <b>Фотография сохранена!</b>\n\n"
    if caption:
        response += f"📝 Описание: {caption}\n"
    if tags:
        response += f"🏷️ Теги: {', '.join(f'#{tag}' for tag in tags)}\n"
    response += "\nФото будет включено в вашу книгу воспоминаний!"
    
    await message.answer(response)
    logger.info(f"Saved photo memory from user {user_id}")


def register_photo_handlers(dp: Dispatcher) -> None:
    """Register photo message handlers."""
    dp.message.register(handle_photo_message, F.photo)
