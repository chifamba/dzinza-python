# Modify src/user_management.py to add deletion and password reset logic
import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from itsdangerous import BadSignature, URLSafeTimedSerializer

import yagmail

from .audit_log import log_audit
from .encryption import hash_password, verify_password
from .db_utils import load_data, save_data
from .user import User, VALID_ROLES

# Constants for password reset
RESET_TOKEN_EXPIRY_MINUTES = 60

def send_email(to_email, subject, body):
    try: yag = yagmail.SMTP(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASSWORD")); yag.send(to=to_email, subject=subject, contents=body); return True; except Exception as e: logging.error(f"Error in send_email: Error sending email to {to_email}: {e}", exc_info=True); return False

class UserManagement:

    """
    Handles user registration, login, roles, deletion, password reset, and data persistence.
    """
    def __init__(self, users_file_path='data/users.json', audit_log_path='data/audit.log'):
        self.users_file_path = users_file_path; users_dir = os.path.dirname(users_file_path); if users_dir: os.makedirs(users_dir, exist_ok=True)
        self.serializer = URLSafeTimedSerializer(os.environ.get('FLASK_SECRET_KEY'), salt='password-reset-salt')
        self.audit_log_path = audit_log_path
        users_dir = os.path.dirname(users_file_path)
        if users_dir: os.makedirs(users_dir, exist_ok=True); self.users = self._load_users()

    def _load_users(self):
        # (Keep existing _load_users implementation from previous step)
        # It now handles the 'role', 'reset_token', 'reset_token_expiry' fields via User.from_dict
        users_data = load_data(self.users_file_path, is_encrypted=True)
        loaded_users = {}
        if users_data:
            for uid, udata in users_data.items():
                 try:
                     if 'user_id' not in udata: udata['user_id'] = uid
                     loaded_users[uid] = User.from_dict(udata)
                 except (KeyError, ValueError) as e:
                     logging.error(f"Error loading user data in _load_users for ID {uid}: {e}. Skipping this user.", exc_info=True)
                     log_audit(self.audit_log_path, "system", "load_users", f"error - invalid user data for ID {uid}: {e}")
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
            save_data(self.users_file_path, users_data_to_save, is_encrypted=True)
            # Removed audit log here as saving the users data is an expected behavior
            # and it is already logged during the loading/registering/deleting/updating
        except Exception as e:
             logging.error(f"Error saving user data in _save_users to {self.users_file_path}: {e}", exc_info=True)
             log_audit(self.audit_log_path, "system", "save_users", f"failure: {e}")

    def register_user(self, username, password, role="basic"):

        # (Keep existing register_user implementation from previous step)
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
        if any(user.username and user.username.lower() == username.lower() for user in self.users.values()):
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
            new_user = User(user_id=user_id, username=username, password_hash=password_hash, role=role)
            self.users[user_id] = new_user
            self._save_users()
            logging.info(f"User '{username}' registered successfully with role '{role}'.")
            return new_user
        except Exception as e:
             logging.error(f"An error occurred in register_user during the final steps of registration for '{username}': {e}", exc_info=True)
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
            if user_to_check.password_hash:           
                if verify_password(password, user_to_check.password_hash):
                    logging.info(f"User '{username}' logged in successfully.")
                    # Clear any lingering reset token on successsful login
                    if user_to_check.reset_token:
                        user_to_check.reset_token = None
                        user_to_check.reset_token_expiry = None
                        self._save_users()
                    return user_to_check
                else: logging.warning(f"login_user - Invalid password for user '{username}'.", exc_info=True); return None
            else: logging.error(f"login_user failed for '{username}': Stored password hash is not in the correct bytes format.", exc_info=True); log_audit(self.audit_log_path, username, 'login', 'failure - invalid stored hash format'); return None
        else: logging.warning(f"login_user - Username '{username}' not found during login attempt.", exc_info=True); return None

    
        # (Keep existing implementation)
        return self.users.get(user_id)

    def find_user_by_username(self, username):
        # (Keep existing implementation)
        if not username: return None
        username_lower = username.lower()
        for user in self.users.values():
            if user.username and user.username.lower() == username_lower: return user
        return None

    def find_user_by_id(self, user_id):
    def set_user_role(self, user_id, new_role, actor_username="system"):
        # (Keep existing implementation from previous step)
        user_to_modify = self.find_user_by_id(user_id)
        if not user_to_modify: logging.error(f"set_user_role - Cannot set role: User with ID '{user_id}' not found.", exc_info=True); log_audit(self.audit_log_path, actor_username, 'set_user_role', f"failure - user not found: {user_id}"); return False
        if new_role not in VALID_ROLES: logging.error(f"set_user_role - Cannot set role for user '{user_to_modify.username}': Invalid role '{new_role}'. Valid roles: {VALID_ROLES}", exc_info=True); log_audit(self.audit_log_path, actor_username, 'set_user_role', f"failure - invalid role '{new_role}' for user {user_id}"); return False
        if user_to_modify.role == new_role: logging.info(f"User '{user_to_modify.username}' already has role '{new_role}'. No change needed.", exc_info=True); log_audit(self.audit_log_path, actor_username, 'set_user_role', f"no change - user {user_id} already has role '{new_role}'"); return True
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
            logging.error(f"delete_user - Cannot delete user: User with ID '{user_id}' not found.", exc_info=True)
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

    def generate_password_reset_token(self, user_id):
        user = self.find_user_by_id(user_id);        if not user: logging.warning(f"generate_password_reset_token - requested for non-existent user ID: {user_id}", exc_info=True); return None, None
        try:
            token = self.serializer.dumps(user_id); expiration_time = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
            user.reset_token = token; user.reset_token_expiry = expiration_time; self._save_users(); return token, expiration_time
        except Exception as e: logging.error(f"Error generating password reset token for user ID {user_id}: {e}", exc_info=True); return None, None

    def request_password_reset(self, email):
        user = self.find_user_by_username(email);        if not user: logging.warning(f"request_password_reset: No user found with email: {email}"); return False
        token, expiry = self.generate_password_reset_token(user.user_id);        if not token: logging.error(f"request_password_reset: Error generating token for user: {email}"); return False
        reset_link = f"{os.environ.get('APP_URL')}/reset_password/{token}"
        body = f"Please click the following link to reset your password: {reset_link} \n This link will expire at: {expiry.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        if not send_email(email, "Password Reset Request", body): logging.error(f"request_password_reset: Error sending email to {email}"); return False
        logging.info(f"request_password_reset: Password reset email sent to {email}"); return True

    def reset_password(self, token, new_password):
        user_id = self.validate_password_reset_token(token);        if not user_id: logging.warning(f"Invalid or expired reset token provided: {token[:8]}...", exc_info=True); return False
        user = self.find_user_by_id(user_id);        if not user: logging.error(f"reset_password - User not found for user_id: {user_id}"); return False
        if not new_password: logging.error(f"Password reset failed for user {user.username}: New password cannot be empty.", exc_info=True); return False
        new_password_hash = hash_password(new_password)
        if new_password_hash is None: logging.error(f"reset_password failed for user {user.username}: Error hashing new password."); log_audit(self.audit_log_path, user.username, 'reset_password', f'failure - password hash error'); return False
        user.password_hash = new_password_hash; user.reset_token = None; user.reset_token_expiry = None; self._save_users(); logging.info(f"Password successfully reset for user: {user.username}")
        log_audit(self.audit_log_path, user.username, 'reset_password', 'success'); return True

        
    

    def validate_password_reset_token(self, token):
        try:
            user_id = self.serializer.loads(token, max_age=RESET_TOKEN_EXPIRY_MINUTES * 60)
            return user_id
        except BadSignature:
            return None 
        except Exception as e:
            logging.error(f"Error validating reset token for: {e}", exc_info=True)
            return None