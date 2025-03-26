"""
Shared fixtures for database tests.
"""
import pytest
import asyncio
import uuid
from typing import Generator, AsyncGenerator

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from ydrpolicy.backend.database.models import Base
from ydrpolicy.backend.database.repository.policies import PolicyRepository
from ydrpolicy.backend.database.repository.users import UserRepository

# PostgreSQL connection details - customize these for your environment
PG_USER = "pouria"
PG_PASSWORD = ""  # Empty password
PG_HOST = "localhost"
PG_PORT = "5432"
PG_BASE_DB = "postgres"  # Default database for initial connection

# Format: postgresql://user:password@host:port/dbname
# For empty password: postgresql://user@host:port/dbname
PG_DSN = f"postgresql://{PG_USER}{':{}'.format(PG_PASSWORD) if PG_PASSWORD else ''}@{PG_HOST}:{PG_PORT}"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for pytest-asyncio."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db_name() -> str:
    """Generate a unique test database name."""
    return f"test_ydrpolicy_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def test_db_url(test_db_name) -> str:
    """Generate the test database URL."""
    return f"{PG_DSN}/{test_db_name}"


@pytest.fixture(scope="session")
def admin_db_url() -> str:
    """Generate the admin database URL."""
    return f"{PG_DSN}/{PG_BASE_DB}"


@pytest.fixture(scope="session")
async def postgres_connection(test_db_name, admin_db_url) -> AsyncGenerator:
    """Create a test database and yield a connection to it."""
    # Connect to the postgres database to create our test database
    conn = await asyncpg.connect(admin_db_url)
    
    # Ensure the test database doesn't exist (in case of previous failed tests)
    await conn.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    
    # Create a fresh test database
    await conn.execute(f"CREATE DATABASE {test_db_name}")
    await conn.close()
    
    # Now connect to our test database
    test_conn = await asyncpg.connect(f"{PG_DSN}/{test_db_name}")
    
    # Create the pgvector extension
    await test_conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    yield test_conn
    
    # Cleanup
    await test_conn.close()
    
    # Reconnect to postgres to drop the test database
    conn = await asyncpg.connect(admin_db_url)
    await conn.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    await conn.close()


@pytest.fixture(scope="session")
async def db_engine(postgres_connection, test_db_url):
    """Create a SQLAlchemy engine connected to the test database."""
    engine = create_async_engine(test_db_url)
    
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