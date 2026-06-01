"""Database connection and session management."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from loguru import logger
from typing import AsyncGenerator


# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/memory_book")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Session factory
session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base for models
Base = declarative_base()


async def init_db():
    """Initialize database tables."""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Import all models to ensure they're registered with Base
            from db.models import Memory, Story, User, Chapter, LLMLog  # noqa: F401
            
            # Create all tables (this will create stories table automatically)
            await conn.run_sync(Base.metadata.create_all)
            
            # Migrate memories to add story_id if it doesn't exist
            # Add column
            await conn.execute(text("ALTER TABLE memories ADD COLUMN IF NOT EXISTS story_id INTEGER REFERENCES stories(id);"))
            
            # Migrate users to add subscription and credits
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR DEFAULT 'free';"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS generation_credits INTEGER DEFAULT 9999;"))
            
        # Second transaction for data migration (needs its own transaction after column creation)
        async with engine.begin() as conn:
            # Check if there are any memories without a story
            result = await conn.execute(text("SELECT COUNT(*) FROM memories WHERE story_id IS NULL"))
            count = result.scalar()
            
            if count and count > 0:
                logger.info(f"Found {count} memories without a story. Creating 'Архив' stories.")
                # We need to create an Archive story for each user who has memories without a story
                await conn.execute(text("""
                    INSERT INTO stories (user_id, title, is_active, created_at)
                    SELECT DISTINCT user_id, 'Архив', 0, NOW()
                    FROM memories
                    WHERE story_id IS NULL
                    ON CONFLICT DO NOTHING
                """))
                
                # Now update those memories
                await conn.execute(text("""
                    UPDATE memories m
                    SET story_id = s.id
                    FROM stories s
                    WHERE m.user_id = s.user_id AND s.title = 'Архив' AND m.story_id IS NULL
                """))
                
        logger.info("Database tables and migrations created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def get_session_factory():
    """Get the session factory."""
    return session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session (for dependency injection)."""
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
