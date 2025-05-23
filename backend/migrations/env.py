from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from models import Base  # Import Base from your application's models
target_metadata = Base.metadata  # Set target_metadata for autogenerate

# Import the application's config to get the database URL
from config import config as app_config # Assuming your Flask app's config is named 'config'
import os

# Retrieve the actual database URL from the application's config or environment
actual_db_url = app_config.DATABASE_URL
if not actual_db_url:
    # Fallback if app_config.DATABASE_URL was None (e.g. import timing or not set)
    actual_db_url = os.getenv('DATABASE_URL') 
    if not actual_db_url:
        raise ValueError("DATABASE_URL is not set in the application configuration or environment.")

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use the actual_db_url fetched from app_config or environment
    context.configure(
        url=actual_db_url,  # Use the correct database URL
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create engine configuration dictionary, overriding the URL with actual_db_url
    # This ensures that the engine connects to the database specified in the app's config
    engine_config_dict = config.get_section(config.config_ini_section, {})
    engine_config_dict['sqlalchemy.url'] = actual_db_url # Use the correct database URL

    connectable = engine_from_config(
        engine_config_dict,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
