from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from db.models import User, Story, Memory, Chapter, LLMLog, Payment
from typing import List, Optional, Any


class BaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


class UserRepository(BaseRepository):
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.session.add(user)
            await self.session.flush()
        return user


class StoryRepository(BaseRepository):
    async def get_by_id(self, story_id: int, load_chapters: bool = False) -> Optional[Story]:
        stmt = select(Story).where(Story.id == story_id)
        if load_chapters:
            stmt = stmt.options(selectinload(Story.chapters))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_user_id(self, user_id: int) -> Optional[Story]:
        result = await self.session.execute(
            select(Story).where(Story.user_id == user_id, Story.is_active == 1)
        )
        return result.scalar_one_or_none()

    async def get_all_by_user_id(self, user_id: int) -> List[Story]:
        result = await self.session.execute(
            select(Story).where(Story.user_id == user_id).order_by(Story.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, user_id: int, title: str, is_active: int = 1) -> Story:
        story = Story(user_id=user_id, title=title, is_active=is_active)
        self.session.add(story)
        await self.session.flush()
        return story

    async def deactivate_all_for_user(self, user_id: int) -> None:
        await self.session.execute(
            update(Story).where(Story.user_id == user_id).values(is_active=0)
        )


class MemoryRepository(BaseRepository):
    async def create(
        self,
        user_id: int,
        story_id: Optional[int],
        content: str,
        memory_type: str = "text",
        tags: Optional[List[str]] = None,
        file_id: Optional[str] = None
    ) -> Memory:
        memory = Memory(
            user_id=user_id,
            story_id=story_id,
            content=content,
            memory_type=memory_type,
            tags=tags or [],
            file_id=file_id
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get_by_id(self, memory_id: int) -> Optional[Memory]:
        result = await self.session.execute(
            select(Memory).where(Memory.id == memory_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_story(self, user_id: int, story_id: Optional[int]) -> List[Memory]:
        stmt = select(Memory).where(Memory.user_id == user_id)
        if story_id is not None:
            stmt = stmt.where(Memory.story_id == story_id)
        stmt = stmt.order_by(Memory.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_user(self, user_id: int, limit: int = 10) -> List[Memory]:
        stmt = select(Memory).where(Memory.user_id == user_id).order_by(Memory.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_id(self, memory_id: int) -> bool:
        result = await self.session.execute(
            delete(Memory).where(Memory.id == memory_id)
        )
        return (result.rowcount or 0) > 0

    async def get_by_ids(self, memory_ids: list[int]) -> list[Memory]:
        """Fetch multiple memories by their IDs, ordered by creation date."""
        if not memory_ids:
            return []
        result = await self.session.execute(
            select(Memory).where(Memory.id.in_(memory_ids)).order_by(Memory.created_at.asc())
        )
        return list(result.scalars().all())


class ChapterRepository(BaseRepository):
    async def create(self, story_id: int, title: str, content: str, chapter_number: int, memory_ids: Optional[str] = None) -> Chapter:
        chapter = Chapter(
            story_id=story_id,
            title=title,
            content=content,
            chapter_number=chapter_number,
            memory_ids=memory_ids
        )
        self.session.add(chapter)
        await self.session.flush()
        return chapter

    async def get_by_id(self, chapter_id: int) -> Optional[Chapter]:
        result = await self.session.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        return result.scalar_one_or_none()

    async def update_content(self, chapter_id: int, content: str) -> None:
        await self.session.execute(
            update(Chapter).where(Chapter.id == chapter_id).values(content=content)
        )

    async def update_title_and_content(self, chapter_id: int, title: str, content: str) -> None:
        """Update both title and content of a chapter."""
        await self.session.execute(
            update(Chapter).where(Chapter.id == chapter_id).values(title=title, content=content)
        )

    async def delete_all_for_story(self, story_id: int) -> None:
        await self.session.execute(
            delete(Chapter).where(Chapter.story_id == story_id)
        )


class LLMLogRepository(BaseRepository):
    async def create(
        self,
        user_id: int,
        story_id: Optional[int],
        provider: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float
    ) -> LLMLog:
        log = LLMLog(
            user_id=user_id,
            story_id=story_id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd
        )
        self.session.add(log)
        await self.session.flush()
        return log


class PaymentRepository(BaseRepository):
    async def create(self, user_id: int, amount: int, currency: str = "XTR", status: str = "pending") -> Payment:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            status=status
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def update_status(self, payment_id: int, status: str) -> None:
        await self.session.execute(
            update(Payment).where(Payment.id == payment_id).values(status=status)
        )
