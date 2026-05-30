"""Database models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    subscription_tier = Column(String, default="free")
    generation_credits = Column(Integer, default=9999) # 9999 for testing
    
    # 🔧 FIX: naive datetime + server_default для БД
    created_at = Column(DateTime, server_default=func.now())

    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    is_active = Column(Integer, default=1)  # 1 for True, 0 for False (using Integer for easier sqlite/postgres compat)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="stories")
    memories = relationship("Memory", back_populates="story", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Story(id={self.id}, title='{self.title}', user_id={self.user_id})>"


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True, index=True)
    
    content = Column(Text, nullable=False)
    memory_type = Column(String(20), default="text")
    # 🔧 FIX: server_default для ARRAY
    tags = Column(ARRAY(String), server_default="{}")
    file_id = Column(String, nullable=True)
    
    # 🔧 FIX: naive datetime + func.now() для авто-заполнения в БД
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="memories")
    story = relationship("Story", back_populates="memories")

    def __repr__(self):
        return f"<Memory(id={self.id}, user_id={self.user_id}, story_id={self.story_id})>"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False) # e.g. amount of Telegram Stars
    currency = Column(String, default="XTR")
    status = Column(String, default="pending") # pending, completed, failed
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")

    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount})>"