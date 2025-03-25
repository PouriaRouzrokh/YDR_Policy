from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, 
    Integer, Float, UniqueConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB, TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, mapped_column, Mapped

from ydrpolicy.backend.config import config

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

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(128))
    first_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    chats: Mapped[List["Chat"]] = relationship("Chat", back_populates="user")
    api_usage: Mapped[List["APIUsage"]] = relationship("APIUsage", back_populates="user")
    feedback: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"


class Policy(Base):
    """Policy document model."""
    __tablename__ = "policies"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    title: Mapped[str] = mapped_column(String(256), index=True)
    content: Mapped[str] = mapped_column(Text)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    department: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_updated: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR, nullable=True
    )

    # Relationships
    chunks: Mapped[List["PolicyChunk"]] = relationship(
        "PolicyChunk", back_populates="policy", cascade="all, delete-orphan"
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

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    policy_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding = Column(
        Vector(config.RAG.EMBEDDING_DIMENSIONS),
        nullable=True
    )
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
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

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="chat", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Chat {self.id}>"


class ChatMessage(Base):
    """Individual chat message model."""
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    chat_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    
    # For tracking which tools/chunks were used
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage {self.id} ({self.role})>"


class Feedback(Base):
    """User feedback on responses."""
    __tablename__ = "feedback"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    message_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer)  # 1-5 star rating
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback {self.id} ({self.rating})>"


class APIUsage(Base):
    """API usage tracking model."""
    __tablename__ = "api_usage"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    endpoint: Mapped[str] = mapped_column(String(256))
    method: Mapped[str] = mapped_column(String(10))
    status_code: Mapped[int] = mapped_column(Integer)
    response_time_ms: Mapped[float] = mapped_column(Float)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_usage")

    def __repr__(self):
        return f"<APIUsage {self.endpoint} ({self.status_code})>"


class SearchLog(Base):
    """Log of search queries and results."""
    __tablename__ = "search_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(Text)
    search_type: Mapped[str] = mapped_column(String(20))  # 'vector', 'keyword', 'hybrid'
    num_results: Mapped[int] = mapped_column(Integer)
    execution_time_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)  # For additional search parameters

    def __repr__(self):
        return f"<SearchLog {self.id} ({self.search_type})>"


# Create a trigger function to update search_vector on policies
def create_search_vector_trigger():
    """SQL to create trigger function for updating search vectors."""
    return """
    CREATE OR REPLACE FUNCTION policies_search_vector_update() RETURNS trigger AS $$
    BEGIN
        NEW.search_vector = setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                            setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B') ||
                            setweight(to_tsvector('english', COALESCE(NEW.department, '')), 'C') ||
                            setweight(to_tsvector('english', COALESCE(NEW.category, '')), 'C');
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