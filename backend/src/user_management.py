# backend/src/user_management.py
import logging
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from typing import Optional, List, Dict, Any

# Assuming User model and audit log function are correctly imported/defined
try:
    from .models.user import User
    from .audit_log import log_audit
    # Import encryption functions if deriving keys from passwords here
    # from .encryption import derive_key_from_password, generate_salt, SALT_SIZE
except ImportError as e:
    logging.critical(f"Failed to import necessary modules in user_management: {e}")
    raise

# --- Constants ---
VALID_ROLES = ["basic", "editor", "admin"] # Define valid roles

class UserManagement:
    """Handles user creation, login, role management, etc."""

    def __init__(self, db_session: Session, audit_log_path: str):
        """
        Initializes UserManagement.

        Args:
            db_session: The SQLAlchemy session object.
            audit_log_path: Path to the audit log file.
        """
        if not isinstance(db_session, Session):
            raise TypeError("db_session must be a SQLAlchemy Session object.")
        self.db = db_session
        self.audit_log_path = audit_log_path
        logging.info("UserManagement initialized.")

    def _hash_password(self, password: str) -> bytes:
        """Hashes a password using bcrypt."""
        if not isinstance(password, str) or not password:
            raise ValueError("Password must be a non-empty string.")
        # Generate salt and hash the password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        # Return the full hash (includes salt) encoded in base64 for storage
        return base64.b64encode(hashed_password)

    def _verify_password(self, stored_hash_b64: bytes, provided_password: str) -> bool:
        """Verifies a provided password against a stored bcrypt hash (base64 encoded)."""
        if not stored_hash_b64 or not isinstance(stored_hash_b64, bytes):
            logging.warning("Attempted password verification with invalid stored hash.")
            return False
        if not provided_password or not isinstance(provided_password, str):
             logging.warning("Attempted password verification with invalid provided password type.")
             return False
        try:
            # Decode the base64 stored hash before checking
            stored_hash = base64.b64decode(stored_hash_b64)
            return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash)
        except ValueError as e:
            # Handle potential base64 decoding errors
            logging.error(f"Error decoding stored password hash: {e}")
            return False
        except Exception as e:
            # Catch other potential errors during checkpw
            logging.error(f"Unexpected error during password verification: {e}", exc_info=True)
            return False


    def create_user(self, username: str, password: str, role: str = "basic") -> Optional[User]:
        """Creates a new user with a hashed password."""
        if role not in VALID_ROLES:
            logging.warning(f"Attempted to create user '{username}' with invalid role '{role}'.")
            raise ValueError(f"Invalid role specified. Valid roles are: {', '.join(VALID_ROLES)}")
        if not username or not isinstance(username, str):
             raise ValueError("Username must be a non-empty string.")
        if not password or not isinstance(password, str):
             raise ValueError("Password must be a non-empty string.")

        # Check if username already exists
        existing_user = self.db.query(User).filter(User.username == username).first()
        if existing_user:
            logging.warning(f"Attempted to create user with existing username '{username}'.")
            log_audit(self.audit_log_path, "system", "create_user_failed", f"username '{username}' already exists")
            return None # Indicate failure due to existing user

        try:
            hashed_password_b64 = self._hash_password(password)
            new_user = User(
                username=username,
                password_hash_b64=hashed_password_b64, # Store the base64 encoded hash
                role=role
            )
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            logging.info(f"User '{username}' created successfully with role '{role}'.")
            log_audit(self.audit_log_path, "system", "create_user_success", f"user '{username}' created with role '{role}'")
            return new_user
        except SQLAlchemyError as e:
            self.db.rollback()
            logging.error(f"Database error creating user '{username}': {e}", exc_info=True)
            log_audit(self.audit_log_path, "system", "create_user_failed", f"database error for user '{username}': {e}")
            return None
        except ValueError as ve: # Catch hashing errors
             logging.error(f"Error hashing password for user '{username}': {ve}")
             log_audit(self.audit_log_path, "system", "create_user_failed", f"password error for user '{username}': {ve}")
             return None


    def login_user(self, username: str, password: str) -> Optional[User]:
        """Authenticates a user and returns the User object if successful."""
        if not username or not password:
            return None
        try:
            user = self.db.query(User).filter(User.username == username).first()
            if user and self._verify_password(user.password_hash_b64, password):
                logging.info(f"User '{username}' logged in successfully.")
                log_audit(self.audit_log_path, username, "login_success", "User logged in")
                return user
            else:
                logging.warning(f"Failed login attempt for username '{username}'.")
                log_audit(self.audit_log_path, username, "login_failed", "Invalid username or password")
                return None
        except NoResultFound:
            logging.warning(f"Failed login attempt: Username '{username}' not found.")
            log_audit(self.audit_log_path, username, "login_failed", "Username not found")
            return None
        except SQLAlchemyError as e:
            logging.error(f"Database error during login for user '{username}': {e}", exc_info=True)
            # Do not log specific DB error details to audit log for security
            log_audit(self.audit_log_path, username, "login_failed", "Database error during login attempt")
            return None
        except Exception as e:
             # Catch potential errors in _verify_password
             logging.error(f"Unexpected error during login for user '{username}': {e}", exc_info=True)
             log_audit(self.audit_log_path, username, "login_failed", "Unexpected error during login attempt")
             return None

    def change_user_role(self, username_to_change: str, new_role: str, performing_user: str) -> bool:
        """Changes the role of a user."""
        if new_role not in VALID_ROLES:
            logging.warning(f"User '{performing_user}' attempted to set invalid role '{new_role}' for user '{username_to_change}'.")
            log_audit(self.audit_log_path, performing_user, "change_role_failed", f"invalid role '{new_role}' for user '{username_to_change}'")
            return False

        try:
            user = self.db.query(User).filter(User.username == username_to_change).first()
            if not user:
                logging.warning(f"User '{performing_user}' attempted to change role for non-existent user '{username_to_change}'.")
                log_audit(self.audit_log_path, performing_user, "change_role_failed", f"user '{username_to_change}' not found")
                return False

            old_role = user.role
            user.role = new_role
            self.db.commit()
            logging.info(f"User '{performing_user}' changed role of user '{username_to_change}' from '{old_role}' to '{new_role}'.")
            log_audit(self.audit_log_path, performing_user, "change_role_success", f"changed role for user '{username_to_change}' from '{old_role}' to '{new_role}'")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logging.error(f"Database error changing role for user '{username_to_change}': {e}", exc_info=True)
            log_audit(self.audit_log_path, performing_user, "change_role_failed", f"database error for user '{username_to_change}': {e}")
            return False

    def delete_user(self, username_to_delete: str, performing_user: str) -> bool:
        """Deletes a user."""
        # Add checks: prevent deleting self, prevent deleting last admin?
        if username_to_delete == performing_user:
             logging.warning(f"User '{performing_user}' attempted to delete themselves.")
             log_audit(self.audit_log_path, performing_user, "delete_user_failed", "attempted to delete self")
             return False

        try:
            user = self.db.query(User).filter(User.username == username_to_delete).first()
            if not user:
                logging.warning(f"User '{performing_user}' attempted to delete non-existent user '{username_to_delete}'.")
                log_audit(self.audit_log_path, performing_user, "delete_user_failed", f"user '{username_to_delete}' not found")
                return False

            # Add check for last admin if necessary
            # if user.role == 'admin':
            #     admin_count = self.db.query(User).filter(User.role == 'admin').count()
            #     if admin_count <= 1:
            #         logging.warning(f"User '{performing_user}' attempted to delete the last admin '{username_to_delete}'.")
            #         log_audit(self.audit_log_path, performing_user, "delete_user_failed", f"attempted to delete last admin '{username_to_delete}'")
            #         return False

            self.db.delete(user)
            self.db.commit()
            logging.info(f"User '{performing_user}' deleted user '{username_to_delete}'.")
            log_audit(self.audit_log_path, performing_user, "delete_user_success", f"deleted user '{username_to_delete}'")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logging.error(f"Database error deleting user '{username_to_delete}': {e}", exc_info=True)
            log_audit(self.audit_log_path, performing_user, "delete_user_failed", f"database error for user '{username_to_delete}': {e}")
            return False

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Changes a user's password after verifying the old one."""
        if not new_password or not isinstance(new_password, str):
             raise ValueError("New password must be a non-empty string.")

        try:
            user = self.db.query(User).filter(User.username == username).first()
            if user and self._verify_password(user.password_hash_b64, old_password):
                user.password_hash_b64 = self._hash_password(new_password)
                self.db.commit()
                logging.info(f"Password changed successfully for user '{username}'.")
                log_audit(self.audit_log_path, username, "change_password_success", "Password changed")
                return True
            else:
                logging.warning(f"Password change failed for user '{username}' due to incorrect old password.")
                log_audit(self.audit_log_path, username, "change_password_failed", "Incorrect old password")
                return False
        except NoResultFound:
             logging.warning(f"Password change failed: User '{username}' not found.")
             log_audit(self.audit_log_path, username, "change_password_failed", "User not found")
             return False
        except SQLAlchemyError as e:
            self.db.rollback()
            logging.error(f"Database error changing password for user '{username}': {e}", exc_info=True)
            log_audit(self.audit_log_path, username, "change_password_failed", "Database error")
            return False
        except ValueError as ve: # Catch hashing errors
             logging.error(f"Error hashing new password for user '{username}': {ve}")
             log_audit(self.audit_log_path, username, "change_password_failed", f"Error hashing new password: {ve}")
             return False


    def get_user_details(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves non-sensitive details for a user."""
        try:
            user = self.db.query(User).filter(User.username == username)\
                .options(load_only(User.id, User.username, User.role, User.created_at)).first() # Select specific fields
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            else:
                return None
        except SQLAlchemyError as e:
            logging.error(f"Database error fetching details for user '{username}': {e}", exc_info=True)
            return None

    def list_all_users(self) -> List[Dict[str, Any]]:
        """Lists all users with non-sensitive details."""
        try:
            users = self.db.query(User)\
                .options(load_only(User.id, User.username, User.role, User.created_at))\
                .order_by(User.username)\
                .all()
            return [
                {
                    "id": u.id,
                    "username": u.username,
                    "role": u.role,
                    "created_at": u.created_at.isoformat() if u.created_at else None
                } for u in users
            ]
        except SQLAlchemyError as e:
            logging.error(f"Database error listing all users: {e}", exc_info=True)
            return []

    def find_user_by_id(self, user_id: int) -> Optional[User]:
         """Finds a user by their ID."""
         try:
             return self.db.query(User).filter(User.id == user_id).first()
         except SQLAlchemyError as e:
             logging.error(f"Database error finding user by ID {user_id}: {e}", exc_info=True)
             return None

    def find_user_by_username(self, username: str) -> Optional[User]:
        """Finds a user by their username."""
        try:
            return self.db.query(User).filter(User.username == username).first()
        except SQLAlchemyError as e:
            # Fixed F541: Added placeholder
            logging.error(f"Database error finding user by username '{username}': {e}", exc_info=True)
            return None

    # --- Add other user management methods as needed ---
    # E.g., password reset functionality, account locking, etc.

