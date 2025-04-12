# src/user_management.py

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta, timezone
from tinydb import TinyDB, Query, table # Import TinyDB components

# Assuming db_utils.py exists for getting DB instances
# If not, you'd initialize TinyDB directly here or pass instances
from .db_utils import get_user_db # Import the function to get the DB instance

from .user import User, VALID_ROLES
from .audit_log import AuditLog, PlaceholderAuditLog
# Keep encryption imports if needed for password checking/hashing
from .encryption import DataEncryptor, PlaceholderDataEncryptor, check_password, hash_password

class UserManager:
    """Manages user accounts, authentication, and persistence using TinyDB."""

    def __init__(self, audit_log: Optional[AuditLog] = None, encryptor: Optional[DataEncryptor] = None):
        """
        Initializes the UserManager.

        Args:
            audit_log: An instance for logging actions. Defaults to PlaceholderAuditLog.
            encryptor: An instance for data encryption/decryption (currently unused for user data).
                       Defaults to PlaceholderDataEncryptor.
        """
        self.audit_log = audit_log or PlaceholderAuditLog()
        self.encryptor = encryptor or PlaceholderDataEncryptor()
        # REMOVED: self.users_table = get_user_db().table('users') - Defer DB access
        logging.info("UserManager initialized (DB access deferred to methods).")

    def _get_users_table(self) -> table.Table:
        """Helper method to get the TinyDB users table within context."""
        # This will now be called inside methods where app context exists
        return get_user_db().table('users')

    def add_user(self, user: User, actor_user_id: str = "system") -> bool:
        """
        Adds a new user to the TinyDB database.

        Args:
            user: The User object to add.
            actor_user_id: The ID of the user performing the action.

        Returns:
            True if the user was added successfully, False if a user with the same ID already exists or validation fails.
        """
        if not isinstance(user, User):
            logging.error(f"Attempted to add non-User object: {type(user)}")
            return False

        users_table = self._get_users_table() # Get table instance now
        UserQuery = Query()
        if users_table.contains(UserQuery.user_id == user.user_id):
            logging.warning(f"Failed to add user: ID '{user.user_id}' already exists in DB.")
            return False

        try:
            user_data = user.to_dict(include_hash=True)
            users_table.insert(user_data)

            log_desc = f"Added user: {user.user_id} ({user.email})"
            self.audit_log.log_event(actor_user_id, "user_added", log_desc)
            logging.info(f"User '{user.user_id}' added to DB by '{actor_user_id}'.")
            return True
        except ValueError as ve:
             logging.error(f"Failed to add user '{user.user_id}' due to validation error: {ve}")
             return False
        except Exception as e:
            logging.exception(f"Unexpected error adding user '{user.user_id}' to DB: {e}")
            return False


    def get_user(self, user_id: str) -> Optional[User]:
        """Retrieves a user by their ID from TinyDB."""
        users_table = self._get_users_table() # Get table instance now
        UserQuery = Query()
        user_data_list = users_table.search(UserQuery.user_id == user_id)
        if user_data_list:
            try:
                return User.from_dict(user_data_list[0])
            except (KeyError, ValueError) as e:
                 logging.error(f"Error creating User object from DB data for ID '{user_id}': {e}. Data: {user_data_list[0]}")
                 return None
        return None

    def update_user(self, user_id: str, update_data: Dict[str, Any], actor_user_id: str = "system") -> bool:
        """
        Updates details of an existing user in TinyDB.

        Args:
            user_id: The ID of the user to update.
            update_data: Dictionary of attributes to update. Password updates require 'password' key.
            actor_user_id: The ID of the user performing the action.

        Returns:
            True if the update was successful, False otherwise.
        """
        users_table = self._get_users_table() # Get table instance now
        UserQuery = Query()
        if not users_table.contains(UserQuery.user_id == user_id):
            logging.warning(f"Update failed: User '{user_id}' not found in DB.")
            return False

        db_update_data = {}
        validated_update_data = {}

        for key, value in update_data.items():
            if key == "password":
                if isinstance(value, str) and value:
                    db_update_data["password_hash"] = hash_password(value)
                    validated_update_data[key] = "****"
                else:
                    logging.warning(f"Skipping invalid password update for user '{user_id}'.")
                continue

            if key == "password_hash":
                 logging.warning(f"Direct update of 'password_hash' is discouraged for user '{user_id}'. Use 'password' key.")
                 continue

            if key == "role":
                 if value not in VALID_ROLES:
                     logging.warning(f"Update failed for user '{user_id}': Invalid role '{value}'.")
                     return False
                 db_update_data[key] = value
                 validated_update_data[key] = value
            elif key == "trust_level":
                 try:
                     new_trust = int(value)
                     clamped_trust = max(0, min(100, new_trust))
                     db_update_data[key] = clamped_trust
                     validated_update_data[key] = clamped_trust
                 except (ValueError, TypeError):
                     logging.warning(f"Update failed for user '{user_id}': Invalid trust level '{value}'. Must be integer.")
                     return False
            elif key in ["user_id", "email", "last_login", "attributes"]:
                 db_update_data[key] = value
                 validated_update_data[key] = value
            else:
                logging.warning(f"Update warning for user '{user_id}': Attribute '{key}' not directly managed or invalid.")

        if not db_update_data:
            logging.info(f"No valid fields to update for user '{user_id}'.")
            return True

        try:
            users_table.update(db_update_data, UserQuery.user_id == user_id)

            log_desc = f"Updated user '{user_id}'. Changes: {validated_update_data}"
            self.audit_log.log_event(actor_user_id, "user_updated", log_desc)
            logging.info(f"User '{user_id}' updated in DB by '{actor_user_id}'. Changes: {validated_update_data}")
            return True
        except Exception as e:
            logging.exception(f"Unexpected error updating user '{user_id}' in DB: {e}")
            return False


    def delete_user(self, user_id: str, actor_user_id: str = "system") -> bool:
        """
        Deletes a user from the TinyDB database.

        Args:
            user_id: The ID of the user to delete.
            actor_user_id: The ID of the user performing the action.

        Returns:
            True if deletion was successful, False if the user was not found.
        """
        users_table = self._get_users_table() # Get table instance now
        UserQuery = Query()
        user_data_list = users_table.search(UserQuery.user_id == user_id)

        if not user_data_list:
            logging.warning(f"Deletion failed: User '{user_id}' not found in DB.")
            return False

        user_email = user_data_list[0].get('email', 'N/A')

        try:
            users_table.remove(UserQuery.user_id == user_id)

            log_desc = f"Deleted user: {user_id} ({user_email})"
            self.audit_log.log_event(actor_user_id, "user_deleted", log_desc)
            logging.info(f"User '{user_id}' deleted from DB by '{actor_user_id}'.")
            return True
        except Exception as e:
             logging.exception(f"Unexpected error deleting user '{user_id}' from DB: {e}")
             return False

    def authenticate_user(self, user_id: str, password: str) -> Optional[User]:
        """
        Authenticates a user based on user ID and password stored in TinyDB.

        Args:
            user_id: The user ID to authenticate.
            password: The plaintext password provided by the user.

        Returns:
            The User object if authentication is successful, None otherwise.
        """
        user = self.get_user(user_id) # This now gets the table inside
        if not user:
            log_desc = f"Failed login attempt for user '{user_id}': User not found."
            self.audit_log.log_event(user_id, "login_failed", log_desc)
            logging.warning(log_desc)
            return None

        if check_password(user.password_hash, password):
            now_iso = datetime.now(timezone.utc).isoformat()
            # Update last login time in the database
            self.update_user(user_id, {"last_login": now_iso}, actor_user_id=user_id)
            user.last_login = now_iso # Update the returned object as well

            log_desc = f"User '{user_id}' authenticated successfully."
            self.audit_log.log_event(user_id, "login_success", log_desc)
            logging.info(log_desc)
            return user
        else:
            log_desc = f"Failed login attempt for user '{user_id}': Incorrect password."
            self.audit_log.log_event(user_id, "login_failed", log_desc)
            logging.warning(log_desc)
            return None

    def get_all_users(self) -> List[User]:
        """ Retrieves all users from the database. """
        users_table = self._get_users_table() # Get table instance now
        all_user_data = users_table.all()
        users = []
        for user_data in all_user_data:
            try:
                users.append(User.from_dict(user_data))
            except (KeyError, ValueError) as e:
                 logging.error(f"Error creating User object from DB data: {e}. Data: {user_data}")
        return users


    # --- Trust Decay ---
    def apply_trust_decay(self, inactivity_threshold_days: int, decay_amount: int, min_trust_level: int = 0, actor_user_id: str = "system") -> None:
        """
        Applies trust decay to users inactive for a specified period in TinyDB.

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

        users_table = self._get_users_table() # Get table instance now
        all_users = users_table.all()
        UserQuery = Query()

        for user_data in all_users:
            user_id = user_data.get('user_id')
            if not user_id: continue

            last_login_str = user_data.get('last_login')
            current_trust = user_data.get('trust_level', 0)

            is_inactive = False
            if last_login_str:
                try:
                    last_login_dt = datetime.fromisoformat(last_login_str.replace('Z', '+00:00'))
                    if last_login_dt.tzinfo is None:
                        last_login_dt = last_login_dt.replace(tzinfo=timezone.utc)
                    if last_login_dt < threshold_time:
                        is_inactive = True
                except ValueError:
                    logging.warning(f"Could not parse last_login timestamp '{last_login_str}' for user '{user_id}'. Treating as inactive for decay.")
                    is_inactive = True
            else:
                is_inactive = True

            if is_inactive and current_trust > min_trust_level:
                original_level = current_trust
                new_level = max(min_trust_level, original_level - decay_amount)
                if new_level < original_level:
                    users_table.update({'trust_level': new_level}, UserQuery.user_id == user_id)
                    log_desc = f"Applied trust decay to user '{user_id}'. New level: {new_level}"
                    self.audit_log.log_event(actor_user_id, "trust_decay_applied", log_desc)
                    logging.info(log_desc)
                    decayed_count += 1

        logging.info(f"Trust decay process completed. Decayed trust for {decayed_count} inactive users.")

