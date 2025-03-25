import pytest
import asyncio
import uuid
from typing import Generator, AsyncGenerator

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Import the modules we'll be testing
from ydrpolicy.backend.database.engine import get_async_engine, get_async_session
from ydrpolicy.backend.database.models import Base, Policy, PolicyChunk, User
from ydrpolicy.backend.database.init_db import init_db, create_tables
from ydrpolicy.backend.services.embeddings import embed_text
from ydrpolicy.backend.services.chunking import chunk_text
from ydrpolicy.backend.repository.policies import PolicyRepository
from ydrpolicy.backend.repository.users import UserRepository
from ydrpolicy.config import get_settings

# PostgreSQL connection details - customize these for your environment
PG_USER = "pouria"
PG_PASSWORD = ""  # Empty password
PG_HOST = "localhost"
PG_PORT = "5432"
PG_BASE_DB = "postgres"  # Default database for initial connection

# Use a unique database name for tests to avoid conflicts
TEST_DB_NAME = f"test_ydrpolicy_{uuid.uuid4().hex[:8]}"
# Format: postgresql://user:password@host:port/dbname (for empty password: postgresql://user@host:port/dbname)
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
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    assert created_user.id is not None
    assert created_user.username == "testuser"
    assert created_user.email == "test@example.com"
    
    # Test retrieval
    retrieved_user = await user_repository.get_by_username("testuser")
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id


@pytest.mark.asyncio
async def test_create_policy(policy_repository):
    """Test creating a policy in the database."""
    policy = Policy(
        title="Test Policy",
        content="This is a test policy content.",
        source_url="https://example.com/policy",
        department="Radiology",
        last_updated="2023-01-01"
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
        content="This is a test policy content that will be chunked and embedded. " * 10,
        source_url="https://example.com/policy",
        department="Radiology",
        last_updated="2023-01-01"
    )
    
    created_policy = await policy_repository.create(policy)
    
    # Chunk the policy content
    chunks = chunk_text(created_policy.content, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1  # We should have multiple chunks
    
    # Create embeddings for each chunk
    for i, chunk_text in enumerate(chunks):
        # Generate embedding
        embedding = await embed_text(chunk_text)
        assert len(embedding) > 0  # Embedding should have values
        
        # Create a chunk with embedding
        chunk = PolicyChunk(
            policy_id=created_policy.id,
            chunk_index=i,
            content=chunk_text,
            embedding=embedding
        )
        
        # Save the chunk
        await policy_repository.create_chunk(chunk)
    
    # Test vector search
    query = "test policy content"
    query_embedding = await embed_text(query)
    
    # Search for similar chunks
    similar_chunks = await policy_repository.search_chunks_by_embedding(
        query_embedding,
        limit=2,
        similarity_threshold=0.7
    )
    
    assert len(similar_chunks) > 0
    # The first chunk should have a higher similarity score
    assert similar_chunks[0].similarity >= 0.7


@pytest.mark.asyncio
async def test_repository_pattern(policy_repository):
    """Test the repository pattern with more complex operations."""
    # Create multiple policies
    policies = [
        Policy(
            title=f"Test Policy {i}",
            content=f"Content for test policy {i}",
            source_url=f"https://example.com/policy/{i}",
            department="Radiology",
            last_updated="2023-01-01"
        )
        for i in range(5)
    ]
    
    for policy in policies:
        await policy_repository.create(policy)
    
    # Test listing all policies
    all_policies = await policy_repository.get_all()
    assert len(all_policies) >= 5
    
    # Test filtering policies
    filtered_policies = await policy_repository.filter_by_department("Radiology")
    assert len(filtered_policies) >= 5
    
    # Test full-text search
    search_results = await policy_repository.full_text_search("test policy")
    assert len(search_results) > 0


@pytest.mark.asyncio
async def test_hybrid_search(policy_repository):
    """Test the hybrid search functionality (combining vector and keyword search)."""
    # Create a policy with multiple chunks
    policy = Policy(
        title="Hybrid Search Test Policy",
        content="This is a specialized radiology protocol for contrast administration. " * 10,
        source_url="https://example.com/policy/contrast",
        department="Radiology",
        last_updated="2023-01-01"
    )
    
    created_policy = await policy_repository.create(policy)
    
    # Chunk and embed
    chunks = chunk_text(created_policy.content, chunk_size=100, chunk_overlap=20)
    for i, chunk_text in enumerate(chunks):
        embedding = await embed_text(chunk_text)
        chunk = PolicyChunk(
            policy_id=created_policy.id,
            chunk_index=i,
            content=chunk_text,
            embedding=embedding
        )
        await policy_repository.create_chunk(chunk)
    
    # Perform hybrid search
    query = "contrast protocol"
    results = await policy_repository.hybrid_search(
        query=query,
        vector_weight=0.7,  # 70% vector search, 30% keyword search
        limit=5,
        similarity_threshold=0.6
    )
    
    assert len(results) > 0
    # Results should be sorted by combined score
    if len(results) > 1:
        assert results[0].combined_score >= results[1].combined_score


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
    
    finally:
        # Cleanup
        conn = await asyncpg.connect(ADMIN_POSTGRES_DSN)
        await conn.execute(f"DROP DATABASE IF EXISTS {temp_db_name}")
        await conn.close()