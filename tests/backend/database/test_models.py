"""
Tests for database models.
"""
import pytest
from datetime import datetime

from ydrpolicy.backend.database.models import User, Policy, PolicyChunk, Chat, Message, ToolUsage


@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test creating and retrieving a user."""
    # Create a user
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        is_admin=False
    )
    
    db_session.add(user)
    await db_session.flush()
    
    # Verify the user was created with proper attributes
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_admin is False
    assert user.created_at is not None
    
    # Retrieve the user directly
    from sqlalchemy import select
    stmt = select(User).where(User.email == "test@example.com")
    result = await db_session.execute(stmt)
    retrieved_user = result.scalars().first()
    
    assert retrieved_user is not None
    assert retrieved_user.id == user.id
    assert retrieved_user.email == "test@example.com"


@pytest.mark.asyncio
async def test_create_policy(db_session):
    """Test creating and retrieving a policy."""
    # Create a policy
    policy = Policy(
        title="Test Policy",
        description="This is a test policy description.",
        url="https://example.com/policy",
        content="This is a test policy content.",
        metadata={"department": "Radiology", "category": "Safety"}
    )
    
    db_session.add(policy)
    await db_session.flush()
    
    # Verify the policy was created with proper attributes
    assert policy.id is not None
    assert policy.title == "Test Policy"
    assert policy.url == "https://example.com/policy"
    assert policy.created_at is not None
    assert policy.metadata.get("department") == "Radiology"
    
    # Retrieve the policy directly
    from sqlalchemy import select
    stmt = select(Policy).where(Policy.title == "Test Policy")
    result = await db_session.execute(stmt)
    retrieved_policy = result.scalars().first()
    
    assert retrieved_policy is not None
    assert retrieved_policy.id == policy.id
    assert retrieved_policy.title == "Test Policy"


@pytest.mark.asyncio
async def test_create_policy_chunk(db_session):
    """Test creating and retrieving a policy chunk."""
    # First create a policy
    policy = Policy(
        title="Chunk Test Policy",
        description="This is a test for policy chunks.",
        url="https://example.com/chunk-test",
        content="This is the full content of the policy for chunk testing."
    )
    
    db_session.add(policy)
    await db_session.flush()
    
    # Now create a chunk for this policy
    chunk = PolicyChunk(
        policy_id=policy.id,
        chunk_index=0,
        content="This is a chunk of the policy content.",
        embedding=[0.1] * 1536  # Dummy embedding
    )
    
    db_session.add(chunk)
    await db_session.flush()
    
    # Verify the chunk was created with proper attributes
    assert chunk.id is not None
    assert chunk.policy_id == policy.id
    assert chunk.chunk_index == 0
    assert chunk.content == "This is a chunk of the policy content."
    assert len(chunk.embedding) == 1536
    
    # Verify the relationship works
    assert chunk.policy.id == policy.id
    assert chunk.policy.title == "Chunk Test Policy"
    
    # Verify the reverse relationship works
    assert len(policy.chunks) == 1
    assert policy.chunks[0].id == chunk.id


@pytest.mark.asyncio
async def test_create_chat_and_messages(db_session):
    """Test creating and retrieving a chat with messages."""
    # First create a user
    user = User(
        email="chat-test@example.com",
        password_hash="password",
        full_name="Chat Test User"
    )
    
    db_session.add(user)
    await db_session.flush()
    
    # Create a chat
    chat = Chat(
        user_id=user.id,
        title="Test Chat"
    )
    
    db_session.add(chat)
    await db_session.flush()
    
    # Create messages
    user_message = Message(
        chat_id=chat.id,
        role="user",
        content="What are the contrast protocols?"
    )
    
    assistant_message = Message(
        chat_id=chat.id,
        role="assistant",
        content="Here is information about contrast protocols."
    )
    
    db_session.add(user_message)
    db_session.add(assistant_message)
    await db_session.flush()
    
    # Create tool usage for assistant message
    tool_usage = ToolUsage(
        message_id=assistant_message.id,
        tool_name="rag",
        input={"query": "contrast protocols"},
        output={"results": [{"content": "Contrast protocols require...", "policy_title": "Contrast Policy"}]},
        execution_time=0.35
    )
    
    db_session.add(tool_usage)
    await db_session.flush()
    
    # Verify the relationships
    from sqlalchemy import select
    
    # Get the chat with messages
    stmt = select(Chat).where(Chat.id == chat.id)
    result = await db_session.execute(stmt)
    retrieved_chat = result.scalars().first()
    
    assert retrieved_chat is not None
    assert len(retrieved_chat.messages) == 2
    
    # Check the tool usage
    stmt = select(ToolUsage).where(ToolUsage.message_id == assistant_message.id)
    result = await db_session.execute(stmt)
    retrieved_tool_usage = result.scalars().first()
    
    assert retrieved_tool_usage is not None
    assert retrieved_tool_usage.tool_name == "rag"
    assert retrieved_tool_usage.execution_time == 0.35