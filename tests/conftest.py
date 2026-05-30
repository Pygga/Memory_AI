"""Pytest fixtures for database and session management."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import sys
from unittest.mock import MagicMock

# Mock weasyprint for local testing where system libs might be missing
sys.modules['weasyprint'] = MagicMock()

from db.database import Base
from db.models import User, Memory


# URL для тестовой БД (отдельная БД или in-memory)
TEST_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/memory_book_test"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def setup_database(engine):
    """Create tables before test, drop after."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        pytest.skip(f"Database not available: {e}")
        
    yield
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def session_factory(engine):
    """Create async session factory."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture(scope="function")
async def db_session(setup_database, session_factory):
    """Provide async session for tests with automatic rollback."""
    async with session_factory() as session:
        yield session
        await session.rollback()  # Откатываем изменения после теста