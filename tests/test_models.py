"""Tests for db/models.py"""
import pytest
from datetime import datetime
from sqlalchemy import select

from db.models import User, Memory


@pytest.mark.asyncio
async def test_create_memory_with_user(db_session):
    """Test creating Memory linked to User."""
    # Create user
    user = User(telegram_id=111222333, username="memory_tester")
    db_session.add(user)
    await db_session.flush()
    
    # Create memory
    memory = Memory(
        user_id=user.id,
        content="Моё первое воспоминание #важное",
        memory_type="text",
        tags=["важное"]
    )
    db_session.add(memory)
    await db_session.commit()
    
    # Verify
    result = await db_session.execute(
        select(Memory).where(Memory.user_id == user.id)
    )
    saved_memory = result.scalar_one()
    
    assert saved_memory.content == "Моё первое воспоминание #важное"
    assert saved_memory.tags == ["важное"]
    assert saved_memory.created_at is not None


@pytest.mark.asyncio
async def test_memory_tags_default_empty(db_session):
    """Test that tags default to empty list."""
    user = User(telegram_id=444555666)
    db_session.add(user)
    await db_session.flush()
    
    memory = Memory(
        user_id=user.id,
        content="Без тегов",
        memory_type="text"
    )
    db_session.add(memory)
    await db_session.commit()
    
    assert memory.tags == []  # Default value


@pytest.mark.asyncio
async def test_memory_type_enum(db_session):
    """Test memory_type field accepts valid values."""
    user = User(telegram_id=777888999)
    db_session.add(user)
    await db_session.flush()
    
    for mem_type in ["text", "voice", "photo"]:
        memory = Memory(
            user_id=user.id,
            content=f"Test {mem_type}",
            memory_type=mem_type
        )
        db_session.add(memory)
    
    await db_session.commit()
    
    result = await db_session.execute(
        select(Memory.memory_type).distinct()
    )
    types = [row[0] for row in result.all()]
    
    assert set(types) == {"text", "voice", "photo"}


@pytest.mark.asyncio
async def test_create_chapter_with_story(db_session):
    """Test creating Chapter linked to Story."""
    user = User(telegram_id=999888777, username="chapter_tester")
    db_session.add(user)
    await db_session.flush()
    
    from db.models import Story, Chapter
    story = Story(user_id=user.id, title="История для глав", is_active=1)
    db_session.add(story)
    await db_session.flush()
    
    chapter = Chapter(
        story_id=story.id,
        title="Глава первая",
        content="Текст первой главы",
        chapter_number=1,
        memory_ids="1,2,3"
    )
    db_session.add(chapter)
    await db_session.commit()
    
    # Verify
    result = await db_session.execute(
        select(Chapter).where(Chapter.story_id == story.id)
    )
    saved_chapter = result.scalar_one()
    assert saved_chapter.title == "Глава первая"
    assert saved_chapter.content == "Текст первой главы"
    assert saved_chapter.chapter_number == 1
    assert saved_chapter.memory_ids == "1,2,3"


@pytest.mark.asyncio
async def test_create_llm_log_with_story(db_session):
    """Test creating LLMLog linked to User and Story."""
    user = User(telegram_id=888777666, username="log_tester")
    db_session.add(user)
    await db_session.flush()
    
    from db.models import Story, LLMLog
    story = Story(user_id=user.id, title="История логов", is_active=1)
    db_session.add(story)
    await db_session.flush()
    
    log = LLMLog(
        user_id=user.id,
        story_id=story.id,
        provider="groq",
        model_name="llama-3.3-70b-versatile",
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cost_usd=0.000985
    )
    db_session.add(log)
    await db_session.commit()
    
    # Verify
    result = await db_session.execute(
        select(LLMLog).where(LLMLog.user_id == user.id)
    )
    saved_log = result.scalar_one()
    assert saved_log.provider == "groq"
    assert saved_log.model_name == "llama-3.3-70b-versatile"
    assert saved_log.prompt_tokens == 1000
    assert saved_log.completion_tokens == 500
    assert saved_log.total_tokens == 1500
    assert saved_log.cost_usd == 0.000985