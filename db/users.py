"""User management utilities."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None
) -> User:
    """
    Get existing user by telegram_id or create new one.
    
    Returns User object with populated .id (internal DB id).
    """
    # Try to find existing user
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    # Create new user if not found
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        # Flush to get the generated user.id BEFORE commit
        await session.flush()
    
    return user