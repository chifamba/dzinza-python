# src/user.py

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import logging
import re # For email validation

# Define valid user roles
VALID_ROLES = ["basic", "trusted", "administrator", "family_historian", "guest"]

# Basic email validation regex (adjust as needed for stricter validation)
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

@dataclass
class User:
    """Represents a user account in the system."""
    user_id: str
    email: str
    password_hash: str # Store hashed password, not plaintext
    role: str = "guest" # Default role
    trust_level: int = 0 # Example: 0-100 trust score
    last_login: Optional[str] = None # Store as ISO 8601 string for JSON compatibility
    attributes: Dict[str, Any] = field(default_factory=dict) # For extra user info

    def __post_init__(self):
        """Validate data after initialization."""
        if not re.match(EMAIL_REGEX, self.email):
             # Decide whether to raise error or just log warning
             logging.warning(f"User '{self.user_id}' created with potentially invalid email: {self.email}")
             # raise ValueError(f"Invalid email format: {self.email}") # Uncomment to enforce

        if self.role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {self.role}. Valid roles are: {VALID_ROLES}")

        if not isinstance(self.trust_level, int) or not (0 <= self.trust_level <= 100):
             logging.warning(f"User '{self.user_id}' trust level ({self.trust_level}) outside expected range [0, 100]. Clamping.")
             self.trust_level = max(0, min(100, self.trust_level)) # Clamp value

        # Ensure attributes is a dict
        if self.attributes is None:
            self.attributes = {}

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"User(user_id='{self.user_id}', email='{self.email}', role='{self.role}')"

    def __eq__(self, other: object) -> bool:
        """Checks equality based on user_id."""
        if not isinstance(other, User):
            return NotImplemented
        return self.user_id == other.user_id

    def __hash__(self) -> int:
        """Computes hash based on user_id."""
        return hash(self.user_id)

    def to_dict(self, include_hash: bool = False) -> Dict[str, Any]:
        """Converts the User object to a dictionary. Excludes password hash by default."""
        data = {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "trust_level": self.trust_level,
            "last_login": self.last_login,
            "attributes": self.attributes,
        }
        if include_hash:
            data["password_hash"] = self.password_hash
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Creates a User object from a dictionary."""
        # Basic validation for required fields
        required_keys = ["user_id", "email", "password_hash"]
        if not all(key in data for key in required_keys):
             missing = [key for key in required_keys if key not in data]
             raise KeyError(f"User data dictionary missing required keys: {missing}")

        return cls(
            user_id=data['user_id'],
            email=data['email'],
            password_hash=data['password_hash'],
            role=data.get('role', 'guest'), # Provide default if missing
            trust_level=data.get('trust_level', 0), # Provide default
            last_login=data.get('last_login'), # Okay if None
            attributes=data.get('attributes', {}) # Provide default
        )

    def update_last_login(self) -> None:
        """Updates the last_login timestamp to the current time (UTC)."""
        self.last_login = datetime.now(timezone.utc).isoformat()
        logging.debug(f"Updated last login for user '{self.user_id}' to {self.last_login}")

    def change_role(self, new_role: str) -> bool:
        """
        Changes the user's role if the new role is valid.

        Returns:
            True if the role was changed, False otherwise.
        """
        if new_role in VALID_ROLES:
            if self.role != new_role:
                self.role = new_role
                logging.info(f"Changed role for user '{self.user_id}' to '{new_role}'.")
                return True
            else:
                logging.debug(f"User '{self.user_id}' already has role '{new_role}'. No change made.")
                return True # Indicate success even if no change occurred
        else:
            logging.warning(f"Attempted to change role for user '{self.user_id}' to invalid role '{new_role}'.")
            return False

    def adjust_trust(self, amount: int) -> None:
        """
        Adjusts the user's trust level by the given amount, clamping between 0 and 100.
        """
        new_trust_level = self.trust_level + amount
        clamped_trust_level = max(0, min(100, new_trust_level))
        if clamped_trust_level != self.trust_level:
            self.trust_level = clamped_trust_level
            logging.debug(f"Adjusted trust level for user '{self.user_id}' by {amount}. New level: {self.trust_level}")
        else:
             logging.debug(f"Trust level for user '{self.user_id}' remains {self.trust_level} after adjustment by {amount} (due to clamping or zero change).")

    # Note: Password setting/changing logic might live in UserManager
    # to handle hashing and security checks properly.
    # If needed here, import hash_password from encryption.py
    # from .encryption import hash_password
    # def set_password(self, new_password: str):
    #     self.password_hash = hash_password(new_password)
    #     logging.info(f"Password updated for user '{self.user_id}'.")

