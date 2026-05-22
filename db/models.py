"""Database models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
import enum

from db.database import Base


class MemoryType(enum.Enum):
    """Types of memories."""
    TEXT = "text"
    VOICE = "voice"
    PHOTO = "photo"


class Memory(Base):
    """Memory model for storing user memories."""
    
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String(20), default="text")
    tags = Column(ARRAY(String), default=list)
    file_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Memory(id={self.id}, user_id={self.user_id}, type={self.memory_type})>"


class User(Base):
    """User model (optional, for future expansion)."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to memories
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"


# Add backref to Memory
Memory.user = relationship("User", back_populates="memories")
