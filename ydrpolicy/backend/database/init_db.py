import asyncio
from typing import Optional
from urllib.parse import urlparse

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

from ydrpolicy.backend.database.models import Base, create_search_vector_trigger
from ydrpolicy.backend.config import config
from ydrpolicy.backend.logger import logger
from ydrpolicy.backend.utils.paths import ensure_directories


async def create_database(db_url: str) -> bool:
    """
    Create the database if it doesn't exist.
    
    Args:
        db_url: The database URL in SQLAlchemy format.
        
    Returns:
        bool: True if database was created, False if it already existed.
    """
    # Parse the database URL to get components
    if db_url.startswith('postgresql+asyncpg://'):
        # Remove the driver prefix for asyncpg
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip('/')
    
    # Construct the postgres admin URL (no specific database)
    admin_url = f"{parsed.scheme}://{parsed.netloc}/postgres"
    
    logger.info(f"Checking if database '{db_name}' exists...")
    
    try:
        # Connect to the postgres database
        conn = await asyncpg.connect(admin_url)
        
        # Check if the database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )
        
        if not result:
            logger.info(f"Creating database '{db_name}'...")
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            await conn.close()
            return True
        else:
            logger.info(f"Database '{db_name}' already exists.")
            await conn.close()
            return False
            
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise


async def create_extension(engine: AsyncEngine, extension_name: str) -> None:
    """
    Create a PostgreSQL extension if it doesn't exist.
    
    Args:
        engine: SQLAlchemy AsyncEngine object.
        extension_name: Name of the extension to create.
    """
    logger.info(f"Creating extension '{extension_name}' if it doesn't exist...")
    
    async with engine.begin() as conn:
        await conn.execute(
            text(f"CREATE EXTENSION IF NOT EXISTS {extension_name}")
        )


async def create_tables(engine: AsyncEngine) -> None:
    """
    Create all database tables defined in the models.
    
    Args:
        engine: SQLAlchemy AsyncEngine object.
    """
    logger.info("Creating database tables...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create triggers for search vectors
    logger.info("Creating search vector triggers...")
    async with engine.connect() as conn:
        await conn.execute(text(create_search_vector_trigger()))
        await conn.commit()


async def init_db(db_url: Optional[str] = None) -> None:
    """
    Initialize the database with all required tables and extensions.
    
    Args:
        db_url: Optional database URL. If not provided, uses the URL from settings.
    """
    # Ensure all required directories exist
    ensure_directories()
    
    if db_url is None:
        db_url = str(config.DATABASE.DATABASE_URL)
    
    # Make sure the database exists
    await create_database(db_url)
    
    # Create engine to connect to the database
    engine = create_async_engine(db_url)
    
    try:
        # Create required PostgreSQL extensions
        await create_extension(engine, "vector")
        
        # Create all tables
        await create_tables(engine)
        
        logger.success("Database initialization completed successfully.")
    finally:
        await engine.dispose()


async def drop_db(db_url: Optional[str] = None) -> None:
    """
    Drop the database. USE WITH CAUTION!
    
    This is primarily for testing or resetting the development environment.
    
    Args:
        db_url: Optional database URL. If not provided, uses the URL from settings.
    """
    if db_url is None:
        db_url = str(config.DATABASE.DATABASE_URL)
    
    # Parse the database URL to get components
    if db_url.startswith('postgresql+asyncpg://'):
        # Remove the driver prefix for asyncpg
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip('/')
    
    # Construct the postgres admin URL (no specific database)
    admin_url = f"{parsed.scheme}://{parsed.netloc}/postgres"
    
    logger.warning(f"Dropping database '{db_name}'... THIS WILL DELETE ALL DATA!")
    
    try:
        # Connect to the postgres database
        conn = await asyncpg.connect(admin_url)
        
        # Force disconnect all active connections to the database
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
            AND pid <> pg_backend_pid()
        """)
        
        # Drop the database
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await conn.close()
        
        logger.success(f"Database '{db_name}' dropped successfully.")
    except Exception as e:
        logger.error(f"Error dropping database: {str(e)}")
        raise


if __name__ == "__main__":
    # This allows running the script directly for database initialization
    asyncio.run(init_db())