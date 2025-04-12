# tests/test_user.py

import unittest
from src.user import User, VALID_ROLES
# Import password functions from the correct module
from src.encryption import hash_password, check_password

class TestUser(unittest.TestCase):
    """Unit tests for the User class."""

    def setUp(self):
        """Set up common user data for tests."""
        # Use the imported hash_password function
        self.hashed_password = hash_password("password123")
        self.user_data = {
            "user_id": "testuser1",
            "email": "test@example.com",
            "password_hash": self.hashed_password,
            "role": "basic",
            "trust_level": 75,
            "last_login": "2024-01-01T10:00:00Z" # Example ISO format timestamp
        }
        self.user = User(**self.user_data)

    def test_user_creation_minimal(self):
        """Test creating a user with minimal required fields."""
        # Assuming user_id, email, password_hash are minimal requirements
        minimal_user = User("min_user", "min@example.com", hash_password("pass"))
        self.assertEqual(minimal_user.user_id, "min_user")
        self.assertEqual(minimal_user.email, "min@example.com")
        self.assertIsNotNone(minimal_user.password_hash)
        self.assertEqual(minimal_user.role, "guest") # Check default role
        self.assertEqual(minimal_user.trust_level, 0) # Check default trust level
        self.assertIsNone(minimal_user.last_login) # Check default last login

    def test_user_creation_full(self):
        """Test creating a user with all fields."""
        self.assertEqual(self.user.user_id, "testuser1")
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.password_hash, self.user_data["password_hash"])
        self.assertEqual(self.user.role, "basic")
        self.assertEqual(self.user.trust_level, 75)
        self.assertEqual(self.user.last_login, "2024-01-01T10:00:00Z")

    def test_user_creation_invalid_role(self):
        """Test creating a user with an invalid role."""
        invalid_data = self.user_data.copy()
        invalid_data["role"] = "invalid_role"
        with self.assertRaises(ValueError) as cm:
            User(**invalid_data)
        self.assertIn("Invalid role", str(cm.exception))
        self.assertIn("invalid_role", str(cm.exception))
        self.assertTrue(all(role in str(cm.exception) for role in VALID_ROLES))

    def test_user_creation_invalid_email(self):
        """Test creating a user with an invalid email format (warning check)."""
        # User.__post_init__ logs a warning but doesn't raise error by default
        invalid_data = self.user_data.copy()
        invalid_data["email"] = "not-an-email"
        # Expect a warning to be logged (can't easily assert log output here without more setup)
        user_invalid_email = User(**invalid_data)
        self.assertEqual(user_invalid_email.email, "not-an-email")


    def test_user_representation(self):
        """Test the string representation (__repr__) of a user."""
        expected_repr = f"User(user_id='{self.user.user_id}', email='{self.user.email}', role='{self.user.role}')"
        self.assertEqual(repr(self.user), expected_repr)

    def test_user_to_dict(self):
        """Test converting a User object to a dictionary."""
        # Test without hash
        user_dict_no_hash = self.user.to_dict()
        self.assertEqual(user_dict_no_hash["user_id"], self.user_data["user_id"])
        self.assertEqual(user_dict_no_hash["email"], self.user_data["email"])
        self.assertNotIn("password_hash", user_dict_no_hash) # Verify hash excluded

        # Test with hash
        user_dict_with_hash = self.user.to_dict(include_hash=True)
        self.assertEqual(user_dict_with_hash["password_hash"], self.user_data["password_hash"])


    def test_user_from_dict(self):
        """Test creating a User object from a dictionary."""
        created_user = User.from_dict(self.user_data)
        self.assertIsInstance(created_user, User)
        self.assertEqual(created_user.user_id, self.user_data["user_id"])
        self.assertEqual(created_user.email, self.user_data["email"])
        self.assertEqual(created_user.password_hash, self.user_data["password_hash"])
        self.assertEqual(created_user.role, self.user_data["role"])
        self.assertEqual(created_user.trust_level, self.user_data["trust_level"])
        self.assertEqual(created_user.last_login, self.user_data["last_login"])

    def test_user_from_dict_missing_keys(self):
        """Test creating from dict with missing required keys."""
        minimal_data = {"user_id": "u1", "email": "e@e.com", "password_hash": "h"}
        try:
            user = User.from_dict(minimal_data)
            # Check defaults for optional fields
            self.assertEqual(user.role, "guest")
            self.assertEqual(user.trust_level, 0)
            self.assertIsNone(user.last_login)
        except KeyError as e:
            self.fail(f"User.from_dict raised KeyError unexpectedly for optional fields: {e}")

        # Test missing required field (e.g., email)
        missing_req_data = {"user_id": "u1", "password_hash": "h"}
        with self.assertRaises(KeyError):
            User.from_dict(missing_req_data)

    def test_update_last_login(self):
        """Test the update_last_login method."""
        self.user.update_last_login()
        self.assertIsNotNone(self.user.last_login)
        # Check if it's a recent timestamp (this is tricky, check format or approximate time)
        # For simplicity, just check it's not the old value or None
        self.assertNotEqual(self.user.last_login, "2024-01-01T10:00:00Z")
        # Could also parse the date and check if it's close to datetime.now()

    def test_change_role(self):
        """Test changing the user's role."""
        self.assertTrue(self.user.change_role("administrator"))
        self.assertEqual(self.user.role, "administrator")

        # Test changing to an invalid role
        self.assertFalse(self.user.change_role("super_admin"))
        self.assertEqual(self.user.role, "administrator") # Role should not have changed

        # Test changing to the same role
        self.assertTrue(self.user.change_role("administrator")) # Should succeed
        self.assertEqual(self.user.role, "administrator")

    def test_adjust_trust(self):
        """Test adjusting the user's trust level."""
        initial_trust = self.user.trust_level # 75

        # Increase trust
        self.user.adjust_trust(10)
        self.assertEqual(self.user.trust_level, 85)

        # Decrease trust
        self.user.adjust_trust(-20)
        self.assertEqual(self.user.trust_level, 65)

        # Test clamping at max (assuming 100)
        self.user.adjust_trust(50)
        self.assertEqual(self.user.trust_level, 100)

        # Test clamping at min (assuming 0)
        self.user.trust_level = 10 # Reset for min test
        self.user.adjust_trust(-30)
        self.assertEqual(self.user.trust_level, 0)

    def test_password_hashing_and_checking(self):
        """Test the password hashing and checking functions (imported)."""
        password = "complex_password!@#"
        # Use imported hash_password
        hashed = hash_password(password)

        self.assertIsNotNone(hashed)
        self.assertNotEqual(password, hashed) # Hash should not be the same as password

        # Use imported check_password
        # Check correct password
        self.assertTrue(check_password(hashed, password))

        # Check incorrect password
        self.assertFalse(check_password(hashed, "wrong_password"))

        # Check against different hash
        different_hash = hash_password("another_password")
        self.assertFalse(check_password(different_hash, password))


    def test_equality_and_hash(self):
        """Test equality and hashing based on user_id."""
        user1 = User("user1", "test1@example.com", "hash1", role="basic")
        # Use the correct role 'administrator' instead of 'admin'
        user_copy = User("user1", "diff@example.com", "hash_copy", role="administrator") # Same ID
        user_different_id = User("user2", "test1@example.com", "hash1", role="basic") # Different ID

        # Test equality (should be based on user_id)
        self.assertEqual(user1, user_copy)
        self.assertNotEqual(user1, user_different_id)

        # Test hash (should be based on user_id)
        self.assertEqual(hash(user1), hash(user_copy))
        self.assertNotEqual(hash(user1), hash(user_different_id))

        # Test comparison with other types
        self.assertNotEqual(user1, "user1")
        self.assertNotEqual(user1, None)

if __name__ == '__main__':
    unittest.main()
