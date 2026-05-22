"""Voice message handlers with Whisper.cpp transcription."""
import os
from aiogram import Dispatcher, F
from aiogram.types import Message, FSInputFile
from loguru import logger

from db.database import get_session_factory
from db.models import Memory


async def transcribe_voice(file_path: str) -> str:
    """Transcribe voice message using whispercpp."""
    try:
        from whispercpp import Whisper
        
        # Initialize Whisper with base model
        whisper = Whisper('base')
        
        # Transcribe the audio file
        result = whisper.transcribe(file_path)
        
        # Extract text from result
        if isinstance(result, dict):
            text = result.get('text', '')
        else:
            text = str(result)
        
        return text.strip()
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return "Ошибка транскрипции"


async def handle_voice_message(message: Message) -> None:
    """Handle voice messages."""
    user_id = message.from_user.id
    
    # Get voice file
    voice = message.voice
    file = await message.bot.get_file(voice.file_id)
    
    # Create temporary file path
    temp_dir = "static/uploads/voice"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{file.file_id}.ogg")
    
    # Download the file
    await message.bot.download_file(file.file_path, file_path)
    
    # Transcribe
    await message.answer("🎤 Транскрибирую голосовое сообщение...")
    transcribed_text = await transcribe_voice(file_path)
    
    # Extract tags from transcribed text
    import re
    tags = re.findall(r'#(\w+)', transcribed_text.lower())
    
    # Save to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        memory = Memory(
            user_id=user_id,
            content=transcribed_text,
            memory_type="voice",
            tags=tags,
            file_id=file.file_id
        )
        session.add(memory)
        await session.commit()
    
    # Clean up temp file
    try:
        os.remove(file_path)
    except:
        pass
    
    response = f"✅ <b>Голосовое сообщение сохранено!</b>\n\n"
    response += f"📝 Текст: {transcribed_text}\n"
    if tags:
        response += f"🏷️ Теги: {', '.join(f'#{tag}' for tag in tags)}\n"
    
    await message.answer(response)
    logger.info(f"Saved voice memory from user {user_id}")


def register_voice_handlers(dp: Dispatcher) -> None:
    """Register voice message handlers."""
    dp.message.register(handle_voice_message, F.voice)
