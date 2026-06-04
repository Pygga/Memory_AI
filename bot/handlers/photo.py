"""Photo message handlers."""
from pathlib import Path
from aiogram import Dispatcher, F
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.repositories import UserRepository, StoryRepository, MemoryRepository
from utils.helpers import extract_tags


async def handle_photo_message(message: Message) -> None:
    """Handle photo messages."""
    user_id_tg = message.from_user.id
    
    # Get the best quality photo
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    
    # Create directory for photos
    photo_dir = Path("static/uploads/photos")
    photo_dir.mkdir(parents=True, exist_ok=True)
    file_path = photo_dir / f"{file.file_id}.jpg"
    
    # Download the file
    await message.bot.download_file(file.file_path, str(file_path))
    
    # Get caption and extract tags
    caption = message.caption or ""
    tags = extract_tags(caption)
    
    # Save to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_or_create(
            telegram_id=user_id_tg,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Get active story
        story_repo = StoryRepository(session)
        active_story = await story_repo.get_active_by_user_id(user.id)
        
        # Create memory with INTERNAL user.id and story_id via repository
        memory_repo = MemoryRepository(session)
        await memory_repo.create(
            user_id=user.id,
            story_id=active_story.id if active_story else None,
            content=caption,
            memory_type="photo",
            tags=tags,
            file_id=file.file_id
        )
        await session.commit()
        
    # Send confirmation
    story_context = f" в историю «{active_story.title}»" if active_story else ""
    response = f"✅ <b>Фотография сохранена{story_context}!</b>"
    if tags:
        response += f"\n🏷️ Теги: {', '.join(f'#{tag}' for tag in tags)}"
    
    await message.answer(response)
    logger.info(f"Saved photo memory from user {user_id_tg}")


def register_photo_handlers(dp: Dispatcher) -> None:
    """Register photo message handlers."""
    dp.message.register(handle_photo_message, F.photo)