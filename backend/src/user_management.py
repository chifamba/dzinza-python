# backend/src/user_management.py
import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from itsdangerous import BadSignature, URLSafeTimedSerializer

import yagmail # Ensure this is added to requirements.txt

from .audit_log import log_audit
from .encryption import hash_password, verify_password
from .db_utils import load_data, save_data
from .user import User, VALID_ROLES

# Constants for password reset
RESET_TOKEN_EXPIRY_MINUTES = 60

def send_email(to_email, subject, body):
    """Helper function to send email using yagmail."""
    try:
        # Load credentials from environment variables
        email_user = os.environ.get("EMAIL_USER")
        email_password = os.environ.get("EMAIL_PASSWORD")

        if not email_user or not email_password:
             logging.error("Email credentials (EMAIL_USER, EMAIL_PASSWORD) not found in environment variables.")
             return False

        yag = yagmail.SMTP(email_user, email_password)
        yag.send(to=to_email, subject=subject, contents=body)
        logging.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending email to {to_email}: {e}", exc_info=True)
        return False

class UserManagement:
    """
    Handles user registration, login, roles, deletion, password reset, and data persistence.
    """
    def __init__(self, users_file_path=None, audit_log_path=None):
        backend_dir = os.path.dirname(os.path.dirname(__file__)) # Go up two directories to reach 'backend'
        self.users_file_path = users_file_path or os.path.join(backend_dir, 'data', 'users.json') # Corrected default path
        self.audit_log_path = audit_log_path or os.path.join(backend_dir, 'logs', 'audit.log') # Corrected default path
        self.secret_key = os.environ.get('FLASK_SECRET_KEY')
        if not self.secret_key:
             logging.critical("FLASK_SECRET_KEY environment variable not set. Password reset tokens will not work.")
             raise ValueError("FLASK_SECRET_KEY is required for password reset functionality.")
        self.serializer = URLSafeTimedSerializer(self.secret_key, salt='password-reset-salt')

        users_dir = os.path.dirname(self.users_file_path)
        if users_dir:
            os.makedirs(users_dir, exist_ok=True)
        self.users = self._load_users()

    def _load_users(self):
        """Loads user data from the specified JSON file (encrypted)."""
        users_data = load_data(self.users_file_path, default={}, is_encrypted=True) # Default to empty dict
        loaded_users = {}
        if isinstance(users_data, dict): # Ensure data is a dictionary
            for uid, udata in users_data.items():
                 try:
                     if isinstance(udata, dict): # Check if udata is a dict
                         if 'user_id' not in udata:
                            udata['user_id'] = uid # Ensure user_id is present
                         loaded_users[uid] = User.from_dict(udata)
                     else:
                          logging.warning(f"_load_users: Invalid data format for user ID {uid} (expected dict, got {type(udata)}). Skipping.")
                 except (KeyError, ValueError, TypeError) as e:
                     logging.error(f"Error loading user data in _load_users for ID {uid}: {e}. Skipping this user.", exc_info=True)
                     log_audit(self.audit_log_path, "system", "load_users", f"error - invalid user data for ID {uid}: {e}")
            count = len(loaded_users)
            logging.info(f"Loaded {count} users from {self.users_file_path}")
            return loaded_users
        else:
            logging.warning(f"No user data found or error loading from {self.users_file_path}. Starting with empty user list.")
            log_audit(self.audit_log_path, "system", "load_users", "warning - file not found or empty/invalid")
            return {} # Return empty dict

    def _save_users(self):
        """Saves the current user data to the JSON file (encrypted)."""
        try:
            # Ensure all users are User objects before trying to call to_dict()
            users_data_to_save = {}
            for uid, user in self.users.items():
                 if isinstance(user, User):
                     users_data_to_save[uid] = user.to_dict()
                 else:
                      logging.error(f"_save_users: Attempted to save non-User object for ID {uid}. Skipping.")
            save_data(self.users_file_path, users_data_to_save, is_encrypted=True)
            # Removed audit log here as saving the users data is an expected behavior
        except Exception as e:
             logging.error(f"Error saving user data in _save_users to {self.users_file_path}: {e}", exc_info=True)
             log_audit(self.audit_log_path, "system", "save_users", f"failure: {e}")

    def register_user(self, username, password, role="basic"):
        """Registers a new user."""
        if not username or not username.strip():
            logging.error("register_user failed: Username cannot be empty.", exc_info=True)
            log_audit(self.audit_log_path, "(registration attempt)", 'register', 'failure - empty username')
            return None
        if not password:
            logging.error("register_user failed: Password cannot be empty.", exc_info=True)
            log_audit(self.audit_log_path, username, 'register', 'failure - empty password')
            return None
        if role not in VALID_ROLES:
            logging.error(f"register_user failed: Invalid role '{role}'. Valid roles: {VALID_ROLES}", exc_info=True)
            log_audit(self.audit_log_path, username, 'register', f"failure - invalid role: {role}")
            return None

        username = username.strip()
        # Case-insensitive check for existing username
        if any(user.username and user.username.lower() == username.lower() for user in self.users.values() if isinstance(user, User)):
            logging.warning(f"Registration failed: Username '{username}' already exists.", exc_info=True)
            log_audit(self.audit_log_path, username, 'register', 'failure - username exists')
            return None

        password_hash = hash_password(password)
        if password_hash is None:
            logging.error(f"register_user error hashing password during registration for '{username}'.", exc_info=True)
            log_audit(self.audit_log_path, username, 'register', f'failure - password hash error')
            return None

        try:
            user_id = str(uuid.uuid4())
            # Create User object using constructor
            new_user = User(user_id=user_id, username=username, password_hash=password_hash, role=role)
            self.users[user_id] = new_user
            self._save_users()
            logging.info(f"User '{username}' registered successfully with role '{role}'.")
            log_audit(self.audit_log_path, username, 'register', f'success - role: {role}, id: {user_id}')
            return new_user
        except Exception as e:
             logging.error(f"An error occurred in register_user during the final steps of registration for '{username}': {e}", exc_info=True)
             log_audit(self.audit_log_path, username, 'register', f'failure - internal error: {e}')
             # Rollback: remove user if added before error
             if 'user_id' in locals() and user_id in self.users:
                 del self.users[user_id]
             return None

    def login_user(self, username, password):
        """Authenticates a user based on username and password."""
        if not username or not password:
            return None

        user_to_check = None
        username_lower = username.lower()
        for user in self.users.values():
             # Ensure it's a User object before accessing attributes
             if isinstance(user, User) and user.username and user.username.lower() == username_lower:
                 user_to_check = user
                 break

        if user_to_check:
            # Check if password hash exists and is bytes
            if user_to_check.password_hash and isinstance(user_to_check.password_hash, bytes):
                if verify_password(password, user_to_check.password_hash):
                    logging.info(f"User '{username}' logged in successfully.")
                    log_audit(self.audit_log_path, username, 'login', 'success')
                    # Clear any lingering reset token on successful login
                    if user_to_check.reset_token:
                        user_to_check.reset_token = None
                        user_to_check.reset_token_expiry = None
                        self._save_users()
                    return user_to_check
                else:
                    logging.warning(f"login_user - Invalid password for user '{username}'.", exc_info=False) # No need for stack trace on wrong password
                    log_audit(self.audit_log_path, username, 'login', 'failure - invalid password')
                    return None
            else:
                logging.error(f"login_user failed for '{username}': Stored password hash is missing or not bytes.", exc_info=True)
                log_audit(self.audit_log_path, username, 'login', 'failure - invalid stored hash format')
                return None
        else:
            logging.warning(f"login_user - Username '{username}' not found during login attempt.", exc_info=False)
            log_audit(self.audit_log_path, username, 'login', 'failure - user not found')
            return None

    def find_user_by_username(self, username):
        """Finds a user by their username (case-insensitive)."""
        if not username:
            return None
        username_lower = username.lower()
        for user in self.users.values():
             if isinstance(user, User) and user.username and user.username.lower() == username_lower:
                 return user
        return None

    def find_user_by_id(self, user_id):
        """Finds a user by their unique ID."""
        user = self.users.get(user_id)
        if isinstance(user, User):
            return user
        return None

    def set_user_role(self, user_id, new_role, actor_username="system"):
        """Sets the role for a given user ID."""
        user_to_modify = self.find_user_by_id(user_id)
        if not user_to_modify:
            logging.error(f"set_user_role - Cannot set role: User with ID '{user_id}' not found.", exc_info=True)
            log_audit(self.audit_log_path, actor_username, 'set_user_role', f"failure - user not found: {user_id}")
            return False

        if new_role not in VALID_ROLES:
            logging.error(f"set_user_role - Cannot set role for user '{user_to_modify.username}': Invalid role '{new_role}'. Valid roles: {VALID_ROLES}", exc_info=True)
            log_audit(self.audit_log_path, actor_username, 'set_user_role', f"failure - invalid role '{new_role}' for user {user_id}")
            return False

        if user_to_modify.role == new_role:
            logging.info(f"User '{user_to_modify.username}' already has role '{new_role}'. No change needed.")
            log_audit(self.audit_log_path, actor_username, 'set_user_role', f"no change - user {user_id} already has role '{new_role}'")
            return True # Indicate success as the state is as requested

        original_role = user_to_modify.role
        user_to_modify.role = new_role
        self._save_users()
        logging.info(f"Successfully changed role for user '{user_to_modify.username}' from '{original_role}' to '{new_role}'.")
        log_audit(self.audit_log_path, actor_username, 'set_user_role', f"success - user {user_id} ({user_to_modify.username}) role changed from '{original_role}' to '{new_role}'")
        return True

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
            logging.error(f"delete_user - Cannot delete user: User with ID '{user_id}' not found.", exc_info=True)
            log_audit(self.audit_log_path, actor_username, 'delete_user', f"failure - user not found: {user_id}")
            return False

        # Optional: Add checks to prevent deletion of critical accounts if needed
        # if user_to_delete.role == 'admin' and some_condition: return False

        deleted_username = user_to_delete.username
        deleted_role = user_to_delete.role
        del self.users[user_id]
        self._save_users() # Save the change
        logging.info(f"Successfully deleted user '{deleted_username}' (ID: {user_id}, Role: {deleted_role}).")
        log_audit(self.audit_log_path, actor_username, 'delete_user', f"success - deleted user {user_id} ({deleted_username}), role: {deleted_role}")
        return True

    def generate_password_reset_token(self, user_id):
        """Generates a time-sensitive password reset token."""
        user = self.find_user_by_id(user_id)
        if not user:
            logging.warning(f"generate_password_reset_token - requested for non-existent user ID: {user_id}", exc_info=True)
            return None, None
        try:
            token = self.serializer.dumps(user_id)
            # Expiration time in UTC
            expiration_time = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
            user.reset_token = token
            user.reset_token_expiry = expiration_time # Store datetime object
            self._save_users()
            return token, expiration_time
        except Exception as e:
            logging.error(f"Error generating password reset token for user ID {user_id}: {e}", exc_info=True)
            return None, None

    def request_password_reset(self, email):
        """Generates a reset token for the user with the given email and sends it."""
        user = self.find_user_by_username(email)
        if not user:
            logging.warning(f"request_password_reset: No user found with email: {email}")
            # Return True here to prevent revealing if an email is registered
            return True

        token, expiry = self.generate_password_reset_token(user.user_id)
        if not token:
            logging.error(f"request_password_reset: Error generating token for user: {email}")
            return False # Internal error

        # Construct reset link (requires APP_URL environment variable)
        app_url = os.environ.get('APP_URL', 'http://localhost:5173') # Default for dev
        reset_link = f"{app_url}/reset-password/{token}" # Assuming this frontend route exists

        expiry_str = expiry.strftime('%Y-%m-%d %H:%M:%S %Z') if expiry else 'soon'
        body = f"Hello {user.username},\n\nPlease click the following link to reset your password:\n{reset_link}\n\nThis link will expire {expiry_str}.\n\nIf you did not request this, please ignore this email."

        # Use the helper function to send email
        if not send_email(email, "Dzinza Family Tree - Password Reset Request", body):
            logging.error(f"request_password_reset: Error sending email to {email}")
            return False

        logging.info(f"request_password_reset: Password reset email sent to {email}")
        return True

    def reset_password(self, token, new_password):
        """Resets the user's password using a valid token."""
        user_id = self.validate_password_reset_token(token)
        if not user_id:
            logging.warning(f"Invalid or expired reset token provided: {token[:8]}...", exc_info=False)
            return False

        user = self.find_user_by_id(user_id)
        if not user:
            # Should not happen if token was valid, but check anyway
            logging.error(f"reset_password - User not found for user_id: {user_id} despite valid token.")
            return False

        if not new_password:
            logging.error(f"Password reset failed for user {user.username}: New password cannot be empty.", exc_info=True)
            return False

        # Validate password complexity if needed here

        new_password_hash = hash_password(new_password)
        if new_password_hash is None:
            logging.error(f"reset_password failed for user {user.username}: Error hashing new password.")
            log_audit(self.audit_log_path, user.username, 'reset_password', f'failure - password hash error')
            return False

        # Update password and clear token details
        user.password_hash = new_password_hash
        user.reset_token = None
        user.reset_token_expiry = None
        self._save_users()
        logging.info(f"Password successfully reset for user: {user.username}")
        log_audit(self.audit_log_path, user.username, 'reset_password', 'success')
        return True

    def validate_password_reset_token(self, token):
        """Validates a password reset token and returns the user ID if valid."""
        try:
            # Loads the token and checks expiration (max_age is in seconds)
            user_id = self.serializer.loads(token, max_age=RESET_TOKEN_EXPIRY_MINUTES * 60)

            # Additional check: Ensure the token matches the one stored for the user
            user = self.find_user_by_id(user_id)
            if not user or user.reset_token != token:
                 logging.warning(f"Token valid syntax/time, but does not match stored token for user {user_id}.")
                 return None
            # Check if token expiry time in user object has passed (belt-and-suspenders)
            if user.reset_token_expiry and user.reset_token_expiry < datetime.now(timezone.utc):
                 logging.warning(f"Token valid syntax/time, but expired according to stored expiry for user {user_id}.")
                 # Optionally clear the expired token here
                 # user.reset_token = None
                 # user.reset_token_expiry = None
                 # self._save_users()
                 return None

            return user_id
        except BadSignature:
            logging.warning(f"Password reset token validation failed: Bad signature or expired. Token: {token[:8]}...")
            return None
        except Exception as e:
            logging.error(f"Error validating reset token: {e}. Token: {token[:8]}...", exc_info=True)
            return None

    # Added method to get all users
    def get_all_users(self):
        """
        Returns a list of all registered users.

        Returns:
            list[User]: A list of all User objects.
        """
        # Return a copy of the values to prevent external modification
        return list(self.users.values())