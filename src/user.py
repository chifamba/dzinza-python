# src/user.py
from datetime import datetime, timedelta
from typing import List, Optional # Import necessary types

VALID_ROLES = ['basic', 'trusted', 'administrator', 'family_historian', 'guest']
TRUST_LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 200,
    4: 300,
    5: 400
} # Points required for each level

class User:
    """
    Represents a user of the application.

    Attributes:
        user_id (str): Unique identifier for the user.
        email (str): User's email address (used for login).
        password_hash (str): Hashed password for security.
        trust_points (int): Points accumulated based on activity and verification.
        role (str): User role determining permissions (e.g., 'basic', 'trusted').
        family_group_spaces (List[str]): IDs of family groups the user belongs to.
        last_login (datetime): Timestamp of the last login.
        created_at (datetime): Timestamp when the user was created.
    """
    def __init__(self, user_id: str, email: str, password_hash: str, role: str = 'basic'):
        """
        Initializes a User object.

        Args:
            user_id (str): The unique identifier for the user.
            email (str): The email address of the user.
            password_hash (str): The hashed password.
            role (str): The initial role of the user. Defaults to 'basic'.

        Raises:
            ValueError: If the provided role is invalid.
        """
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Valid roles are: {VALID_ROLES}")

        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash # Store hash, not plain password
        self.trust_points: int = 0
        self.role: str = role
        self.family_group_spaces: List[str] = []
        self.last_login: datetime = datetime.now()
        self.created_at: datetime = datetime.now()

    def check_password(self, password_to_check: str) -> bool:
        """
        Checks if the provided password matches the stored hash.
        NOTE: Requires a password hashing library (e.g., passlib, werkzeug.security).
              This is a placeholder implementation.

        Args:
            password_to_check (str): The plain text password to check.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        # Placeholder - Replace with actual hash comparison
        # from werkzeug.security import check_password_hash # Example
        # return check_password_hash(self.password_hash, password_to_check)
        print("Warning: Password check is a placeholder and not secure.")
        return self.password_hash == password_to_check # Insecure placeholder comparison

    def update_last_login(self):
        """Updates the last login timestamp to the current time."""
        self.last_login = datetime.now()

    def set_role(self, new_role: str):
        """
        Sets the user's role.

        Args:
            new_role (str): The new role to assign.

        Raises:
            ValueError: If the new role is not valid.
        """
        if new_role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {new_role}. Valid roles are: {VALID_ROLES}")
        self.role = new_role

    def add_trust_points(self, points: int):
        """
        Adds trust points to the user.

        Args:
            points (int): The number of trust points to add (must be non-negative).

        Raises:
            ValueError: If points are negative.
        """
        if points < 0:
            raise ValueError("Points must be a non-negative number.")
        self.trust_points += points
        # Optional: Update role automatically based on new points?
        # self.role = self._calculate_role_based_on_trust()

    def remove_trust_points(self, points: int):
        """
        Removes trust points from the user.

        Args:
            points (int): The number of trust points to remove (must be non-negative).

        Raises:
            ValueError: If points are negative.
        """
        if points < 0:
            raise ValueError("Points must be a non-negative number.")
        self.trust_points = max(0, self.trust_points - points) # Ensure points don't go below zero
        # Optional: Update role automatically based on new points?
        # self.role = self._calculate_role_based_on_trust()


    def get_trust_level(self) -> int:
        """
        Calculates the trust level based on current trust points.

        Returns:
            int: The calculated trust level (1-5).
        """
        level = 1
        for lvl, threshold in sorted(TRUST_LEVEL_THRESHOLDS.items(), reverse=True):
            if self.trust_points >= threshold:
                level = lvl
                break
        return level

    def add_family_group(self, family_group_id: str):
        """Adds a family group ID to the user's list if not already present."""
        if family_group_id not in self.family_group_spaces:
            self.family_group_spaces.append(family_group_id)
        # else: raise ValueError(f"User {self.user_id} already in family group {family_group_id}.")

    def remove_family_group(self, family_group_id: str):
        """Removes a family group ID from the user's list."""
        if family_group_id in self.family_group_spaces:
            self.family_group_spaces.remove(family_group_id)
        else:
            raise ValueError(f"User {self.user_id} is not in family group {family_group_id}.")

    def is_inactive(self, days_threshold: int = 30) -> bool:
        """
        Checks if the user has been inactive for a specified number of days.

        Args:
            days_threshold (int): The number of days of inactivity to check against.

        Returns:
            bool: True if the user's last login was longer ago than the threshold, False otherwise.
        """
        inactive_threshold = datetime.now() - timedelta(days=days_threshold)
        return self.last_login < inactive_threshold

    def __str__(self) -> str:
        """String representation of the User object."""
        return f"User(id={self.user_id}, email={self.email}, role={self.role}, trust_pts={self.trust_points})"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"<User {self.user_id} - {self.email}>"

    def __eq__(self, other: object) -> bool:
        """Equality check based on user_id."""
        if not isinstance(other, User):
            return NotImplemented
        return self.user_id == other.user_id

    def __hash__(self) -> int:
        """Hash based on user_id."""
        return hash(self.user_id)

