# Modify src/user.py to add reset token fields
import base64
import logging
from datetime import datetime, timedelta # Import datetime and timedelta

# Define valid roles
VALID_ROLES = ["basic", "admin"]

class User:
    """Represents a user of the application."""
    def __init__(self, user_id, username, password_hash, role="basic",
                 reset_token=None, reset_token_expiry=None): # Add token fields
        """
        Initializes a User object.

        Args:
            user_id (str): The unique ID for the user.
            username (str): The user's chosen username.
            password_hash (bytes): The bcrypt hashed password (as bytes).
            role (str): The user's role (e.g., 'basic', 'admin'). Defaults to 'basic'.
            reset_token (str, optional): Password reset token. Defaults to None.
            reset_token_expiry (datetime, optional): Expiry time for the reset token. Defaults to None.
        """
        if not username:
            logging.warning("Username cannot be empty during User initialization.")
            # raise ValueError("Username cannot be empty") # Optionally raise error

        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash # Should be bytes

        # Validate and set role
        if role not in VALID_ROLES:
            logging.warning(f"Invalid role '{role}' provided for user {username}. Defaulting to 'basic'. Valid roles are: {VALID_ROLES}")
            self.role = "basic"
        else:
            self.role = role

        # Set reset token details
        self.reset_token = reset_token
        # Ensure expiry is datetime object if provided
        if isinstance(reset_token_expiry, str):
            try:
                self.reset_token_expiry = datetime.fromisoformat(reset_token_expiry)
            except (ValueError, TypeError):
                logging.warning(f"Invalid reset token expiry format '{reset_token_expiry}' for user {username}. Setting to None.")
                self.reset_token_expiry = None
        else:
             self.reset_token_expiry = reset_token_expiry


    def to_dict(self):
        """
        Converts the User object to a dictionary suitable for JSON serialization.
        Stores the password hash as a base64 encoded string for better compatibility.
        Stores datetime as ISO format string.
        """
        hash_str = base64.b64encode(self.password_hash).decode('utf-8') if isinstance(self.password_hash, bytes) else None
        if not hash_str and self.password_hash is not None:
             logging.warning(f"Password hash for user {self.username} is not bytes, cannot serialize properly.")
             hash_str = None

        expiry_str = self.reset_token_expiry.isoformat() if self.reset_token_expiry else None

        return {
            "user_id": self.user_id,
            "username": self.username,
            "password_hash_b64": hash_str,
            "role": self.role,
            "reset_token": self.reset_token, # Add token
            "reset_token_expiry": expiry_str # Add expiry string
        }

    @classmethod
    def from_dict(cls, data):
        """
        Creates a User object from a dictionary (e.g., loaded from JSON).
        Expects the password hash to be a base64 encoded string.
        Parses expiry string back to datetime.
        """
        user_id = data.get("user_id")
        username = data.get("username")
        password_hash_b64 = data.get("password_hash_b64")
        role = data.get("role", "basic")
        reset_token = data.get("reset_token") # Get token
        reset_token_expiry_str = data.get("reset_token_expiry") # Get expiry string

        password_hash_bytes = None
        if password_hash_b64:
            try:
                password_hash_bytes = base64.b64decode(password_hash_b64.encode('utf-8'))
            except (base64.binascii.Error, TypeError, ValueError) as e:
                 logging.warning(f"Could not decode password hash for user {username} from base64: {e}")
                 password_hash_bytes = None
        else:
             old_hash_str = data.get("password_hash")
             if isinstance(old_hash_str, str):
                 logging.warning(f"Found old string hash format for user {username}. Attempting to encode.")
                 try:
                     password_hash_bytes = old_hash_str.encode('utf-8')
                 except Exception as enc_e:
                      logging.error(f"Could not encode old string hash for user {username}: {enc_e}")
                      password_hash_bytes = None

        reset_token_expiry = None
        if reset_token_expiry_str:
            try:
                reset_token_expiry = datetime.fromisoformat(reset_token_expiry_str)
            except (ValueError, TypeError):
                 logging.warning(f"Invalid reset token expiry format '{reset_token_expiry_str}' in data for user {username}. Setting expiry to None.")
                 reset_token_expiry = None


        if not user_id:
             raise ValueError("User ID is missing in user data.")

        try:
            return cls(
                user_id=user_id,
                username=username,
                password_hash=password_hash_bytes,
                role=role,
                reset_token=reset_token, # Pass token
                reset_token_expiry=reset_token_expiry # Pass expiry datetime
            )
        except ValueError as e:
            logging.error(f"Failed to create User object from dict for user ID {user_id}: {e}")
            raise

    def __repr__(self):
         return f"User(user_id='{self.user_id}', username='{self.username}', role='{self.role}')"