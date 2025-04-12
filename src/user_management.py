# src/user_management.py
from typing import Dict, Optional

from src.user import User, VALID_ROLES
from src.audit_log import AuditLog # Import placeholder

# Placeholder for password hashing - USE A REAL LIBRARY like passlib or werkzeug
# from werkzeug.security import generate_password_hash, check_password_hash # Example
def placeholder_hash_password(password: str) -> str:
    print("Warning: Using placeholder password hashing (NOT SECURE).")
    return password # Insecure placeholder

def placeholder_check_password(hashed_password: str, password_to_check: str) -> bool:
     print("Warning: Using placeholder password checking (NOT SECURE).")
     return hashed_password == password_to_check # Insecure placeholder

class UserManager:
    """
    Manages user accounts, authentication, and roles.

    Attributes:
        users (Dict[str, User]): Dictionary mapping user_id to User object.
        users_by_email (Dict[str, User]): Dictionary mapping email to User object for quick lookup.
        audit_log (AuditLog): Instance for logging user management actions.
    """
    def __init__(self, audit_log: Optional[AuditLog] = None):
        """
        Initializes the UserManager.

        Args:
            audit_log (Optional[AuditLog]): An instance of AuditLog.
        """
        self.users: Dict[str, User] = {}
        self.users_by_email: Dict[str, User] = {}
        self.audit_log = audit_log if audit_log else AuditLog() # Use placeholder if none provided

    def create_user(self, user_id: str, email: str, password: str, role: str = 'basic', acting_user_id: str = "system") -> User:
        """
        Creates a new user, hashes the password, and adds them to the manager.

        Args:
            user_id (str): The desired unique user ID.
            email (str): The user's email address.
            password (str): The user's plain text password.
            role (str): The initial role for the user.
            acting_user_id (str): The ID of the user performing the creation (for audit).

        Returns:
            User: The newly created User object.

        Raises:
            ValueError: If user ID or email already exists, or if the role is invalid.
        """
        if user_id in self.users:
            raise ValueError(f"User ID '{user_id}' already exists.")
        if email.lower() in self.users_by_email:
            raise ValueError(f"Email '{email}' is already in use.")
        if role not in VALID_ROLES:
             raise ValueError(f"Invalid role: {role}. Valid roles are: {VALID_ROLES}")

        # --- Password Hashing ---
        # Use a real hashing library here!
        password_hash = placeholder_hash_password(password)

        user = User(user_id, email.lower(), password_hash, role)
        self.users[user.user_id] = user
        self.users_by_email[user.email] = user

        self.audit_log.log_event(acting_user_id, "user_created", f"Created user: {user.user_id} ({user.email}), role: {user.role}")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Retrieves a user by their user ID."""
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email address (case-insensitive)."""
        return self.users_by_email.get(email.lower())

    def update_user(self, user_id: str,
                    new_email: Optional[str] = None,
                    new_password: Optional[str] = None,
                    new_role: Optional[str] = None,
                    acting_user_id: str = "system"):
        """
        Updates a user's email, password, or role.

        Args:
            user_id (str): The ID of the user to update.
            new_email (Optional[str]): The new email address.
            new_password (Optional[str]): The new plain text password.
            new_role (Optional[str]): The new role.
            acting_user_id (str): The ID of the user performing the update.

        Raises:
            ValueError: If the user is not found, the new email is already taken,
                        or the new role is invalid.
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User with ID '{user_id}' not found.")

        log_details = []

        # Update Email
        if new_email is not None and new_email.lower() != user.email:
            new_email_lower = new_email.lower()
            if new_email_lower in self.users_by_email:
                raise ValueError(f"Email '{new_email}' is already in use.")
            # Update mapping
            del self.users_by_email[user.email]
            user.email = new_email_lower
            self.users_by_email[user.email] = user
            log_details.append(f"email updated to {user.email}")

        # Update Password
        if new_password is not None:
            # Use a real hashing library here!
            user.password_hash = placeholder_hash_password(new_password)
            log_details.append("password updated")

        # Update Role
        if new_role is not None and new_role != user.role:
            user.set_role(new_role) # set_role includes validation
            log_details.append(f"role updated to {user.role}")

        if log_details:
             self.audit_log.log_event(acting_user_id, "user_updated", f"Updated user {user_id}: {', '.join(log_details)}")
        else:
             self.audit_log.log_event(acting_user_id, "user_updated", f"Attempted update for user {user_id}, but no changes were made.")


    def delete_user(self, user_id: str, acting_user_id: str = "system"):
        """
        Deletes a user from the system.

        Args:
            user_id (str): The ID of the user to delete.
            acting_user_id (str): The ID of the user performing the deletion.

        Raises:
            ValueError: If the user is not found.
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User with ID '{user_id}' not found.")

        # Remove from dictionaries
        del self.users[user_id]
        del self.users_by_email[user.email]

        self.audit_log.log_event(acting_user_id, "user_deleted", f"Deleted user: {user_id} ({user.email})")

    def validate_user_credentials(self, email: str, password: str) -> Optional[User]:
        """
        Validates user login credentials.

        Args:
            email (str): The user's email.
            password (str): The user's plain text password.

        Returns:
            Optional[User]: The User object if credentials are valid, None otherwise.
        """
        user = self.get_user_by_email(email)
        if user:
            # Use a real password checking function here!
            if placeholder_check_password(user.password_hash, password):
                user.update_last_login()
                self.audit_log.log_event(user.user_id, "login_success", f"User {user.user_id} logged in successfully.")
                return user
            else:
                 self.audit_log.log_event(email, "login_failed", f"Login failed for email {email} (incorrect password).")
        else:
            self.audit_log.log_event(email, "login_failed", f"Login failed for email {email} (user not found).")

        return None

    # --- Role and Trust Management ---

    def change_user_role(self, user_id: str, new_role: str, acting_user_id: str):
        """Changes the role of a specific user."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")
        if user.role == new_role:
             print(f"User {user_id} already has role {new_role}.")
             return # No change needed

        try:
            user.set_role(new_role)
            self.audit_log.log_event(acting_user_id, "role_change", f"Changed role for user {user_id} to {new_role}.")
        except ValueError as e:
            self.audit_log.log_event(acting_user_id, "role_change_failed", f"Failed to change role for user {user_id} to {new_role}: {e}")
            raise e

    def add_trust_points(self, user_id: str, points: int, reason: str, acting_user_id: str):
        """Adds trust points to a user."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")
        try:
            user.add_trust_points(points)
            self.audit_log.log_event(acting_user_id, "trust_points_added", f"Added {points} trust points to user {user_id}. Reason: {reason}. New total: {user.trust_points}.")
        except ValueError as e:
             self.audit_log.log_event(acting_user_id, "trust_points_failed", f"Failed to add trust points to user {user_id}: {e}")
             raise e

    def remove_trust_points(self, user_id: str, points: int, reason: str, acting_user_id: str):
        """Removes trust points from a user."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")
        try:
            user.remove_trust_points(points)
            self.audit_log.log_event(acting_user_id, "trust_points_removed", f"Removed {points} trust points from user {user_id}. Reason: {reason}. New total: {user.trust_points}.")
        except ValueError as e:
             self.audit_log.log_event(acting_user_id, "trust_points_failed", f"Failed to remove trust points from user {user_id}: {e}")
             raise e

    def apply_trust_decay(self, days_threshold: int = 30, decay_points: int = 50, acting_user_id: str = "system"):
        """Applies trust point decay to inactive users."""
        self.audit_log.log_event(acting_user_id, "trust_decay_start", f"Starting trust decay check (threshold: {days_threshold} days).")
        decayed_count = 0
        for user in self.users.values():
            if user.is_inactive(days_threshold) and user.trust_points > 0: # Only decay if points > 0
                points_to_remove = min(decay_points, user.trust_points) # Don't remove more than they have
                if points_to_remove > 0:
                    try:
                        user.remove_trust_points(points_to_remove)
                        self.audit_log.log_event(acting_user_id, "trust_decay_applied", f"Applied trust decay (-{points_to_remove} points) to inactive user {user.user_id}. New total: {user.trust_points}.")
                        decayed_count += 1
                    except ValueError as e: # Should not happen with max(0, ...)
                         self.audit_log.log_event(acting_user_id, "trust_decay_error", f"Error applying decay to user {user.user_id}: {e}")

        self.audit_log.log_event(acting_user_id, "trust_decay_end", f"Trust decay check complete. Applied decay to {decayed_count} users.")

