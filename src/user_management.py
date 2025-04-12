import uuid
import os
from .user import User
from .encryption import hash_password, verify_password
# Use load_data and save_data instead of the non-existent get_user_db
from .db_utils import load_data, save_data
from .audit_log import log_audit

class UserManagement:
    """
    Handles user registration, login, and data persistence.
    """
    def __init__(self, users_file_path='data/users.json', audit_log_path='data/audit.log'):
        """
        Initializes the UserManagement system.

        Args:
            users_file_path (str): Path to the JSON file storing user data.
            audit_log_path (str): Path to the audit log file.
        """
        self.users_file_path = users_file_path
        self.audit_log_path = audit_log_path
        # Ensure the directory for the users file exists
        os.makedirs(os.path.dirname(users_file_path), exist_ok=True)
        self.users = self._load_users() # Load users on initialization

    def _load_users(self):
        """Loads users from the JSON file."""
        users_data = load_data(self.users_file_path)
        if users_data:
            # Assuming users_data is a dictionary {user_id: user_dict}
            return {uid: User.from_dict(udata) for uid, udata in users_data.items()}
        else:
            # If file not found, empty, or invalid, start with an empty dictionary
            return {}

    def _save_users(self):
        """Saves the current users dictionary to the JSON file."""
        # Convert User objects back to dictionaries for saving
        users_data_to_save = {uid: user.to_dict() for uid, user in self.users.items()}
        save_data(self.users_file_path, users_data_to_save)
        # Optional: Add audit log for saving users if needed, though might be noisy
        # log_audit(self.audit_log_path, "system", "save_users", "success")


    def register_user(self, username, password):
        """
        Registers a new user.

        Args:
            username (str): The desired username.
            password (str): The user's password.

        Returns:
            User: The newly registered User object, or None if username already exists.
        """
        # Check if username already exists (case-insensitive check)
        if any(user.username.lower() == username.lower() for user in self.users.values()):
            print(f"Username '{username}' already exists.")
            # Log audit failure - username exists handled in calling function (app.py)
            return None

        # Hash the password
        password_hash = hash_password(password)
        if not password_hash:
            print("Error hashing password during registration.")
            log_audit(self.audit_log_path, username, 'register', 'failure - password hash error')
            return None # Indicate failure

        # Create new user
        user_id = str(uuid.uuid4())
        new_user = User(user_id, username, password_hash)
        self.users[user_id] = new_user

        # Save updated user list
        self._save_users()
        print(f"User '{username}' registered successfully.")
        # Log audit success - handled in calling function (app.py)
        return new_user

    def login_user(self, username, password):
        """
        Logs in a user.

        Args:
            username (str): The username.
            password (str): The password.

        Returns:
            User: The User object if login is successful, None otherwise.
        """
        # Find user by username (case-insensitive)
        user_to_check = None
        for user in self.users.values():
            if user.username.lower() == username.lower():
                user_to_check = user
                break

        if user_to_check:
            # Verify password
            if verify_password(password, user_to_check.password_hash):
                print(f"User '{username}' logged in successfully.")
                # Log audit success - handled in calling function (app.py)
                return user_to_check
            else:
                print(f"Invalid password for user '{username}'.")
                # Log audit failure - handled in calling function (app.py)
                return None
        else:
            print(f"Username '{username}' not found.")
            # Log audit failure - handled in calling function (app.py)
            return None

    def find_user_by_id(self, user_id):
        """
        Finds a user by their ID.

        Args:
            user_id (str): The ID of the user to find.

        Returns:
            User: The found User object, or None if not found.
        """
        return self.users.get(user_id)

    def find_user_by_username(self, username):
        """
        Finds a user by their username (case-insensitive).

        Args:
            username (str): The username to find.

        Returns:
            User: The found User object, or None if not found.
        """
        for user in self.users.values():
            if user.username.lower() == username.lower():
                return user
        return None

