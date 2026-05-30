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