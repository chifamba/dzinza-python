# backend/database.py
import structlog
from sqlalchemy import create_engine, inspect, func
from sqlalchemy.orm import sessionmaker
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from .config import config
from .models import Base, User, UserRole # Import Base and models needed for seeding
from .utils import _hash_password, _validate_password_complexity # For seeding admin

logger = structlog.get_logger(__name__)

engine = None
SessionLocal = None

def init_engine():
    """Initializes the SQLAlchemy engine."""
    global engine
    if not config.DATABASE_URL:
        logger.critical("DATABASE_URL environment variable is not set. Database engine cannot be initialized.")
        raise RuntimeError("DATABASE_URL is not set.")
    
    try:
        engine = create_engine(
            config.DATABASE_URL,
            pool_size=config.DB_POOL_SIZE,
            max_overflow=config.DB_MAX_OVERFLOW,
            pool_recycle=config.DB_POOL_RECYCLE,
            echo=config.SQLALCHEMY_ECHO
        )
        # Instrument the engine for OpenTelemetry
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy engine created and instrumented successfully.")
        return engine
    except Exception as e:
        logger.critical(f"Failed to create SQLAlchemy engine: {e}", exc_info=True)
        raise RuntimeError(f"Database engine initialization failed: {e}")

def init_sessionlocal():
    """Initializes the SQLAlchemy SessionLocal factory."""
    global SessionLocal, engine
    if engine is None:
        init_engine() # Ensure engine is initialized first
    
    try:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("SQLAlchemy SessionLocal factory created successfully.")
        return SessionLocal
    except Exception as e:
        logger.critical(f"Failed to create SQLAlchemy SessionLocal factory: {e}", exc_info=True)
        raise RuntimeError(f"Database SessionLocal factory initialization failed: {e}")


def create_tables_db(engine_to_use):
    """Creates database tables if they don't exist."""
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
    """Populates initial admin data if no users exist."""
    logger.info("Checking if initial data population is needed...")
    db_session = session_factory()
    try:
        user_count = db_session.query(func.count(User.id)).scalar()
        if user_count == 0:
            logger.info("No users found. Populating initial admin data...")
            admin_username = config.INITIAL_ADMIN_USERNAME
            admin_email = config.INITIAL_ADMIN_EMAIL
            admin_password = config.INITIAL_ADMIN_PASSWORD

            if not admin_password:
                 logger.critical("INITIAL_ADMIN_PASSWORD environment variable is not set. Cannot create initial admin user.")
                 return

            try:
                _validate_password_complexity(admin_password)
            except ValueError as e:
                 logger.critical(f"Initial admin password does not meet complexity requirements: {e}. Cannot create initial admin user.")
                 return

            hashed_password = _hash_password(admin_password)
            admin_user = User(
                username=admin_username,
                email=admin_email.lower(),
                password_hash=hashed_password,
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True
            )
            db_session.add(admin_user)
            db_session.commit()
            logger.info(f"Initial admin user '{admin_user.username}' created successfully.")
        else:
            logger.info(f"Database already contains {user_count} users. Skipping initial admin data population.")
    except Exception as e: # Catch any error during population
        logger.error(f"Error during initial data population: {e}", exc_info=True)
        db_session.rollback()
    finally:
        db_session.close()

def initialize_database():
    """Initializes the database: creates engine, session, tables, and populates initial data."""
    global engine, SessionLocal # To ensure they are assigned
    logger.info("Initializing database...")
    try:
        current_engine = init_engine() # Get the initialized engine
        current_session_local = init_sessionlocal() # Get the initialized SessionLocal

        # Test connection
        with current_engine.connect() as connection:
            logger.info("Database connection successful.")
        
        create_tables_db(current_engine)
        populate_initial_data_db(current_session_local)
        logger.info("Database initialization process complete.")
    except Exception as e:
        logger.critical(f"Full database initialization failed: {e}", exc_info=True)
        raise RuntimeError(f"Full database initialization failed: {e}")

# Call initialization when this module is imported, so SessionLocal and engine are available.
# This should be called by the main app.py during its setup.
# For now, let's assume it's called explicitly by app.py.
# init_engine()
# init_sessionlocal()
