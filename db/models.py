"""Database models."""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, func, Float
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String, default="free")
    generation_credits: Mapped[int] = mapped_column(default=9999) # 9999 for testing
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    memories: Mapped[List["Memory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    stories: Mapped[List["Story"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[int] = mapped_column(default=1)  # 1 for True, 0 for False (using Integer for easier sqlite/postgres compat)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="stories")
    memories: Mapped[List["Memory"]] = relationship(back_populates="story", cascade="all, delete-orphan")
    chapters: Mapped[List["Chapter"]] = relationship(back_populates="story", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Story(id={self.id}, title='{self.title}', user_id={self.user_id})>"


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    story_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stories.id"), nullable=True, index=True)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(20), default="text")
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), server_default="{}")
    file_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="memories")
    story: Mapped[Optional["Story"]] = relationship(back_populates="memories")

    def __repr__(self):
        return f"<Memory(id={self.id}, user_id={self.user_id}, story_id={self.story_id})>"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(nullable=False) # e.g. amount of Telegram Stars
    currency: Mapped[str] = mapped_column(String, default="XTR")
    status: Mapped[str] = mapped_column(String, default="pending") # pending, completed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship()

    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount})>"


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chapter_number: Mapped[int] = mapped_column(nullable=False)
    memory_ids: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    story: Mapped["Story"] = relationship(back_populates="chapters")

    def __repr__(self):
        return f"<Chapter(id={self.id}, story_id={self.story_id}, title='{self.title}', number={self.chapter_number})>"


class LLMLog(Base):
    __tablename__ = "llm_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    story_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stories.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship()
    story: Mapped[Optional["Story"]] = relationship()

    def __repr__(self):
        return f"<LLMLog(id={self.id}, user_id={self.user_id}, total_tokens={self.total_tokens}, cost_usd={self.cost_usd})>"