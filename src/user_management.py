# src/user_management.py
import uuid
import os
# Import User and password functions from their respective modules
from .user import User
from .encryption import hash_password, verify_password
# Use load_data and save_data from db_utils
from .db_utils import load_data, save_data
# Import the audit log function
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
        # Use os.path.dirname to get the directory part of the path
        users_dir = os.path.dirname(users_file_path)
        if users_dir: # Check if path includes a directory
             os.makedirs(users_dir, exist_ok=True)
        else:
             # Handle case where path is just a filename in the current directory
             # No directory creation needed, but good to be aware
             pass
        self.users = self._load_users() # Load users on initialization

    def _load_users(self):
        """Loads users from the JSON file."""
        users_data = load_data(self.users_file_path)
        loaded_users = {}
        if users_data:
            # Assuming users_data is a dictionary {user_id: user_dict}
            for uid, udata in users_data.items():
                 try:
                     # Attempt to create User object from dictionary
                     user_obj = User.from_dict(udata)
                     # Basic validation: Ensure user has a username after loading
                     if user_obj.username is None:
                         print(f"Warning: Loaded user data for ID {uid} is missing a username. Skipping this user.")
                         log_audit(self.audit_log_path, "system", "load_users", f"warning - user data missing username for ID {uid}")
                         continue # Skip adding this user to the manager
                     loaded_users[uid] = user_obj
                 except KeyError as e:
                     # Log error if essential keys are missing in user data during load
                     print(f"Error loading user data for ID {uid}: Missing key {e}. Skipping this user.")
                     log_audit(self.audit_log_path, "system", "load_users", f"error - user data missing key {e} for ID {uid}")
                 except Exception as e:
                     # Catch other potential errors during User.from_dict
                     print(f"Error creating User object for ID {uid}: {e}. Skipping this user.")
                     log_audit(self.audit_log_path, "system", "load_users", f"error - creating user object failed for ID {uid}: {e}")
            return loaded_users
        else:
            # If file not found, empty, or invalid, start with an empty dictionary
            print(f"No user data found or error loading from {self.users_file_path}. Starting with empty user list.")
            return {}

    def _save_users(self):
        """Saves the current users dictionary to the JSON file."""
        try:
            # Convert User objects back to dictionaries for saving
            users_data_to_save = {uid: user.to_dict() for uid, user in self.users.items()}
            save_data(self.users_file_path, users_data_to_save)
            # Optional: Add audit log for saving users if needed, though might be noisy
            # log_audit(self.audit_log_path, "system", "save_users", "success")
        except Exception as e:
             # Log error if saving fails
             print(f"Error saving user data to {self.users_file_path}: {e}")
             log_audit(self.audit_log_path, "system", "save_users", f"failure: {e}")


    def register_user(self, username, password):
        """
        Registers a new user.

        Args:
            username (str): The desired username. Must not be empty.
            password (str): The user's password. Must not be empty.

        Returns:
            User: The newly registered User object, or None if registration fails.
        """
        # --- Input Validation ---
        if not username:
            print("Registration failed: Username cannot be empty.")
            log_audit(self.audit_log_path, "(registration attempt)", 'register', 'failure - empty username')
            return None
        if not password:
            print("Registration failed: Password cannot be empty.")
            log_audit(self.audit_log_path, username, 'register', 'failure - empty password')
            return None

        # --- Check for Existing Username ---
        # Case-insensitive check
        if any(user.username and user.username.lower() == username.lower() for user in self.users.values()):
            print(f"Registration failed: Username '{username}' already exists.")
            log_audit(self.audit_log_path, username, 'register', 'failure - username exists')
            return None

        # --- Hash Password ---
        password_hash = hash_password(password)
        if not password_hash:
            print(f"Error hashing password during registration for '{username}'.")
            log_audit(self.audit_log_path, username, 'register', 'failure - password hash error')
            return None # Indicate failure

        # --- Create and Store User ---
        try:
            user_id = str(uuid.uuid4())
            # Create new user - ensure username is passed correctly
            new_user = User(user_id=user_id, username=username, password_hash=password_hash)
            self.users[user_id] = new_user

            # --- Save Updated User List ---
            self._save_users() # Save immediately after successful addition
            print(f"User '{username}' registered successfully.")
            # Log audit success - handled in calling function (app.py) which calls this
            return new_user
        except Exception as e:
             # Catch potential errors during User creation or saving
             print(f"An error occurred during the final steps of registration for '{username}': {e}")
             log_audit(self.audit_log_path, username, 'register', f'failure - internal error: {e}')
             # Attempt to remove the partially added user if necessary (though unlikely here)
             if user_id in self.users:
                 del self.users[user_id]
             return None


    def login_user(self, username, password):
        """
        Logs in a user.

        Args:
            username (str): The username.
            password (str): The password.

        Returns:
            User: The User object if login is successful, None otherwise.
        """
        user_to_check = None
        # Find user by username (case-insensitive)
        for user in self.users.values():
            # --- DEFENSIVE CHECK ADDED ---
            # Ensure user.username is not None before calling .lower()
            # This prevents AttributeError if data is corrupted or loaded incorrectly.
            if user.username and user.username.lower() == username.lower():
                user_to_check = user
                break # Found the user, exit loop

        if user_to_check:
            # Verify password using the function from encryption module
            # Ensure the stored hash is bytes, as expected by verify_password
            if isinstance(user_to_check.password_hash, bytes):
                if verify_password(password, user_to_check.password_hash):
                    print(f"User '{username}' logged in successfully.")
                    # Log audit success - handled in calling function (app.py)
                    # Optionally update last login time here
                    # user_to_check.update_last_login() # Assuming User class has this method
                    # self._save_users() # Save if last login was updated
                    return user_to_check
                else:
                    print(f"Invalid password for user '{username}'.")
                    # Log audit failure - handled in calling function (app.py)
                    return None
            else:
                 # Log error if password hash is not in the expected bytes format
                 print(f"Login failed for '{username}': Stored password hash is not in the correct format.")
                 log_audit(self.audit_log_path, username, 'login', 'failure - invalid stored hash format')
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
        if not username: # Handle empty username search
             return None
        for user in self.users.values():
            # Check if user.username exists before comparing
            if user.username and user.username.lower() == username.lower():
                return user
        return None

