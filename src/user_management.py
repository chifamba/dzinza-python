# Modify src/user_management.py to add deletion and password reset logic
import uuid
import os
import logging
import secrets # For generating secure tokens
from datetime import datetime, timedelta, timezone # Ensure timezone is imported
# Import User and password functions from their respective modules
from .user import User, VALID_ROLES
from .encryption import hash_password, verify_password
# Use load_data and save_data from db_utils
from .db_utils import load_data, save_data
# Import the audit log function
from .audit_log import log_audit

# Constants for password reset
RESET_TOKEN_EXPIRY_MINUTES = 60

class UserManagement:
    """
    Handles user registration, login, roles, deletion, password reset, and data persistence.
    """
    def __init__(self, users_file_path='data/users.json', audit_log_path='data/audit.log'):
        self.users_file_path = users_file_path
        self.audit_log_path = audit_log_path
        users_dir = os.path.dirname(users_file_path)
        if users_dir:
             os.makedirs(users_dir, exist_ok=True)
        self.users = self._load_users()

    def _load_users(self):
        # (Keep existing _load_users implementation from previous step)
        # It now handles the 'role', 'reset_token', 'reset_token_expiry' fields via User.from_dict
        users_data = load_data(self.users_file_path)
        loaded_users = {}
        if users_data:
            for uid, udata in users_data.items():
                 try:
                     if 'user_id' not in udata: udata['user_id'] = uid
                     user_obj = User.from_dict(udata)
                     loaded_users[uid] = user_obj
                 except (KeyError, ValueError) as e:
                     logging.error(f"Error loading user data for ID {uid}: {e}. Skipping this user.")
                     log_audit(self.audit_log_path, "system", "load_users", f"error - invalid user data for ID {uid}: {e}")
                 except Exception as e:
                     logging.error(f"Error creating User object for ID {uid}: {e}. Skipping this user.")
                     log_audit(self.audit_log_path, "system", "load_users", f"error - creating user object failed for ID {uid}: {e}")
            count = len(loaded_users)
            logging.info(f"Loaded {count} users from {self.users_file_path}")
            # Removed redundant audit log here, covered by save/load actions
            return loaded_users
        else:
            logging.warning(f"No user data found or error loading from {self.users_file_path}. Starting with empty user list.")
            log_audit(self.audit_log_path, "system", "load_users", "warning - file not found or empty/invalid")
            return {}

    def _save_users(self):
        # (Keep existing _save_users implementation from previous step)
        # It now saves the 'role', 'reset_token', 'reset_token_expiry' fields via User.to_dict
        try:
            users_data_to_save = {uid: user.to_dict() for uid, user in self.users.items()}
            save_data(self.users_file_path, users_data_to_save)
            # Keep audit log minimal unless debugging save issues
            # log_audit(self.audit_log_path, "system", "save_users", f"success - saved {len(self.users)} users")
        except Exception as e:
             logging.error(f"Error saving user data to {self.users_file_path}: {e}")
             log_audit(self.audit_log_path, "system", "save_users", f"failure: {e}")


    def register_user(self, username, password, role="basic"):
        # (Keep existing register_user implementation from previous step)
        if not username or not username.strip():
            logging.error("Registration failed: Username cannot be empty.")
            log_audit(self.audit_log_path, "(registration attempt)", 'register', 'failure - empty username')
            return None
        if not password:
            logging.error("Registration failed: Password cannot be empty.")
            log_audit(self.audit_log_path, username, 'register', 'failure - empty password')
            return None
        if role not in VALID_ROLES:
            logging.error(f"Registration failed: Invalid role '{role}'. Valid roles: {VALID_ROLES}")
            log_audit(self.audit_log_path, username, 'register', f'failure - invalid role: {role}')
            return None

        username = username.strip()
        if any(user.username and user.username.lower() == username.lower() for user in self.users.values()):
            logging.warning(f"Registration failed: Username '{username}' already exists.")
            log_audit(self.audit_log_path, username, 'register', 'failure - username exists')
            return None

        password_hash = hash_password(password)
        if not password_hash:
            logging.error(f"Error hashing password during registration for '{username}'.")
            log_audit(self.audit_log_path, username, 'register', 'failure - password hash error')
            return None

        try:
            user_id = str(uuid.uuid4())
            new_user = User(user_id=user_id, username=username, password_hash=password_hash, role=role)
            self.users[user_id] = new_user
            self._save_users()
            logging.info(f"User '{username}' registered successfully with role '{role}'.")
            return new_user
        except Exception as e:
             logging.error(f"An error occurred during the final steps of registration for '{username}': {e}")
             log_audit(self.audit_log_path, username, 'register', f'failure - internal error: {e}')
             if 'user_id' in locals() and user_id in self.users: del self.users[user_id]
             return None


    def login_user(self, username, password):
        # (Keep existing login_user implementation from previous step)
        if not username or not password: return None
        user_to_check = None; username_lower = username.lower()
        for user in self.users.values():
            if user.username and user.username.lower() == username_lower: user_to_check = user; break
        if user_to_check:
            if isinstance(user_to_check.password_hash, bytes):
                if verify_password(password, user_to_check.password_hash):
                    logging.info(f"User '{username}' logged in successfully.")
                    # Clear any lingering reset token on successful login
                    if user_to_check.reset_token:
                        user_to_check.reset_token = None
                        user_to_check.reset_token_expiry = None
                        self._save_users()
                    return user_to_check
                else: logging.warning(f"Invalid password for user '{username}'."); return None
            else: logging.error(f"Login failed for '{username}': Stored password hash is not in the correct bytes format."); log_audit(self.audit_log_path, username, 'login', 'failure - invalid stored hash format'); return None
        else: logging.warning(f"Username '{username}' not found during login attempt."); return None


    def find_user_by_id(self, user_id):
        # (Keep existing implementation)
        return self.users.get(user_id)

    def find_user_by_username(self, username):
        # (Keep existing implementation)
        if not username: return None
        username_lower = username.lower()
        for user in self.users.values():
            if user.username and user.username.lower() == username_lower: return user
        return None

    def set_user_role(self, user_id, new_role, actor_username="system"):
        # (Keep existing implementation from previous step)
        user_to_modify = self.find_user_by_id(user_id)
        if not user_to_modify: logging.error(f"Cannot set role: User with ID '{user_id}' not found."); log_audit(self.audit_log_path, actor_username, 'set_user_role', f"failure - user not found: {user_id}"); return False
        if new_role not in VALID_ROLES: logging.error(f"Cannot set role for user '{user_to_modify.username}': Invalid role '{new_role}'. Valid roles: {VALID_ROLES}"); log_audit(self.audit_log_path, actor_username, 'set_user_role', f"failure - invalid role '{new_role}' for user {user_id}"); return False
        if user_to_modify.role == new_role: logging.info(f"User '{user_to_modify.username}' already has role '{new_role}'. No change needed."); log_audit(self.audit_log_path, actor_username, 'set_user_role', f"no change - user {user_id} already has role '{new_role}'"); return True
        original_role = user_to_modify.role
        user_to_modify.role = new_role
        self._save_users()
        logging.info(f"Successfully changed role for user '{user_to_modify.username}' from '{original_role}' to '{new_role}'.")
        log_audit(self.audit_log_path, actor_username, 'set_user_role', f"success - user {user_id} ({user_to_modify.username}) role changed from '{original_role}' to '{new_role}'")
        return True

    # --- NEW: Delete User Method ---
    def delete_user(self, user_id, actor_username="system"):
        """
        Deletes a user from the system.

        Args:
            user_id (str): The ID of the user to delete.
            actor_username (str): The username of the user performing the action (for audit).

        Returns:
            bool: True if the user was deleted successfully, False otherwise.
        """
        user_to_delete = self.find_user_by_id(user_id)
        if not user_to_delete:
            logging.error(f"Cannot delete user: User with ID '{user_id}' not found.")
            log_audit(self.audit_log_path, actor_username, 'delete_user', f"failure - user not found: {user_id}")
            return False

        # Prevent admin from deleting themselves? Or add specific checks.
        # if user_id == actor_user_id: # Example check if actor is identified by ID
        #     logging.warning(f"User '{actor_username}' attempted to delete themselves.")
        #     log_audit(self.audit_log_path, actor_username, 'delete_user', f"failure - attempted self-deletion: {user_id}")
        #     return False

        deleted_username = user_to_delete.username
        deleted_role = user_to_delete.role
        del self.users[user_id]
        self._save_users() # Save the change
        logging.info(f"Successfully deleted user '{deleted_username}' (ID: {user_id}, Role: {deleted_role}).")
        log_audit(self.audit_log_path, actor_username, 'delete_user', f"success - deleted user {user_id} ({deleted_username}), role: {deleted_role}")
        return True

    # --- NEW: Password Reset Methods ---

    def generate_reset_token(self, username):
        """
        Generates a password reset token for a user and sets its expiry.

        Args:
            username (str): The username of the user requesting the reset.

        Returns:
            str | None: The generated reset token if the user exists, otherwise None.
                         Returns None on error.
        """
        user = self.find_user_by_username(username)
        if not user:
            logging.warning(f"Password reset requested for non-existent user: {username}")
            # Don't log specific failure type here to avoid user enumeration
            return None

        try:
            token = secrets.token_urlsafe(32) # Generate a secure random token
            expiry_time = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

            user.reset_token = token
            user.reset_token_expiry = expiry_time
            self._save_users()

            logging.info(f"Generated password reset token for user: {username}")
            log_audit(self.audit_log_path, username, 'generate_reset_token', 'success')

            # In a real application, you would email this token to the user here.
            # Since we can't email, we just return it.
            # WARNING: Returning the token directly like this is insecure for production.
            return token
        except Exception as e:
            logging.error(f"Error generating reset token for {username}: {e}")
            log_audit(self.audit_log_path, username, 'generate_reset_token', f'failure: {e}')
            return None


    def verify_reset_token(self, token):
        """
        Verifies if a password reset token is valid and not expired.

        Args:
            token (str): The password reset token to verify.

        Returns:
            User | None: The User object associated with the token if valid, otherwise None.
        """
        if not token:
            return None

        user_found = None
        for user in self.users.values():
            if user.reset_token == token:
                user_found = user
                break

        if not user_found:
            logging.warning(f"Invalid password reset token provided: {token[:8]}...")
            # Don't log specific failure type here
            return None

        # Check expiry
        if user_found.reset_token_expiry and user_found.reset_token_expiry >= datetime.now(timezone.utc):
             # Token is valid and not expired
             return user_found
        else:
            # Token expired or expiry not set correctly
            logging.warning(f"Expired or invalid expiry for reset token for user {user_found.username}")
            # Clear the expired token
            user_found.reset_token = None
            user_found.reset_token_expiry = None
            self._save_users()
            log_audit(self.audit_log_path, user_found.username, 'verify_reset_token', 'failure - token expired')
            return None


    def reset_password(self, token, new_password):
        """
        Resets the password for a user using a valid reset token.

        Args:
            token (str): The valid password reset token.
            new_password (str): The new password to set.

        Returns:
            bool: True if the password was reset successfully, False otherwise.
        """
        user = self.verify_reset_token(token) # verify_reset_token checks validity and expiry

        if not user:
            # Verification failed (invalid token or expired) - error logged in verify_reset_token
            return False

        if not new_password:
            logging.error(f"Password reset failed for user {user.username}: New password cannot be empty.")
            log_audit(self.audit_log_path, user.username, 'reset_password', 'failure - empty password')
            return False

        # Hash the new password
        new_password_hash = hash_password(new_password)
        if not new_password_hash:
            logging.error(f"Password reset failed for user {user.username}: Error hashing new password.")
            log_audit(self.audit_log_path, user.username, 'reset_password', 'failure - password hash error')
            return False

        # Update password and clear token
        user.password_hash = new_password_hash
        user.reset_token = None
        user.reset_token_expiry = None
        self._save_users() # Save the changes

        logging.info(f"Password successfully reset for user: {user.username}")
        log_audit(self.audit_log_path, user.username, 'reset_password', 'success')
        return True