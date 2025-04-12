# src/user_management.py

import json
import os
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta, timezone

from .user import User, VALID_ROLES
from .audit_log import AuditLog, PlaceholderAuditLog
from .encryption import DataEncryptor, PlaceholderDataEncryptor, check_password # Import check_password

class UserManager:
    """Manages user accounts, authentication, and persistence."""

    def __init__(self, audit_log: Optional[AuditLog] = None, encryptor: Optional[DataEncryptor] = None):
        """
        Initializes the UserManager.

        Args:
            audit_log: An instance for logging actions. Defaults to PlaceholderAuditLog.
            encryptor: An instance for data encryption/decryption. Defaults to PlaceholderDataEncryptor.
        """
        self.users: Dict[str, User] = {}
        self.audit_log = audit_log or PlaceholderAuditLog()
        self.encryptor = encryptor or PlaceholderDataEncryptor()
        logging.info("UserManager initialized.")

    def add_user(self, user: User, actor_user_id: str = "system") -> bool:
        """
        Adds a new user to the manager.

        Args:
            user: The User object to add.
            actor_user_id: The ID of the user performing the action.

        Returns:
            True if the user was added successfully, False if a user with the same ID already exists.
        """
        if not isinstance(user, User):
            logging.error(f"Attempted to add non-User object: {type(user)}")
            return False
        if user.user_id in self.users:
            logging.warning(f"Failed to add user: ID '{user.user_id}' already exists.")
            return False

        try:
            # Ensure role is valid (User.__post_init__ should raise error if invalid)
            if user.role not in VALID_ROLES:
                 logging.warning(f"Attempted to add user '{user.user_id}' with invalid role '{user.role}'. Setting to 'guest'.")
                 user.role = "guest" # Or reject the addition

            self.users[user.user_id] = user
            log_desc = f"Added user: {user.user_id} ({user.email})"
            self.audit_log.log_event(actor_user_id, "user_added", log_desc)
            logging.info(f"User '{user.user_id}' added by '{actor_user_id}'.")
            return True
        except ValueError as ve: # Catch validation errors from User.__post_init__
             logging.error(f"Failed to add user '{user.user_id}' due to validation error: {ve}")
             return False
        except Exception as e:
            logging.exception(f"Unexpected error adding user '{user.user_id}': {e}")
            return False


    def get_user(self, user_id: str) -> Optional[User]:
        """Retrieves a user by their ID."""
        return self.users.get(user_id)

    def update_user(self, user_id: str, update_data: Dict[str, Any], actor_user_id: str = "system") -> bool:
        """
        Updates details of an existing user.

        Args:
            user_id: The ID of the user to update.
            update_data: Dictionary of attributes to update (e.g., email, role, trust_level).
                         Password updates should use a dedicated method like change_password.
            actor_user_id: The ID of the user performing the action.

        Returns:
            True if the update was successful, False otherwise.
        """
        user = self.get_user(user_id)
        if not user:
            logging.warning(f"Update failed: User '{user_id}' not found.")
            return False

        updated_fields = {}
        for key, value in update_data.items():
            if key == "password_hash" or key == "password":
                logging.warning(f"Attempted to update password via generic update for user '{user_id}'. Use change_password method.")
                continue # Skip password changes here

            if key == "role":
                 if value not in VALID_ROLES:
                     logging.warning(f"Update failed for user '{user_id}': Invalid role '{value}'.")
                     return False # Fail the whole update if role is invalid
                 if user.role != value:
                     user.role = value
                     updated_fields[key] = value
            elif key == "trust_level":
                 try:
                     new_trust = int(value)
                     if user.trust_level != new_trust:
                         user.trust_level = max(0, min(100, new_trust)) # Clamp value
                         updated_fields[key] = user.trust_level
                 except (ValueError, TypeError):
                     logging.warning(f"Update failed for user '{user_id}': Invalid trust level '{value}'. Must be integer.")
                     return False # Fail update if trust level is invalid format
            elif hasattr(user, key):
                current_value = getattr(user, key)
                if current_value != value:
                    setattr(user, key, value)
                    updated_fields[key] = value
            else:
                logging.warning(f"Update warning for user '{user_id}': Attribute '{key}' not found on User object.")

        if updated_fields:
            log_desc = f"Updated user '{user_id}'. Changes: {updated_fields}"
            self.audit_log.log_event(actor_user_id, "user_updated", log_desc)
            logging.info(f"User '{user_id}' updated by '{actor_user_id}'. Changes: {updated_fields}")
            return True
        else:
            logging.info(f"No changes applied during update for user '{user_id}'.")
            return True # No changes, but operation didn't fail


    def delete_user(self, user_id: str, actor_user_id: str = "system") -> bool:
        """
        Deletes a user from the manager.

        Args:
            user_id: The ID of the user to delete.
            actor_user_id: The ID of the user performing the action.

        Returns:
            True if deletion was successful, False if the user was not found.
        """
        user = self.get_user(user_id)
        if not user:
            logging.warning(f"Deletion failed: User '{user_id}' not found.")
            return False

        email = user.email # Get email before deleting
        del self.users[user_id]
        log_desc = f"Deleted user: {user_id} ({email})"
        self.audit_log.log_event(actor_user_id, "user_deleted", log_desc)
        logging.info(f"User '{user_id}' deleted by '{actor_user_id}'.")
        return True

    def authenticate_user(self, user_id: str, password: str) -> Optional[User]:
        """
        Authenticates a user based on user ID and password.

        Args:
            user_id: The user ID to authenticate.
            password: The plaintext password provided by the user.

        Returns:
            The User object if authentication is successful, None otherwise.
        """
        user = self.get_user(user_id)
        if not user:
            log_desc = f"Failed login attempt for user '{user_id}': User not found."
            self.audit_log.log_event(user_id, "login_failed", log_desc) # Log with attempted user_id
            logging.warning(log_desc)
            return None

        # Use the imported check_password function
        if check_password(user.password_hash, password):
            user.update_last_login() # Update last login time on success
            log_desc = f"User '{user_id}' authenticated successfully."
            self.audit_log.log_event(user_id, "login_success", log_desc)
            logging.info(log_desc)
            return user
        else:
            log_desc = f"Failed login attempt for user '{user_id}': Incorrect password."
            self.audit_log.log_event(user_id, "login_failed", log_desc)
            logging.warning(log_desc)
            return None

    # --- Persistence ---

    def save_users(self, file_path: str, actor_user_id: str = "system") -> bool:
        """
        Saves the current user data to a file (e.g., JSON).

        Args:
            file_path: The path to the file where users should be saved.
            actor_user_id: The ID of the user performing the save action.

        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            users_data = [user.to_dict(include_hash=True) for user in self.users.values()]
            data_to_save = {"users": users_data}
            json_string = json.dumps(data_to_save, indent=4)
            encrypted_data = self.encryptor.encrypt(json_string)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)

            log_desc = f"User data saved to {file_path}"
            self.audit_log.log_event(actor_user_id, "users_saved", log_desc)
            logging.info(f"{log_desc} by {actor_user_id}.")
            return True
        except IOError as e:
            log_desc = f"Error saving user data to {file_path}: {e}"
            self.audit_log.log_event(actor_user_id, "users_save_failed", log_desc)
            logging.error(log_desc)
            return False
        except Exception as e:
            log_desc = f"Unexpected error saving user data: {e}"
            self.audit_log.log_event(actor_user_id, "users_save_failed", log_desc)
            logging.exception(log_desc) # Log full traceback
            return False

    def load_users(self, file_path: str, actor_user_id: str = "system") -> bool:
        """
        Loads user data from a file, replacing current users.

        Args:
            file_path: The path to the file from which users should be loaded.
            actor_user_id: The ID of the user performing the load action.

        Returns:
            True if loading was successful, False otherwise.
        """
        if not os.path.exists(file_path):
            log_desc = f"User data file not found: {file_path}. Skipping load."
            self.audit_log.log_event(actor_user_id, "users_load_skipped", log_desc)
            logging.warning(log_desc)
            return False # Indicate file not found, but not necessarily a failure of the manager

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted_data = f.read()

            decrypted_data_str = self.encryptor.decrypt(encrypted_data)
            if not decrypted_data_str:
                 # Handle potential decryption failure if decrypt returns empty on error
                 raise ValueError("Decryption failed or resulted in empty data.")

            loaded_data = json.loads(decrypted_data_str)
            users_list = loaded_data.get("users", [])

            self.users.clear() # Clear existing users before loading
            loaded_count = 0
            skipped_count = 0
            for user_data in users_list:
                try:
                    user = User.from_dict(user_data)
                    self.users[user.user_id] = user
                    loaded_count += 1
                except (KeyError, ValueError) as e:
                    logging.warning(f"Skipping invalid user data during load: {e}. Data: {user_data}")
                    skipped_count += 1

            log_desc = f"User data loaded from {file_path}. Found {loaded_count} users."
            if skipped_count > 0:
                log_desc += f" Skipped {skipped_count} invalid entries."
            self.audit_log.log_event(actor_user_id, "users_loaded", log_desc)
            logging.info(f"{log_desc} Loaded by {actor_user_id}.")
            return True

        except (IOError, json.JSONDecodeError, ValueError) as e:
            log_desc = f"Error loading user data from {file_path}: {e}"
            self.audit_log.log_event(actor_user_id, "users_load_failed", log_desc)
            logging.error(log_desc)
            self.users.clear() # Ensure partial loads don't leave inconsistent state
            return False
        except Exception as e:
            log_desc = f"Unexpected error loading user data: {e}"
            self.audit_log.log_event(actor_user_id, "users_load_failed", log_desc)
            logging.exception(log_desc) # Log full traceback
            self.users.clear()
            return False

    # --- Trust Decay ---
    def apply_trust_decay(self, inactivity_threshold_days: int, decay_amount: int, min_trust_level: int = 0, actor_user_id: str = "system") -> None:
        """
        Applies trust decay to users inactive for a specified period.

        Args:
            inactivity_threshold_days: Number of days of inactivity to trigger decay.
            decay_amount: The amount to decrease trust level by (positive integer).
            min_trust_level: The minimum trust level a user can decay to.
            actor_user_id: The ID performing this action (e.g., 'system_cron').
        """
        if decay_amount <= 0:
             logging.warning("Trust decay amount must be positive. Aborting decay process.")
             return

        now = datetime.now(timezone.utc)
        threshold_time = now - timedelta(days=inactivity_threshold_days)
        decayed_count = 0

        logging.info(f"Starting trust decay process by '{actor_user_id}' (Threshold: {inactivity_threshold_days} days, Amount: {decay_amount}, Min Level: {min_trust_level}).")

        # Iterate over a copy of user IDs as trust adjustment modifies the user object
        for user_id in list(self.users.keys()):
            user = self.users.get(user_id)
            if not user: continue # Should not happen if iterating keys, but safe check

            is_inactive = False
            if user.last_login:
                try:
                    last_login_dt = datetime.fromisoformat(user.last_login.replace('Z', '+00:00')) # Ensure timezone aware
                    if last_login_dt < threshold_time:
                        is_inactive = True
                except ValueError:
                    logging.warning(f"Could not parse last_login timestamp '{user.last_login}' for user '{user_id}'. Treating as inactive for decay.")
                    is_inactive = True # Treat unparseable dates as inactive? Or skip?
            else:
                # User has never logged in, consider inactive if account exists long enough?
                # For simplicity, treat users who never logged in as inactive for decay purposes.
                is_inactive = True

            if is_inactive and user.trust_level > min_trust_level:
                original_level = user.trust_level
                new_level = max(min_trust_level, user.trust_level - decay_amount)
                if new_level < original_level: # Apply decay only if it reduces the level
                    user.trust_level = new_level
                    log_desc = f"Applied trust decay to user '{user_id}'. New level: {new_level}"
                    self.audit_log.log_event(actor_user_id, "trust_decay_applied", log_desc)
                    logging.info(log_desc)
                    decayed_count += 1

        logging.info(f"Trust decay process completed. Decayed trust for {decayed_count} inactive users.")

    # Add methods for password change, password reset flows etc. as needed
    # These should use hash_password from encryption.py

