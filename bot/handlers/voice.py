"""Voice message handlers with faster-whisper transcription."""
from pathlib import Path
import asyncio
from aiogram import Dispatcher, F
from aiogram.types import Message
from loguru import logger

from db.database import get_session_factory
from db.repositories import UserRepository, StoryRepository, MemoryRepository
from utils.helpers import extract_tags
from faster_whisper import WhisperModel
from bot.config import settings

# Global whisper model — loaded once at startup
_whisper_model = None


async def load_whisper_model():
    """Lazy-load Whisper model in executor to avoid blocking."""
    global _whisper_model
    if _whisper_model is None:
        loop = asyncio.get_event_loop()
        _whisper_model = await loop.run_in_executor(
            None,
            lambda: WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        )
    return _whisper_model


async def transcribe_voice(file_path: str) -> str:
    """Transcribe voice message using faster-whisper."""
    try:
        model = await load_whisper_model()
        loop = asyncio.get_event_loop()
        
        segments, _ = await loop.run_in_executor(
            None,
            lambda: model.transcribe(file_path, beam_size=5, language="ru")
        )
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return "Ошибка транскрипции"


async def handle_voice_message(message: Message) -> None:
    """Handle voice messages."""
    user_id_tg = message.from_user.id
    
    # Get voice file info
    voice = message.voice
    file = await message.bot.get_file(voice.file_id)
    
    # Create temp dir and path
    temp_dir = Path("static/uploads/voice")
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = temp_dir / f"{file.file_id}.ogg"
    
    # Download .ogg file from Telegram
    await message.bot.download_file(file.file_path, destination=str(file_path))
    
    # Notify user
    await message.answer("🎤 Транскрибирую голосовое сообщение...")
    
    # Transcribe
    transcribed_text = await transcribe_voice(str(file_path))
    
    # Extract hashtags from transcribed text
    tags = extract_tags(transcribed_text)
    
    # Save to DB
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
        
        # Create memory with INTERNAL user.id via repository
        memory_repo = MemoryRepository(session)
        await memory_repo.create(
            user_id=user.id,
            story_id=active_story.id if active_story else None,
            content=transcribed_text,
            memory_type="voice",
            tags=tags,
            file_id=file.file_id
        )
        await session.commit()
    
    # Cleanup temp file
    try:
        file_path.unlink(missing_ok=True)
    except OSError as e:
        logger.warning(f"Failed to delete temp file {file_path}: {e}")
    
    # Send confirmation
    story_context = f" в историю «{active_story.title}»" if active_story else ""
    response = f"✅ <b>Голосовая заметка сохранена{story_context}!</b>\n\n📝 {transcribed_text}"
    if tags:
        response += f"\n🏷️ Теги: {', '.join(f'#{tag}' for tag in tags)}"
    
    await message.answer(response)
    logger.info(f"Saved voice memory from user {user_id_tg}")


def register_voice_handlers(dp: Dispatcher) -> None:
    """Register voice message handlers."""
    dp.message.register(handle_voice_message, F.voice)