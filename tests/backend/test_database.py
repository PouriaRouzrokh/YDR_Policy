import pytest
import asyncio
import uuid
from typing import Generator, AsyncGenerator
from datetime import datetime

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# PostgreSQL connection details - customize these for your environment
PG_USER = "pouria"
PG_PASSWORD = ""  # Empty password
PG_HOST = "localhost"
PG_PORT = "5432"
PG_BASE_DB = "postgres"  # Default database for initial connection

# Import the modules we'll be testing
from ydrpolicy.backend.database.engine import get_async_engine, get_async_session
from ydrpolicy.backend.database.models import Base, Policy, PolicyChunk, User, Message, ToolUsage, Chat
from ydrpolicy.backend.database.init_db import init_db, create_tables
from ydrpolicy.backend.services.embeddings import embed_text, dummy_embed_text
from ydrpolicy.backend.services.chunking import chunk_text
from ydrpolicy.backend.database.repository.policies import PolicyRepository
from ydrpolicy.backend.database.repository.users import UserRepository
from ydrpolicy.backend.config import config
from ydrpolicy.backend.logger import logger

# Use a unique database name for tests to avoid conflicts
TEST_DB_NAME = f"test_ydrpolicy_{uuid.uuid4().hex[:8]}"
# Format: postgresql://user:password@host:port/dbname
# For empty password: postgresql://user@host:port/dbname
PG_DSN = f"postgresql://{PG_USER}{':{}'.format(PG_PASSWORD) if PG_PASSWORD else ''}@{PG_HOST}:{PG_PORT}"
TEST_POSTGRES_DSN = f"{PG_DSN}/{TEST_DB_NAME}"
ADMIN_POSTGRES_DSN = f"{PG_DSN}/{PG_BASE_DB}"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for pytest-asyncio."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def postgres_connection() -> AsyncGenerator:
    """Create a test database and yield a connection to it."""
    # Connect to the postgres database to create our test database
    conn = await asyncpg.connect(ADMIN_POSTGRES_DSN)
    
    # Ensure the test database doesn't exist (in case of previous failed tests)
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    
    # Create a fresh test database
    await conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    await conn.close()
    
    # Now connect to our test database
    test_conn = await asyncpg.connect(f"{PG_DSN}/{TEST_DB_NAME}")
    
    # Create the pgvector extension
    await test_conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    yield test_conn
    
    # Cleanup
    await test_conn.close()
    
    # Reconnect to postgres to drop the test database
    conn = await asyncpg.connect(ADMIN_POSTGRES_DSN)
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    await conn.close()


@pytest.fixture(scope="session")
async def db_engine(postgres_connection):
    """Create a SQLAlchemy engine connected to the test database."""
    engine = create_async_engine(TEST_POSTGRES_DSN)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator:
    """Create a fresh SQLAlchemy session for each test."""
    async_session = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        yield session
        # Rollback any changes to keep tests isolated
        await session.rollback()


@pytest.fixture(scope="function")
async def policy_repository(db_session) -> PolicyRepository:
    """Create a policy repository for testing."""
    return PolicyRepository(db_session)


@pytest.fixture(scope="function")
async def user_repository(db_session) -> UserRepository:
    """Create a user repository for testing."""
    return UserRepository(db_session)


@pytest.mark.asyncio
async def test_db_connection(db_session):
    """Test that we can connect to the database and execute a query."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_pgvector_extension(db_session):
    """Test that the pgvector extension is properly installed."""
    result = await db_session.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
    assert result.scalar() is not None


@pytest.mark.asyncio
async def test_create_user(user_repository):
    """Test creating a user in the database."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    assert created_user.id is not None
    assert created_user.email == "test@example.com"
    assert created_user.full_name == "Test User"
    
    # Test retrieval
    retrieved_user = await user_repository.get_by_email("test@example.com")
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id


@pytest.mark.asyncio
async def test_create_policy(policy_repository):
    """Test creating a policy in the database."""
    policy = Policy(
        title="Test Policy",
        description="This is a test policy description.",
        url="https://example.com/policy",
        content="This is a test policy content.",
        metadata={"department": "Radiology", "category": "Safety"}
    )
    
    created_policy = await policy_repository.create(policy)
    assert created_policy.id is not None
    assert created_policy.title == "Test Policy"
    
    # Test retrieval
    retrieved_policy = await policy_repository.get_by_id(created_policy.id)
    assert retrieved_policy is not None
    assert retrieved_policy.title == "Test Policy"
    assert retrieved_policy.content == "This is a test policy content."


@pytest.mark.asyncio
async def test_chunking_and_embedding(policy_repository):
    """Test the chunking and embedding functionality."""
    # Create a policy
    policy = Policy(
        title="Embedding Test Policy",
        description="Policy for testing embeddings",
        url="https://example.com/embedding-test",
        content="This is a test policy content that will be chunked and embedded. " * 10,
        metadata={"department": "Radiology", "category": "Embedding Tests"}
    )
    
    created_policy = await policy_repository.create(policy)
    
    # Chunk the policy content
    chunks = chunk_text(created_policy.content, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1  # We should have multiple chunks
    
    # Create embeddings for each chunk
    for i, chunk_content in enumerate(chunks):
        # Generate embedding using dummy function to avoid API calls during tests
        embedding = await dummy_embed_text(chunk_content)
        assert len(embedding) > 0  # Embedding should have values
        
        # Create a chunk with embedding
        chunk = PolicyChunk(
            policy_id=created_policy.id,
            chunk_index=i,
            content=chunk_content,
            embedding=embedding
        )
        
        # Save the chunk
        await policy_repository.create_chunk(chunk)
    
    # Test vector search
    query = "test policy content"
    query_embedding = await dummy_embed_text(query)
    
    # Search for similar chunks
    similar_chunks = await policy_repository.search_chunks_by_embedding(
        query_embedding,
        limit=2,
        similarity_threshold=0.5  # Lower threshold for dummy embeddings
    )
    
    assert len(similar_chunks) > 0
    # The chunks should have a similarity score
    assert similar_chunks[0]['similarity'] > 0


@pytest.mark.asyncio
async def test_repository_pattern(policy_repository):
    """Test the repository pattern with more complex operations."""
    # Create multiple policies
    policies = [
        Policy(
            title=f"Test Policy {i}",
            description=f"Description for test policy {i}",
            url=f"https://example.com/policy/{i}",
            content=f"Content for test policy {i}",
            metadata={"department": "Radiology", "category": "Test"}
        )
        for i in range(5)
    ]
    
    for policy in policies:
        await policy_repository.create(policy)
    
    # Test listing all policies
    all_policies = await policy_repository.get_all()
    assert len(all_policies) >= 5
    
    # Test getting recent policies
    recent_policies = await policy_repository.get_recent_policies(limit=3)
    assert len(recent_policies) == 3
    
    # Test full-text search
    search_results = await policy_repository.full_text_search("test policy")
    assert len(search_results) > 0


@pytest.mark.asyncio



@pytest.mark.asyncio
async def test_policy_update_logging(policy_repository, user_repository):
    """Test logging policy updates."""
    # Create a user (admin)
    admin = User(
        email="admin@example.com",
        password_hash="admin_password",
        full_name="Admin User",
        is_admin=True
    )
    created_admin = await user_repository.create(admin)
    
    # Create a policy
    policy = Policy(
        title="Update Test Policy",
        description="Policy for testing updates",
        url="https://example.com/update-test",
        content="Original content",
        metadata={"department": "Radiology"}
    )
    created_policy = await policy_repository.create(policy)
    
    # Log an update
    update_details = {
        "changed_fields": ["content", "title"],
        "old_title": "Update Test Policy",
        "new_title": "Updated Policy",
        "content_changed": True
    }
    
    log_entry = await policy_repository.log_policy_update(
        policy_id=created_policy.id,
        admin_id=created_admin.id,
        action="update",
        details=update_details
    )
    
    assert log_entry.id is not None
    assert log_entry.policy_id == created_policy.id
    assert log_entry.admin_id == created_admin.id
    assert log_entry.action == "update"
    
    # Get update history
    history = await policy_repository.get_policy_update_history(created_policy.id)
    assert len(history) == 1
    assert history[0].id == log_entry.id


@pytest.mark.asyncio
async def test_tool_usage_tracking(db_session):
    """Test tracking tool usage for message responses."""
    # Create a user
    user = User(
        email="tool-test@example.com",
        password_hash="password",
        full_name="Tool Test User",
        is_admin=False
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create a chat
    chat = Chat(
        user_id=user.id,
        title="Tool Test Chat"
    )
    db_session.add(chat)
    await db_session.flush()
    
    # Create a message
    message = Message(
        chat_id=chat.id,
        role="assistant",
        content="Here is information about contrast protocols."
    )
    db_session.add(message)
    await db_session.flush()
    
    # Create a tool usage record
    tool_usage = ToolUsage(
        message_id=message.id,
        tool_name="rag",
        input={"query": "contrast protocols"},
        output={"results": [{"content": "Contrast protocols require...", "policy_title": "Contrast Policy"}]},
        execution_time=0.35
    )
    db_session.add(tool_usage)
    await db_session.flush()
    
    # Query the tool usage
    stmt = text("""
        SELECT m.content, t.tool_name, t.execution_time
        FROM tool_usage t
        JOIN messages m ON t.message_id = m.id
        WHERE t.message_id = :message_id
    """)
    result = await db_session.execute(stmt, {"message_id": message.id})
    row = result.fetchone()
    
    assert row is not None
    assert row.content == "Here is information about contrast protocols."
    assert row.tool_name == "rag"
    assert row.execution_time == 0.35


@pytest.mark.asyncio
async def test_init_db_script():
    """Test the init_db script that creates the database from scratch."""
    # Use a completely new database name
    temp_db_name = f"temp_ydrpolicy_{uuid.uuid4().hex[:8]}"
    temp_db_url = f"{PG_DSN}/{temp_db_name}"
    
    # Create a new database
    conn = await asyncpg.connect(ADMIN_POSTGRES_DSN)
    await conn.execute(f"DROP DATABASE IF EXISTS {temp_db_name}")
    await conn.execute(f"CREATE DATABASE {temp_db_name}")
    await conn.close()
    
    try:
        # Initialize the database using our init_db function
        await init_db(temp_db_url)
        
        # Connect to the initialized database and verify it's set up correctly
        engine = create_async_engine(temp_db_url)
        session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        async with session_maker() as session:
            # Check that pgvector extension is installed
            result = await session.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            assert result.scalar() is not None
            
            # Check that tables are created
            result = await session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'policies')"
            ))
            assert result.scalar() is True
            
            result = await session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'policy_chunks')"
            ))
            assert result.scalar() is True
            
            result = await session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            ))
            assert result.scalar() is True
            
            result = await session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tool_usage')"
            ))
            assert result.scalar() is True
            
        await engine.dispose()
    
    finally:
        # Cleanup
        conn = await asyncpg.connect(ADMIN_POSTGRES_DSN)
        await conn.execute(f"DROP DATABASE IF EXISTS {temp_db_name}")
        await conn.close()


@pytest.mark.asyncio
async def test_admin_user_operations(user_repository):
    """Test admin-specific user operations."""
    # Create a regular user
    user = User(
        email="regular@example.com",
        password_hash="password",
        full_name="Regular User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    assert created_user.is_admin is False
    
    # Promote to admin
    promoted_user = await user_repository.promote_to_admin(created_user.id)
    assert promoted_user.is_admin is True
    
    # Retrieve and verify
    retrieved_user = await user_repository.get_by_id(created_user.id)
    assert retrieved_user.is_admin is True
    
    # Demote from admin
    demoted_user = await user_repository.demote_from_admin(created_user.id)
    assert demoted_user.is_admin is False
    
    # Retrieve and verify
    retrieved_user = await user_repository.get_by_id(created_user.id)
    assert retrieved_user.is_admin is False


@pytest.mark.asyncio
async def test_get_policy_by_url(policy_repository):
    """Test retrieving a policy by its URL."""
    # Create a policy
    url = "https://example.com/unique-policy-url"
    policy = Policy(
        title="URL Test Policy",
        description="This is a test for URL retrieval",
        url=url,
        content="This policy can be retrieved by URL."
    )
    
    await policy_repository.create(policy)
    
    # Retrieve by URL
    retrieved_policy = await policy_repository.get_by_url(url)
    assert retrieved_policy is not None
    assert retrieved_policy.title == "URL Test Policy"
    
    # Test with non-existent URL
    non_existent = await policy_repository.get_by_url("https://example.com/non-existent")
    assert non_existent is None


@pytest.mark.asyncio
async def test_get_complete_policies_from_chunks(policy_repository):
    """Test retrieving complete policies from chunk search results."""
    # Create multiple policies
    policies = [
        Policy(
            title=f"Complete Policy Test {i}",
            description=f"Testing complete policy retrieval {i}",
            url=f"https://example.com/policy/complete-{i}",
            content=f"Complete policy content for test {i}. This is a longer content with more details.",
            metadata={"department": "Radiology", "test_case": "complete_retrieval"}
        )
        for i in range(3)
    ]
    
    created_policies = []
    for policy in policies:
        created = await policy_repository.create(policy)
        created_policies.append(created)
        
        # Create chunks for each policy
        chunks = chunk_text(created.content, chunk_size=50, chunk_overlap=10)
        for i, chunk_content in enumerate(chunks):
            embedding = await dummy_embed_text(chunk_content)
            chunk = PolicyChunk(
                policy_id=created.id,
                chunk_index=i,
                content=chunk_content,
                embedding=embedding
            )
            await policy_repository.create_chunk(chunk)
    
    # Perform a search that should match chunks from multiple policies
    query = "complete policy test"
    query_embedding = await dummy_embed_text(query)
    
    # Use hybrid search to find chunks
    chunk_results = await policy_repository.hybrid_search(
        query=query,
        embedding=query_embedding,
        similarity_threshold=0.1  # Low threshold for test
    )
    
    assert len(chunk_results) > 0
    logger.info(f"Search returned {len(chunk_results)} chunks")
    
    # Get the complete policies from chunks
    complete_policies = await policy_repository.get_policies_from_chunks(chunk_results)
    
    # Verify we got the complete policies
    assert len(complete_policies) > 0
    
    # Check that each policy has its full content
    for policy in complete_policies:
        assert len(policy.content) > 0
        assert "Complete policy content" in policy.content
        
    # Verify we got unique policies (no duplicates)
    policy_ids = [p.id for p in complete_policies]
    assert len(policy_ids) == len(set(policy_ids))
    
    logger.info(f"Retrieved {len(complete_policies)} complete policies from chunks")


@pytest.mark.asyncio
async def test_user_authentication(user_repository):
    """Test user authentication functionality."""
    # Create a user
    user = User(
        email="auth@example.com",
        password_hash="correct_hash",
        full_name="Auth Test User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    
    # Test successful authentication
    authenticated_user = await user_repository.authenticate(
        email="auth@example.com", 
        password_hash="correct_hash"
    )
    assert authenticated_user is not None
    assert authenticated_user.id == created_user.id
    
    # Test authentication with wrong password
    wrong_user = await user_repository.authenticate(
        email="auth@example.com", 
        password_hash="wrong_hash"
    )
    assert wrong_user is None
    
    # Test authentication with non-existent user
    non_existent = await user_repository.authenticate(
        email="nonexistent@example.com", 
        password_hash="any_hash"
    )
    assert non_existent is None