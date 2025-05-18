# backend/database.py
"""
This module handles database initialization and session management for the application.
It includes functions to create the SQLAlchemy engine, session factory, tables, and populate initial data.
"""
import structlog
from sqlalchemy import create_engine, inspect, func, text
from sqlalchemy.orm import sessionmaker
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

import config as app_config_module 
from models import Base, User, UserRole 
from utils import _hash_password, _validate_password_complexity

logger = structlog.get_logger(__name__)

engine = None
SessionLocal = None

def init_engine():
    """
    Initializes and returns the SQLAlchemy database engine.

    Reads database configuration from the application config and creates an engine with connection pooling.
    Also instruments the engine for OpenTelemetry.
    """
    global engine
    current_config = app_config_module.config
    if not current_config.DATABASE_URL:
        logger.critical("DATABASE_URL environment variable is not set. Database engine cannot be initialized.")
        raise RuntimeError("DATABASE_URL is not set.")
    
    try:
        engine = create_engine(
            current_config.DATABASE_URL,
            pool_size=current_config.DB_POOL_SIZE,
            max_overflow=current_config.DB_MAX_OVERFLOW,
            pool_recycle=current_config.DB_POOL_RECYCLE,
            echo=current_config.SQLALCHEMY_ECHO
        )
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy engine created and instrumented successfully.")
        return engine
    except Exception as e:
        logger.critical(f"Failed to create SQLAlchemy engine: {e}", exc_info=True)
        raise RuntimeError(f"Database engine initialization failed: {e}")

def init_sessionlocal():
    """
    Initializes and returns the SQLAlchemy sessionmaker factory.

    If the engine is not already initialized, it calls `init_engine`.
    Creates a configured session factory for database interactions.
    """
    global SessionLocal, engine
    if engine is None:
        init_engine()
    
    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("SQLAlchemy SessionLocal factory created successfully.")
        return SessionLocal
    except Exception as e:
        logger.critical(f"Failed to create SQLAlchemy SessionLocal factory: {e}", exc_info=True)
        raise RuntimeError(f"Database SessionLocal factory initialization failed: {e}")


def create_tables_db(engine_to_use):
    """
    Creates database tables based on the defined SQLAlchemy models if they do not exist.

    Args:
        engine_to_use: The SQLAlchemy engine to use for table creation.
    """
    logger.info("Attempting to create database tables if they don't exist...")
    try:
        inspector = inspect(engine_to_use)
        existing_tables = inspector.get_table_names()
        
        all_defined_tables_present = True
        for table_name in Base.metadata.tables.keys():
            if table_name not in existing_tables:
                all_defined_tables_present = False
                logger.info(f"Table '{table_name}' is missing.")
                break
        
        if not all_defined_tables_present:
             logger.info("Not all defined tables exist. Creating/updating schema...")
             Base.metadata.create_all(bind=engine_to_use)
             logger.info("Database schema creation/update attempt complete.")
        else:
             logger.info(f"All defined tables ({len(Base.metadata.tables)}) seem to exist. Skipping schema creation.")
    except Exception as e:
        logger.error(f"Error during database schema check/creation: {e}", exc_info=True)
        raise

def populate_initial_data_db(session_factory):
    """
    Populates initial data, such as the default admin user, if no users exist in the database.

    Args:
        session_factory: The SQLAlchemy session factory to create sessions.
    """
    logger.info("Checking if initial data population is needed...")
    db_session = session_factory()
    current_config = app_config_module.config
    try:
        user_count = db_session.query(func.count(User.id)).scalar()
        if user_count == 0:
            logger.info("No users found. Populating initial admin data...")
            admin_username = current_config.INITIAL_ADMIN_USERNAME
            admin_email = current_config.INITIAL_ADMIN_EMAIL
            admin_password = current_config.INITIAL_ADMIN_PASSWORD

            if not admin_password:
                 logger.critical("INITIAL_ADMIN_PASSWORD env var not set. Cannot create initial admin.")
                 return

            try:
                _validate_password_complexity(admin_password)
            except ValueError as e:
                 logger.critical(f"Initial admin password complexity error: {e}. Cannot create admin.")
                 return

            hashed_password = _hash_password(admin_password)
            admin_user = User(
                username=admin_username, email=admin_email.lower(),
                password_hash=hashed_password, role=UserRole.ADMIN,
                is_active=True, email_verified=True
            )
            db_session.add(admin_user)
            db_session.commit()
            logger.info(f"Initial admin user '{admin_user.username}' created.")
        else:
            logger.info(f"DB has {user_count} users. Skipping initial data population.")
    except Exception as e:
        logger.error(f"Error during initial data population: {e}", exc_info=True)
        db_session.rollback()
    finally:
        db_session.close()

def initialize_database():
    """
    Performs the complete database initialization process.
    Initializes the engine, session factory, creates tables, and populates initial data.
    """
    global engine, SessionLocal
    logger.info("Initializing database...")
    try:
        current_engine = init_engine()
        current_session_local = init_sessionlocal()

        with current_engine.connect() as connection: # Test connection
            connection.execute(text("SELECT 1")) # Make sure connection is live
            logger.info("Database connection successful.")
        
        create_tables_db(current_engine)
        populate_initial_data_db(current_session_local)
        logger.info("Database initialization process complete.")
    except Exception as e:
        logger.critical(f"Full database initialization failed: {e}", exc_info=True)
        raise RuntimeError(f"Full database initialization failed: {e}")
