import os
import logging
import argparse
import subprocess
from pathlib import Path

from ydrpolicy.backend.logger import logger


def create_alembic_config():
    """
    Create the Alembic configuration files if they don't exist.
    
    This initializes the alembic directory structure and configuration.
    """
    # Set up the migrations directory path
    base_dir = Path(__file__).parent
    
    # Check if alembic.ini exists
    alembic_ini = base_dir / "alembic.ini"
    if alembic_ini.exists():
        logger.info("Alembic config already exists.")
        return
    
    # Create the migrations directory if it doesn't exist
    migrations_dir = base_dir
    os.makedirs(migrations_dir, exist_ok=True)
    
    # Run alembic init
    logger.info("Initializing Alembic...")
    try:
        subprocess.run(
            ["alembic", "init", "versions"],
            cwd=migrations_dir,
            check=True
        )
        logger.info("Alembic initialized successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error initializing Alembic: {e}")
        raise
    
    # Update alembic.ini
    alembic_ini = migrations_dir / "alembic.ini"
    with open(alembic_ini, "r") as f:
        config = f.read()
    
    # Replace the SQLAlchemy URL with our placeholder
    config = config.replace(
        "sqlalchemy.url = driver://user:pass@localhost/dbname",
        "sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/ydrpolicy"
    )
    
    with open(alembic_ini, "w") as f:
        f.write(config)
    
    # Update env.py
    env_py = migrations_dir / "versions" / "env.py"
    with open(env_py, "r") as f:
        env_content = f.read()
    
    # Add import for AsyncEngine and our models
    env_content = env_content.replace(
        "from sqlalchemy import pool",
        "from sqlalchemy import pool\n"
        "from sqlalchemy.ext.asyncio import async_engine_from_config\n"
        "\n"
        "from ydrpolicy.backend.database.models import Base"
    )
    
    # Update target_metadata
    env_content = env_content.replace(
        "target_metadata = None",
        "target_metadata = Base.metadata"
    )
    
    # Update run_migrations_online for async support
    run_migrations_online = """
def run_migrations_online() -> None:
    \"\"\"Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    \"\"\"
    configuration = config.get_section(config.config_ini_section)
    url = configuration["sqlalchemy.url"]
    
    # Use AsyncEngine for creating the connection
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Use standard engine for Alembic migrations (not async)
    sync_connectable = create_engine(url)
    
    with sync_connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
"""
    
    # Replace the run_migrations_online function
    import re
    env_content = re.sub(
        r"def run_migrations_online\(\) -> None:.*?end run_migrations_online",
        run_migrations_online,
        env_content,
        flags=re.DOTALL
    )
    
    with open(env_py, "w") as f:
        f.write(env_content)
    
    logger.info("Alembic configuration updated.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Initialize Alembic configuration")
    args = parser.parse_args()
    
    create_alembic_config()