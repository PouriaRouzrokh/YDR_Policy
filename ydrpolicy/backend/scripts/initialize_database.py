#!/usr/bin/env python
"""
Initialize the Yale Radiology Policies RAG database.

This script:
1. Creates the database if it doesn't exist
2. Creates necessary extensions (pgvector)
3. Creates all database tables
4. Sets up search vector triggers
5. Initializes Alembic if needed

Usage:
    python -m ydrpolicy.scripts.initialize_database [--drop] [--db_url DB_URL]

Options:
    --drop      Drop the database before initializing (CAUTION: destroys all data)
    --db_url    Custom database URL (default: from config)
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add the parent directory to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from ydrpolicy.backend.database.init_db import drop_db, init_db
from ydrpolicy.backend.database.migrations.init_alembic import \
    create_alembic_config
from ydrpolicy.backend.logger import logger
from ydrpolicy.backend.config import config


async def run_migration():
    """Run Alembic migrations to latest version."""
    import subprocess
    from pathlib import Path
    
    migrations_dir = Path(__file__).parent.parent / "backend" / "database" / "migrations"
    
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=migrations_dir,
            check=True
        )
        logger.info("Database migrations applied successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error applying migrations: {e}")
        raise


async def main(args):
    """Main function to initialize the database."""
    db_url = args.db_url or str(config.DATABASE.DATABASE_URL)
    
    logger.info(f"Initializing database at: {db_url}")
    
    if args.drop:
        logger.warning("DROPPING DATABASE! All data will be lost!")
        await drop_db(db_url)
    
    # Initialize the database
    await init_db(db_url)
    
    # Create Alembic configuration if it doesn't exist
    create_alembic_config()
    
    # Run migrations to latest version
    await run_migration()
    
    logger.info("Database initialization complete!")


if __name__ == "__main__":
    logger.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Initialize the Yale Radiology Policies RAG database")
    parser.add_argument("--drop", action="store_true", help="Drop the database before initializing")
    parser.add_argument("--db_url", help="Custom database URL")
    
    args = parser.parse_args()
    
    asyncio.run(main(args))