"""
Tests for database connection and setup.
"""
import pytest
from sqlalchemy import text
import asyncpg

from ydrpolicy.backend.database.init_db import init_db
from ydrpolicy.backend.database.engine import get_async_engine, get_async_session
from ydrpolicy.backend.config import config
from ydrpolicy.backend.logger import logger


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
async def test_init_db_script(test_db_name, admin_db_url, test_db_url):
    """Test the init_db script that creates the database from scratch."""
    # Use a completely new database name
    temp_db_name = f"temp_ydrpolicy_{test_db_name}"
    temp_db_url = f"{admin_db_url.rsplit('/', 1)[0]}/{temp_db_name}"
    
    # Create a new database
    conn = await asyncpg.connect(admin_db_url)
    await conn.execute(f"DROP DATABASE IF EXISTS {temp_db_name}")
    await conn.execute(f"CREATE DATABASE {temp_db_name}")
    await conn.close()
    
    try:
        # Initialize the database using our init_db function
        await init_db(temp_db_url)
        
        # Connect to the initialized database and verify it's set up correctly
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
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
        conn = await asyncpg.connect(admin_db_url)
        await conn.execute(f"DROP DATABASE IF EXISTS {temp_db_name}")
        await conn.close()