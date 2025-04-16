# src/user.py
import base64 # Using base64 for slightly better hash storage than raw bytes string

class User:
    """Represents a user of the application."""
    def __init__(self, user_id, username, password_hash):
        """
        Initializes a User object.

        Args:
            user_id (str): The unique ID for the user.
            username (str): The user's chosen username.
            password_hash (bytes): The bcrypt hashed password (as bytes).
        """
        self.user_id = user_id
        self.username = username # Ensure this attribute is assigned
        self.password_hash = password_hash # Should be bytes

    def to_dict(self):
        """
        Converts the User object to a dictionary suitable for JSON serialization.
        Stores the password hash as a base64 encoded string for better compatibility.
        """
        # Encode bytes hash to base64 string for JSON storage
        hash_str = base64.b64encode(self.password_hash).decode('utf-8') if isinstance(self.password_hash, bytes) else None
        if not hash_str:
             print(f"Warning: Password hash for user {self.username} is not bytes, cannot serialize properly.")
             # Decide how to handle this - store None, empty string, or raise error?
             hash_str = None # Store None if hash wasn't bytes

        return {
            "user_id": self.user_id,
            "username": self.username,
            "password_hash_b64": hash_str # Store base64 string
        }

    @classmethod
    def from_dict(cls, data):
        """
        Creates a User object from a dictionary (e.g., loaded from JSON).
        Expects the password hash to be a base64 encoded string.
        """
        user_id = data.get("user_id")
        username = data.get("username") # Get username from data
        password_hash_b64 = data.get("password_hash_b64") # Get base64 hash string

        password_hash_bytes = None
        if password_hash_b64:
            try:
                # Decode base64 string back to bytes
                password_hash_bytes = base64.b64decode(password_hash_b64.encode('utf-8'))
            except (base64.binascii.Error, TypeError, ValueError) as e:
                 print(f"Warning: Could not decode password hash for user {username} from base64: {e}")
                 # Decide how to handle - set hash to None, raise error?
                 password_hash_bytes = None # Set to None if decoding fails
        else:
             # Handle case where hash might be missing or stored under old key 'password_hash'
             # For backward compatibility, you might check data.get('password_hash') here
             # and try to encode it if it exists.
             old_hash_str = data.get("password_hash")
             if isinstance(old_hash_str, str):
                 print(f"Warning: Found old hash format for user {username}. Attempting to encode.")
                 password_hash_bytes = old_hash_str.encode('utf-8')
             else:
                 print(f"Warning: Missing or invalid password hash for user {username}.")


        # Ensure username is assigned, even if it's None from the data
        return cls(
            user_id=user_id,
            username=username, # Assigns the value retrieved from data.get("username")
            password_hash=password_hash_bytes # Store as bytes (or None if failed)
        )

