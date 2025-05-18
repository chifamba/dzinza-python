# backend/database.py
from collections.abc import Callable
import threading
from typing import Any, Optional

import structlog
from sqlalchemy import create_engine, inspect, func, text, Enum as SQLAlchemyEnum
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, ProgrammingError
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

import config as app_config_module
# Import the consolidated UserRole and other enums
from models import Base, User, UserRole, PrivacyLevelEnum, MediaTypeEnum, RelationshipTypeEnum
from utils import _hash_password, _validate_password_complexity

logger = structlog.get_logger(__name__)

# --- Thread-Safe Singleton Engine and Session Factory ---
# These locks are for ensuring singletons WITHIN a single process.
_engine: Optional[Engine] = None
_session_factory: Optional[scoped_session] = None 
_engine_lock = threading.Lock()
_session_factory_lock = threading.Lock()

# --- Database Initialization Global Advisory Lock ID ---
# This ID must be unique across your application for this specific locking purpose.
DB_OVERALL_INIT_ADVISORY_LOCK_ID = 12345 


def _create_actual_engine() -> Engine:
    """
    Actually creates and configures the SQLAlchemy engine.
    This function should only be called once per process.
    """
    current_config = app_config_module.config
    if not current_config.DATABASE_URL:
        logger.critical("DATABASE_URL environment variable is not set.")
        raise RuntimeError("DATABASE_URL is not set.")
    
    try:
        engine_instance = create_engine(
            current_config.DATABASE_URL,
            pool_size=current_config.DB_POOL_SIZE,
            max_overflow=current_config.DB_MAX_OVERFLOW,
            pool_recycle=current_config.DB_POOL_RECYCLE,
            echo=False,  # Explicitly disable SQLAlchemy echo
        )
        SQLAlchemyInstrumentor().instrument(engine=engine_instance)
        logger.info("SQLAlchemy engine created and instrumented for this process.")
        return engine_instance
    except Exception as e:
        logger.critical(f"Failed to create SQLAlchemy engine: {e}", exc_info=True)
        raise RuntimeError(f"Database engine initialization failed: {e}") from e

def get_engine() -> Engine:
    """
    Get the singleton SQLAlchemy engine instance for this process, initializing it if necessary.
    This function is thread-safe within the current process.
    
    Returns:
        Engine: The SQLAlchemy engine instance.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:  # Double-checked locking
                _engine = _create_actual_engine()
    return _engine

def _create_actual_session_factory(engine_instance: Engine) -> scoped_session:
    """
    Actually creates and configures the SQLAlchemy scoped session factory.
    This function should only be called once per process.
    
    Args:
        engine_instance: The SQLAlchemy engine to bind the session factory to.
        
    Returns:
        scoped_session: A scoped session factory.
    """
    try:
        session_factory_instance = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=engine_instance)
        )
        logger.info("SQLAlchemy scoped session factory created for this process.")
        return session_factory_instance
    except Exception as e:
        logger.critical(f"Failed to create SQLAlchemy session factory: {e}", exc_info=True)
        raise RuntimeError(f"Database session factory initialization failed: {e}") from e

def get_session_factory() -> scoped_session:
    """
    Get the singleton SQLAlchemy scoped_session factory for this process, initializing it if necessary.
    This function is thread-safe within the current process.
    
    Returns:
        scoped_session: The SQLAlchemy session factory.
    """
    global _session_factory
    if _session_factory is None:
        with _session_factory_lock:
            if _session_factory is None:  # Double-checked locking
                current_engine = get_engine()  # Ensures engine is initialized first for this process
                _session_factory = _create_actual_session_factory(current_engine)
    return _session_factory

def get_db_session() -> Session:
    """
    Get a new database session from the scoped session factory.
    The returned session is managed by scoped_session for thread-safety within the current process.
    
    Returns:
        Session: A new SQLAlchemy session.
    """
    factory = get_session_factory()
    if not factory:
        logger.critical("Session factory not initialized before getting a session.")
        raise RuntimeError("Session factory not initialized.")
    return factory() 

def _create_enum_types_if_not_exist(engine_to_use: Engine) -> None:
    """
    Explicitly creates all ENUM types if they don't already exist in the database.
    If an ENUM type exists, it checks if its labels match the Python definition.
    This function is intended to be called by the single process that holds the global init lock.
    
    Args:
        engine_to_use: The SQLAlchemy engine to use for database operations.
    """
    enum_definitions = [
        (UserRole, "userrole"), 
        (PrivacyLevelEnum, "privacylevelenum"),
        (MediaTypeEnum, "mediatypeenum"),
        (RelationshipTypeEnum, "relationshiptypeenum")
    ]

    # Each ENUM operation is performed in its own connection and transaction block.
    # This is important because CREATE TYPE in PostgreSQL is transactional,
    # and we want to isolate failures.
    for py_enum, sql_type_name in enum_definitions:
        with engine_to_use.connect() as conn: # New connection for each ENUM
            with conn.begin(): # Start a transaction for this ENUM operation
                try:
                    check_sql = text(
                        "SELECT 1 FROM pg_type pt JOIN pg_namespace pn ON pn.oid = pt.typnamespace "
                        "WHERE pt.typname = :type_name AND pn.nspname = 'public'"
                    )
                    type_exists_check = conn.execute(check_sql, {"type_name": sql_type_name}).scalar_one_or_none()
                    py_values = sorted([member.value for member in py_enum]) # Sorted for consistent comparison

                    if type_exists_check:
                        get_labels_sql = text(
                            "SELECT e.enumlabel FROM pg_type t "
                            "JOIN pg_enum e ON t.oid = e.enumtypid "
                            "WHERE t.typname = :type_name ORDER BY e.enumsortorder;"
                        )
                        existing_labels_rows = conn.execute(get_labels_sql, {"type_name": sql_type_name}).fetchall()
                        existing_labels = sorted([row[0] for row in existing_labels_rows]) 

                        if existing_labels == py_values:
                            logger.info(f"ENUM type '{sql_type_name}' exists and its labels match Python enum values. Skipping creation.")
                        else:
                            logger.warning(
                                f"ENUM type '{sql_type_name}' exists but its labels {existing_labels} "
                                f"do NOT match current Python enum values {py_values}. "
                                f"Manual DB migration might be needed."
                            )
                        # Transaction commits automatically if no exception
                        continue # Skip to next enum definition

                    # ENUM type does not exist, create it
                    labels_str = [f"'{e_val}'" for e_val in py_values] 
                    create_sql_command = f"CREATE TYPE {sql_type_name} AS ENUM ({', '.join(labels_str)})"
                    logger.info(f"Attempting to create ENUM type '{sql_type_name}' with labels: {py_values}.")
                    conn.execute(text(create_sql_command))
                    # Transaction commits automatically
                    logger.info(f"ENUM type '{sql_type_name}' created successfully.")

                except (IntegrityError, ProgrammingError) as ie:
                    # Transaction rolls back automatically on exception
                    original_exception = getattr(ie, 'orig', None)
                    pgcode = getattr(original_exception, 'pgcode', None)
                    
                    if pgcode == '42710' or (original_exception and "already exists" in str(original_exception).lower()):
                        logger.warning(f"ENUM type '{sql_type_name}' already exists (DB error: {pgcode or 'N/A'}). Handled.")
                    elif pgcode == '25P02': # in_failed_sql_transaction
                         logger.error(f"Transaction aborted for ENUM '{sql_type_name}'. Prior error likely.", exc_info=False)
                         raise # Re-raise to indicate a problem with the transaction state
                    else:
                        logger.error(f"Database error processing ENUM type {sql_type_name}: {ie}", exc_info=True)
                        raise 
                except Exception as e: 
                    # Transaction rolls back automatically
                    logger.error(f"Unexpected error processing ENUM type {sql_type_name}: {e}", exc_info=True)
                    raise

def populate_initial_data_db(session_factory_instance: scoped_session) -> None:
    """
    Populate initial data into the database if needed.
    Uses pg_try_advisory_xact_lock to ensure only one process/thread populates data.
    This function is intended to be called by the single process that holds the global init lock.
    
    Args:
        session_factory_instance: The SQLAlchemy scoped_session factory to use.
    """
    logger.info("Checking if initial data population is needed...")
    db_session = session_factory_instance() 
    current_config = app_config_module.config
    try:
        # Begin a transaction that will also scope the advisory lock for data population
        with db_session.begin(): 
            # Attempt to acquire a transaction-level advisory lock (ID 42).
            lock_acquired_result = db_session.execute(text("SELECT pg_try_advisory_xact_lock(42)")).scalar_one()
            
            if not lock_acquired_result:
                logger.info("Could not acquire data population advisory lock (ID 42). Another process/thread may be populating. Skipping.")
                return 

            logger.info("Data population advisory lock (ID 42) acquired.")
            user_count = db_session.query(func.count(User.id)).scalar()
            if user_count == 0:
                logger.info("No users found. Populating initial admin user and demo users...")
                admin_username = current_config.INITIAL_ADMIN_USERNAME
                admin_email = current_config.INITIAL_ADMIN_EMAIL
                admin_password = current_config.INITIAL_ADMIN_PASSWORD

                if not admin_password:
                    logger.critical("INITIAL_ADMIN_PASSWORD env var not set. Cannot create initial admin.")
                else:
                    try:
                        _validate_password_complexity(admin_password)
                        hashed_password = _hash_password(admin_password)
                        admin_user = User(
                            username=admin_username, 
                            email=admin_email.lower(),
                            password_hash=hashed_password, 
                            role=UserRole.admin.value,
                            is_active=True, 
                            email_verified=True
                        )
                        db_session.add(admin_user)
                        logger.info(f"Initial admin user '{admin_user.username}' prepared with role '{admin_user.role}'.")
                    except ValueError as e:
                         logger.critical(f"Initial admin password complexity error: {e}. Admin not created.")
                    except Exception as e:
                        logger.error(f"Error preparing admin user: {e}", exc_info=True)

                for i in range(1, 11): 
                    demo_username = f"demo{i:02d}"
                    demo_password = f"{demo_username}_2025" 
                    demo_email = f"{demo_username}@example.com"
                    try:
                        demo_hashed_password = _hash_password(demo_password)
                        demo_user = User(
                            username=demo_username, 
                            email=demo_email.lower(),
                            password_hash=demo_hashed_password, 
                            role=UserRole.user.value,
                            full_name=f"Demo User {i:02d}", 
                            is_active=True, 
                            email_verified=True
                        )
                        db_session.add(demo_user)
                        logger.info(f"Demo user '{demo_user.username}' prepared with role '{demo_user.role}'.")
                    except Exception as e: 
                        logger.error(f"Error preparing demo user {demo_username}: {e}", exc_info=True)
                
                logger.info("Initial admin and demo users prepared for commit.")
            else:
                logger.info(f"Database already has {user_count} users. Skipping initial data population.")
            # Transaction commits here, releasing the pg_try_advisory_xact_lock(42).
        logger.info("Transaction for initial data population (if any) completed.")

    except SQLAlchemyError as e: 
        logger.error(f"SQLAlchemyError during initial data population block: {e}", exc_info=True)
        raise 
    except Exception as e:
        logger.error(f"Unexpected error during initial data population: {e}", exc_info=True)
        raise 
    finally:
        session_factory_instance.remove()


def initialize_database() -> None:
    """
    Initializes the database: creates ENUMs, tables, and populates initial data if needed.
    This function uses a PostgreSQL session-level advisory lock to ensure that across multiple 
    processes (e.g., Gunicorn workers), only one process performs the actual initialization steps.
    Other processes will wait for the lock and then skip if initialization is found to be complete.
    """
    engine = get_engine() # Ensures engine singleton is created for this process
    
    # The connection for the advisory lock must persist for the duration of the lock.
    # The lock is session-level. It's released when the session ends or explicitly.
    with engine.connect() as conn_for_lock:
        try:
            logger.info(f"Attempting to acquire global database initialization lock (ID: {DB_OVERALL_INIT_ADVISORY_LOCK_ID}). This may block if another process holds the lock.")
            # pg_advisory_lock will wait until the lock is available.
            conn_for_lock.execute(text(f"SELECT pg_advisory_lock({DB_OVERALL_INIT_ADVISORY_LOCK_ID})"))
            # If the execute call implicitly started a transaction in a non-autocommit connection, commit it.
            # This ensures the lock is held by the session even if the transaction ends.
            # However, for session-level locks, this commit is more about ending the implicit transaction
            # than about the lock itself, which is session-bound.
            if conn_for_lock.in_transaction():
                 conn_for_lock.commit()

            logger.info(f"Global database initialization lock (ID: {DB_OVERALL_INIT_ADVISORY_LOCK_ID}) acquired by process {threading.get_ident()}.")

            # CRITICAL CHECK: After acquiring the lock, check if initialization is already done.
            # Another process might have completed it while this process was waiting for the lock.
            inspector = inspect(engine) 
            if inspector.has_table("users"):  # Using 'users' table as a sentinel for initialization.
                logger.info("Key table 'users' already exists. Database assumed to be initialized. Skipping further setup by this process.")
                # The lock will be released in the 'finally' block.
                return 

            logger.info("This process (lock holder) will perform database schema setup and initial data population.")
            
            current_session_factory = get_session_factory() # Ensures session factory singleton for this process

            # Step 1: Create ENUM types.
            # _create_enum_types_if_not_exist handles its own connections/transactions.
            logger.info("Ensuring ENUM types exist...")
            _create_enum_types_if_not_exist(engine) 

            # Step 2: Create tables.
            logger.info("Attempting to create database tables (checkfirst=True)...")
            try:
                Base.metadata.create_all(bind=engine, checkfirst=True)
                logger.info("Database tables checked/created successfully.")
            except IntegrityError as ie_create_all:
                # Log detailed info if the specific pg_type error occurs, as it's unusual with checkfirst=True + advisory lock.
                if hasattr(ie_create_all, 'orig') and ie_create_all.orig is not None and "pg_type_typname_nsp_index" in str(ie_create_all.orig):
                    logger.error(
                        f"IntegrityError during create_all related to pg_type_typname_nsp_index. "
                        f"This suggests a type (e.g., for table 'users') already existed when CREATE TABLE was attempted, "
                        f"even though checkfirst=True and global lock are active. Error: {ie_create_all}",
                        exc_info=True
                    )
                    # Perform an immediate re-check to understand the state.
                    if inspector.has_table("users"):
                         logger.warning("Follow-up check: 'users' table DOES exist. checkfirst=True might have an issue or race condition not covered.")
                    else:
                         logger.warning("Follow-up check: 'users' table does NOT exist, but its type seems to. This indicates an inconsistent database state.")
                else:
                    logger.error(f"IntegrityError during Base.metadata.create_all: {ie_create_all}", exc_info=True)
                raise # Re-raise the original error to halt initialization if critical.
            except Exception as e_create_all:
                logger.error(f"Unexpected error during Base.metadata.create_all: {e_create_all}", exc_info=True)
                raise

            # Step 3: Populate initial data.
            # populate_initial_data_db uses its own advisory lock for data population idempotency.
            logger.info("Populating initial data if database is empty...")
            populate_initial_data_db(current_session_factory)
            
            logger.info("Database initialization process completed successfully by this process.")

        except SQLAlchemyError as db_err:
            logger.critical(f"A database error occurred during the initialization process: {db_err}", exc_info=True)
            # The lock should still be released in the finally block if acquired.
            raise # Propagate the error; initialization failed.
        except Exception as e:
            logger.critical(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
            # The lock should still be released in the finally block if acquired.
            raise # Propagate the error; initialization failed.
        finally:
            # Ensure the main advisory lock is released by this process.
            # This must be called on the same connection that acquired the lock.
            logger.info(f"Attempting to release global database initialization lock (ID: {DB_OVERALL_INIT_ADVISORY_LOCK_ID}) by process {threading.get_ident()}.")
            if conn_for_lock and not conn_for_lock.closed:
                conn_for_lock.execute(text(f"SELECT pg_advisory_unlock({DB_OVERALL_INIT_ADVISORY_LOCK_ID})"))
                if conn_for_lock.in_transaction(): # End transaction if one was started by execute
                    conn_for_lock.commit()
                logger.info(f"Global database initialization lock (ID: {DB_OVERALL_INIT_ADVISORY_LOCK_ID}) released by this process.")
            else:
                # This case should ideally not happen if the 'with engine.connect()' block is managed correctly.
                logger.warning(f"Connection for lock (ID: {DB_OVERALL_INIT_ADVISORY_LOCK_ID}) was closed or invalid before explicit unlock could be performed by process {threading.get_ident()}. The lock might be auto-released if session ended.")
            # The connection 'conn_for_lock' is closed automatically when exiting the 'with' statement.
            # If the connection is closed, PostgreSQL automatically releases session-level advisory locks held by that session.
