# tests/test_user.py
import unittest
from datetime import datetime, timedelta

from src.user import User, VALID_ROLES, TRUST_LEVEL_THRESHOLDS

class TestUser(unittest.TestCase):
    """Test suite for the refactored User class."""

    def setUp(self):
        """Create a default user for tests."""
        self.user = User("user1", "test@example.com", "hashed_password") # Default role 'basic'

    def test_user_initialization(self):
        """Test attributes after basic initialization."""
        self.assertEqual(self.user.user_id, "user1")
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.password_hash, "hashed_password")
        self.assertEqual(self.user.role, "basic")
        self.assertEqual(self.user.trust_points, 0)
        self.assertEqual(self.user.family_group_spaces, [])
        self.assertIsInstance(self.user.last_login, datetime)
        self.assertIsInstance(self.user.created_at, datetime)

    def test_initialization_with_role(self):
        """Test initializing with a specific valid role."""
        admin_user = User("admin1", "admin@example.com", "hash2", role="administrator")
        self.assertEqual(admin_user.role, "administrator")

    def test_initialization_invalid_role(self):
        """Test initializing with an invalid role raises ValueError."""
        with self.assertRaisesRegex(ValueError, "Invalid role"):
            User("user2", "fail@example.com", "hash3", role="invalid_role")

    def test_check_password_placeholder(self):
        """Test the placeholder password check."""
        # Assumes placeholder check is simple equality
        self.assertTrue(self.user.check_password("hashed_password"))
        self.assertFalse(self.user.check_password("wrong_password"))
        # NOTE: This test MUST be updated when real hashing is implemented.

    def test_update_last_login(self):
        """Test updating the last login time."""
        initial_login_time = self.user.last_login
        # Need to ensure time progresses enough to see a difference
        import time; time.sleep(0.01)
        self.user.update_last_login()
        self.assertGreater(self.user.last_login, initial_login_time)

    def test_set_role(self):
        """Test setting a valid role."""
        self.user.set_role("trusted")
        self.assertEqual(self.user.role, "trusted")
        self.user.set_role("administrator")
        self.assertEqual(self.user.role, "administrator")

    def test_set_invalid_role(self):
        """Test setting an invalid role raises ValueError."""
        with self.assertRaisesRegex(ValueError, "Invalid role"):
            self.user.set_role("super_admin")

    def test_add_trust_points(self):
        """Test adding trust points."""
        self.user.add_trust_points(50)
        self.assertEqual(self.user.trust_points, 50)
        self.user.add_trust_points(75)
        self.assertEqual(self.user.trust_points, 125)

    def test_add_negative_trust_points(self):
        """Test adding negative trust points raises ValueError."""
        with self.assertRaisesRegex(ValueError, "non-negative number"):
            self.user.add_trust_points(-10)

    def test_remove_trust_points(self):
        """Test removing trust points."""
        self.user.add_trust_points(100)
        self.user.remove_trust_points(30)
        self.assertEqual(self.user.trust_points, 70)

    def test_remove_more_trust_points_than_available(self):
        """Test removing more points than available results in zero points."""
        self.user.add_trust_points(50)
        self.user.remove_trust_points(100)
        self.assertEqual(self.user.trust_points, 0) # Should not go below zero

    def test_remove_negative_trust_points(self):
        """Test removing negative trust points raises ValueError."""
        with self.assertRaisesRegex(ValueError, "non-negative number"):
            self.user.remove_trust_points(-10)

    def test_get_trust_level(self):
        """Test calculating trust level based on points."""
        self.assertEqual(self.user.get_trust_level(), 1) # 0 points
        self.user.add_trust_points(TRUST_LEVEL_THRESHOLDS[2] - 1) # 99 points
        self.assertEqual(self.user.get_trust_level(), 1)
        self.user.add_trust_points(1) # 100 points
        self.assertEqual(self.user.get_trust_level(), 2)
        self.user.add_trust_points(TRUST_LEVEL_THRESHOLDS[4] - TRUST_LEVEL_THRESHOLDS[2]) # 300 points total
        self.assertEqual(self.user.get_trust_level(), 4)
        self.user.add_trust_points(TRUST_LEVEL_THRESHOLDS[5] - TRUST_LEVEL_THRESHOLDS[4]) # 400 points total
        self.assertEqual(self.user.get_trust_level(), 5)
        self.user.add_trust_points(1000) # Way above max threshold
        self.assertEqual(self.user.get_trust_level(), 5)

    def test_add_remove_family_group(self):
        """Test adding and removing family group IDs."""
        group1 = "fg_123"
        group2 = "fg_456"
        self.user.add_family_group(group1)
        self.assertIn(group1, self.user.family_group_spaces)
        self.assertEqual(len(self.user.family_group_spaces), 1)

        # Add same group again (should have no effect)
        self.user.add_family_group(group1)
        self.assertEqual(len(self.user.family_group_spaces), 1)

        self.user.add_family_group(group2)
        self.assertCountEqual(self.user.family_group_spaces, [group1, group2])

        self.user.remove_family_group(group1)
        self.assertEqual(self.user.family_group_spaces, [group2])

        # Remove non-existent group
        with self.assertRaisesRegex(ValueError, "not in family group"):
            self.user.remove_family_group("non_existent_group")

    def test_is_inactive(self):
        """Test the inactivity check."""
        self.assertFalse(self.user.is_inactive(30)) # Just created, should be active

        # Manually set last_login to the past
        self.user.last_login = datetime.now() - timedelta(days=31)
        self.assertTrue(self.user.is_inactive(30))
        self.assertFalse(self.user.is_inactive(35)) # Still active within 35 days

        self.user.last_login = datetime.now() - timedelta(days=10)
        self.assertFalse(self.user.is_inactive(30))

    def test_string_representation(self):
        """Test __str__ and __repr__ methods."""
        self.assertIn("user1", str(self.user))
        self.assertIn("test@example.com", str(self.user))
        self.assertIn("role=basic", str(self.user))
        self.assertIn("trust_pts=0", str(self.user))

        self.assertTrue(repr(self.user).startswith("<User user1"))
        self.assertIn("test@example.com", repr(self.user))

    def test_equality_and_hash(self):
        """Test equality and hashing based on user_id."""
        user_copy = User("user1", "diff@example.com", "hash_copy", role="admin") # Same ID
        user_diff = User("user2", "test@example.com", "hashed_password") # Diff ID

        self.assertEqual(self.user, user_copy)
        self.assertEqual(hash(self.user), hash(user_copy))

        self.assertNotEqual(self.user, user_diff)
        self.assertNotEqual(hash(self.user), hash(user_diff))

        self.assertNotEqual(self.user, "not a user")


if __name__ == '__main__':
    unittest.main()
