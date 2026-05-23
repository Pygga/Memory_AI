"""Tests for db/users.py"""
import pytest
from sqlalchemy import select

from db.models import User
from db.users import get_or_create_user


@pytest.mark.asyncio
async def test_create_new_user(db_session):
    """Test creating a new user."""
    telegram_id = 123456789
    
    user = await get_or_create_user(
        db_session,
        telegram_id=telegram_id,
        username="test_user",
        first_name="Test"
    )
    
    assert user.id is not None  # Internal DB id assigned
    assert user.telegram_id == telegram_id
    assert user.username == "test_user"


@pytest.mark.asyncio
async def test_get_existing_user(db_session):
    """Test getting existing user (not creating duplicate)."""
    telegram_id = 987654321
    
    # Create user first time
    user1 = await get_or_create_user(
        db_session,
        telegram_id=telegram_id,
        username="first",
        first_name="First"
    )
    user1_id = user1.id
    
    # Get same user second time
    user2 = await get_or_create_user(
        db_session,
        telegram_id=telegram_id,
        username="second",  # Different data — should be ignored
        first_name="Second"
    )
    
    # Should return same user (same internal id)
    assert user2.id == user1_id
    assert user2.username == "first"  # Original data preserved


@pytest.mark.asyncio
async def test_user_flush_assigns_id(db_session):
    """Test that flush() assigns internal id before commit."""
    telegram_id = 555666777
    
    user = await get_or_create_user(
        db_session,
        telegram_id=telegram_id,
        username="flush_test"
    )
    
    # After flush(), user.id should be assigned (even before commit)
    assert user.id is not None
    assert isinstance(user.id, int)