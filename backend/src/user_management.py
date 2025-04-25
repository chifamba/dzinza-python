# backend/src/user_management.py
import logging
from sqlalchemy.orm import Session
# Corrected import path for the User model
from app.models.user import User # Changed from from src.models.user import User
from src.audit_log import log_audit
from src.encryption import hash_password, verify_password # Assuming encryption functions are here

# Define valid roles if not imported from elsewhere
VALID_ROLES = ['user', 'admin']

class UserManagement:
    """Handles user-related operations like registration and login."""

    def __init__(self, db_session_factory, audit_log_file):
        # Store the session factory, not a session instance
        self.db_session_factory = db_session_factory
        self.audit_log_file = audit_log_file
        logging.info("UserManagement initialized.")

    def _get_db(self) -> Session:
        """Helper to get a DB session from the factory."""
        if not self.db_session_factory:
            logging.error("Database session factory not initialized in UserManagement.")
            # In a service layer, raising an exception might be better than aborting
            raise ConnectionError("Database connection not available.")
        return self.db_session_factory()

    def register_user(self, username, password, role='user') -> Optional[User]:
        """Registers a new user."""
        if role not in VALID_ROLES:
            logging.warning(f"Attempted to register user '{username}' with invalid role: {role}")
            log_audit(self.audit_log_file, 'system', 'registration_failed', f'Invalid role provided for user {username}')
            return None # Or raise a specific error

        db = None # Initialize db to None
        try:
            db = self._get_db() # Get a new session
            # Check if user already exists
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                logging.warning(f"Registration failed: Username '{username}' already exists.")
                log_audit(self.audit_log_file, username, 'registration_failed', 'Username already exists')
                return None # Or raise a specific error (e.g., Conflict)

            hashed_pw = hash_password(password) # Hash the password
            new_user = User(username=username, password_hash=hashed_pw, role=role)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            logging.info(f"User '{username}' registered successfully with role '{role}'.")
            log_audit(self.audit_log_file, username, 'registration_success', f'User {username} registered')
            return new_user
        except Exception as e:
            if db: db.rollback() # Rollback on error
            logging.error(f"Error during user registration for '{username}': {e}", exc_info=True)
            log_audit(self.audit_log_file, username, 'registration_failed', f'Error: {e}')
            return None # Indicate failure
        finally:
            if db: db.close() # Close the session

    def login_user(self, username, password) -> Optional[User]:
        """Logs in a user."""
        db = None # Initialize db to None
        try:
            db = self._get_db() # Get a new session
            user = db.query(User).filter(User.username == username).first()
            if user and verify_password(password, user.password_hash):
                logging.info(f"User '{username}' logged in successfully.")
                # Audit logging for login success is handled in main.py after session is set
                return user
            else:
                logging.warning(f"Login failed for user '{username}': Invalid credentials.")
                log_audit(self.audit_log_file, username, 'login_failed', 'Invalid credentials')
                return None # Indicate failure
        except Exception as e:
            # No rollback needed for read operation, but log the error
            logging.error(f"Error during user login for '{username}': {e}", exc_info=True)
            log_audit(self.audit_log_file, username, 'login_failed', f'Error: {e}')
            return None # Indicate failure
        finally:
            if db: db.close() # Close the session

    # Add other user management methods as needed (e.g., update password, delete user)
    # Ensure each method gets and closes its own session if not using a request-scoped session pattern
