from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, 
    Integer, Float, UniqueConstraint, Index, func, JSON
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, mapped_column, Mapped

# Import for pgvector
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # For type checking and testing without pgvector
    class Vector:
        def __init__(self, dimensions):
            self.dimensions = dimensions

# Base class for all models
Base = declarative_base(cls=(AsyncAttrs,))


class User(Base):
    """User model for authentication and access control."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    chats: Mapped[List["Chat"]] = relationship("Chat", back_populates="user")
    policy_updates: Mapped[List["PolicyUpdate"]] = relationship("PolicyUpdate", back_populates="admin")

    def __repr__(self):
        return f"<User {self.email}>"


class Policy(Base):
    """Policy document model."""
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR, nullable=True
    )

    # Relationships
    chunks: Mapped[List["PolicyChunk"]] = relationship(
        "PolicyChunk", back_populates="policy", cascade="all, delete-orphan"
    )
    updates: Mapped[List["PolicyUpdate"]] = relationship(
        "PolicyUpdate", back_populates="policy"
    )

    # Indexes
    __table_args__ = (
        Index(
            'idx_policies_search_vector',
            search_vector,
            postgresql_using='gin'
        ),
    )

    def __repr__(self):
        return f"<Policy {self.title}>"


class PolicyChunk(Base):
    """Chunks of policy documents with embeddings."""
    __tablename__ = "policy_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("policies.id"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding = Column(Vector(1536))  # Default for OpenAI text-embedding-3-small
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    policy: Mapped["Policy"] = relationship("Policy", back_populates="chunks")

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('policy_id', 'chunk_index', name='uix_policy_chunk_index'),
        Index(
            'idx_policy_chunks_search_vector',
            search_vector,
            postgresql_using='gin'
        ),
        Index(
            'idx_policy_chunks_embedding',
            embedding,
            postgresql_using='ivfflat',
            postgresql_with={'lists': 100}
        ),
    )

    def __repr__(self):
        return f"<PolicyChunk {self.policy_id}:{self.chunk_index}>"


class Chat(Base):
    """Chat session model."""
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Chat {self.id}>"


class Message(Base):
    """Message model for chat interactions."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chats.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # 'user', 'assistant', or 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    tool_usages: Mapped[List["ToolUsage"]] = relationship(
        "ToolUsage", back_populates="message", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Message {self.id} ({self.role})>"


class ToolUsage(Base):
    """Tool usage tracking for assistant messages."""
    __tablename__ = "tool_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 'rag', 'keyword_search', etc.
    input: Mapped[dict] = mapped_column(JSON, nullable=False)  # Tool input parameters
    output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Tool output
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    execution_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Time taken in seconds

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="tool_usages")

    def __repr__(self):
        return f"<ToolUsage {self.id} {self.tool_name}>"


class PolicyUpdate(Base):
    """Log of policy updates."""
    __tablename__ = "policy_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    policy_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("policies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # 'create', 'update', 'delete'
    details: Mapped[dict] = mapped_column(JSON, nullable=True)  # Details of what was changed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    admin: Mapped[Optional["User"]] = relationship("User", back_populates="policy_updates")
    policy: Mapped[Optional["Policy"]] = relationship("Policy", back_populates="updates")

    def __repr__(self):
        return f"<PolicyUpdate {self.id} {self.action}>"


# Create a trigger function to update search_vector on policies
def create_search_vector_trigger():
    """SQL to create trigger function for updating search vectors."""
    return """
    CREATE OR REPLACE FUNCTION policies_search_vector_update() RETURNS trigger AS $$
    BEGIN
        NEW.search_vector = setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                            setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                            setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'C');
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS policies_search_vector_update ON policies;
    CREATE TRIGGER policies_search_vector_update
    BEFORE INSERT OR UPDATE ON policies
    FOR EACH ROW EXECUTE FUNCTION policies_search_vector_update();
    
    -- For policy chunks
    CREATE OR REPLACE FUNCTION policy_chunks_search_vector_update() RETURNS trigger AS $$
    BEGIN
        NEW.search_vector = to_tsvector('english', COALESCE(NEW.content, ''));
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS policy_chunks_search_vector_update ON policy_chunks;
    CREATE TRIGGER policy_chunks_search_vector_update
    BEFORE INSERT OR UPDATE ON policy_chunks
    FOR EACH ROW EXECUTE FUNCTION policy_chunks_search_vector_update();
    """