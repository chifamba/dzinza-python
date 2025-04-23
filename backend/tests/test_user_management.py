# tests/test_user_management.py
import unittest
from unittest.mock import patch, MagicMock, call


# Import necessary classes and functions
from src.user import User, UserRole
from src.user_management import UserManagement
# Assuming db_utils is used for load/save
# from src.db_utils import load_data, save_data

# Mock data path
MOCK_USERS_FILE = 'mock_data/users.json'

class TestUserManagement(unittest.TestCase):
    """Test cases for the UserManagement class."""

    def setUp(self):
        """Set up a fresh UserManagement instance and mock data for each test."""
        # Mock load_data
        self.load_patcher = patch('user_management.load_data')
        self.mock_load_data = self.load_patcher.start()
        # Start with an empty user list for clean tests
        self.mock_load_data.return_value = []

        # Mock save_data
        self.save_patcher = patch('user_management.save_data')
        self.mock_save_data = self.save_patcher.start()

        # Create a new UserManagement instance
        self.user_mgmt = UserManagement(filepath=MOCK_USERS_FILE)

        # Sample users
        self.user1 = User(username="testuser", password_hash="hashed_pw_1", role=UserRole.USER)
        # Manually set password for testing validation (normally done by add_user)
        self.user1.set_password("password123")
        self.admin_user = User(username="admin", password_hash="hashed_pw_admin", role=UserRole.ADMIN)
        self.admin_user.set_password("adminpass")


    def tearDown(self):
        """Stop the patchers after each test."""
        self.load_patcher.stop()
        self.save_patcher.stop()

    def test_initialization_loads_data(self):
        """Test that user data is loaded during initialization."""
        self.mock_load_data.assert_called_once_with(MOCK_USERS_FILE, default=[])

    def test_add_user_success(self):
        """Test adding a new user successfully."""
        result = self.user_mgmt.add_user("newuser", "newpass", UserRole.USER)
        self.assertTrue(result)
        self.assertIn("newuser", self.user_mgmt.users)
        added_user = self.user_mgmt.get_user("newuser")
        self.assertIsNotNone(added_user)
        self.assertEqual(added_user.username, "newuser")
        self.assertTrue(added_user.check_password("newpass"))
        self.assertEqual(added_user.role, UserRole.USER)
        # Check that save was called
        self.mock_save_data.assert_called_once()
        # Check the data saved (optional, but good)
        args, kwargs = self.mock_save_data.call_args
        self.assertEqual(args[0], MOCK_USERS_FILE)
        self.assertEqual(len(args[1]), 1) # Saved list has one user dict
        self.assertEqual(args[1][0]['username'], 'newuser')

    def test_add_user_duplicate_username(self):
        """Test adding a user with an existing username."""
        self.user_mgmt.add_user("testuser", "password123", UserRole.USER)
        # Reset save mock to check if called again
        self.mock_save_data.reset_mock()

        result = self.user_mgmt.add_user("testuser", "anotherpass", UserRole.ADMIN)
        self.assertFalse(result) # Should fail or return False
        self.assertEqual(len(self.user_mgmt.users), 1) # Count should remain 1
        # Ensure save was not called for the failed attempt
        self.mock_save_data.assert_not_called()
        # Verify the original user wasn't overwritten
        original_user = self.user_mgmt.get_user("testuser")
        self.assertTrue(original_user.check_password("password123"))
        self.assertEqual(original_user.role, UserRole.USER)


    def test_get_user(self):
        """Test retrieving an existing user."""
        self.user_mgmt.add_user("testuser", "password123", UserRole.USER)
        retrieved_user = self.user_mgmt.get_user("testuser")
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.username, "testuser")

    def test_get_user_not_found(self):
        """Test retrieving a non-existent user."""
        retrieved_user = self.user_mgmt.get_user("nonexistent")
        self.assertIsNone(retrieved_user)

    def test_validate_user_correct(self):
        """Test validating a user with correct credentials."""
        self.user_mgmt.add_user("testuser", "password123", UserRole.USER)
        validated_user = self.user_mgmt.validate_user("testuser", "password123")
        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user.username, "testuser")

    def test_validate_user_incorrect_password(self):
        """Test validating a user with an incorrect password."""
        self.user_mgmt.add_user("testuser", "password123", UserRole.USER)
        validated_user = self.user_mgmt.validate_user("testuser", "wrongpassword")
        self.assertIsNone(validated_user)

    def test_validate_user_not_found(self):
        """Test validating a non-existent user."""
        validated_user = self.user_mgmt.validate_user("nonexistent", "password")
        self.assertIsNone(validated_user)

    def test_delete_user_success(self):
        """Test deleting an existing user."""
        self.user_mgmt.add_user("testuser", "password123", UserRole.USER)
        self.user_mgmt.add_user("anothertest", "pass", UserRole.USER)
        self.assertEqual(len(self.user_mgmt.users), 2)
        self.mock_save_data.reset_mock() # Reset mock before deletion

        result = self.user_mgmt.delete_user("testuser")
        self.assertTrue(result)
        self.assertNotIn("testuser", self.user_mgmt.users)
        self.assertEqual(len(self.user_mgmt.users), 1)
        # Check save was called
        self.mock_save_data.assert_called_once()
        # Check the correct data was saved
        args, kwargs = self.mock_save_data.call_args
        self.assertEqual(args[0], MOCK_USERS_FILE)
        self.assertEqual(len(args[1]), 1)
        self.assertEqual(args[1][0]['username'], 'anothertest') # Only remaining user


    def test_delete_user_not_found(self):
        """Test deleting a non-existent user."""
        self.user_mgmt.add_user("testuser", "password123", UserRole.USER)
        self.mock_save_data.reset_mock()

        result = self.user_mgmt.delete_user("nonexistent")
        self.assertFalse(result)
        self.assertEqual(len(self.user_mgmt.users), 1) # Count unchanged
        # Save should not be called if nothing changed
        self.mock_save_data.assert_not_called()

    # Example test for updating role - requires an update_user method in UserManagement
    # def test_update_user_role(self):
    #     """Test updating a user's role."""
    #     self.user_mgmt.add_user("testuser", "password123", UserRole.USER)
    #     self.mock_save_data.reset_mock()

    #     # Assuming an update_user method exists:
    #     # result = self.user_mgmt.update_user("testuser", role=UserRole.ADMIN)
    #     # self.assertTrue(result)

    #     updated_user = self.user_mgmt.get_user("testuser")
    #     # self.assertEqual(updated_user.role, UserRole.ADMIN)
    #     # self.mock_save_data.assert_called_once() # Check save on update

    def test_get_all_users(self):
        """Test retrieving all users."""
        self.user_mgmt.add_user("user1", "pass1", UserRole.USER)
        self.user_mgmt.add_user("user2", "pass2", UserRole.ADMIN)
        all_users = self.user_mgmt.get_all_users()
        self.assertEqual(len(all_users), 2)
        usernames = {u.username for u in all_users}
        self.assertEqual(usernames, {"user1", "user2"})

    def test_save_on_change(self):
        """Verify save is called after modifications."""
        # Add user
        self.mock_save_data.reset_mock()
        self.user_mgmt.add_user("newuser", "pass", UserRole.USER)
        self.mock_save_data.assert_called_once()
        args, kwargs = self.mock_save_data.call_args
        self.assertEqual(args[0], MOCK_USERS_FILE)
        self.assertEqual(len(args[1]), 1)

        # Delete user
        self.mock_save_data.reset_mock()
        self.user_mgmt.delete_user("newuser")
        self.mock_save_data.assert_called_once()
        args, kwargs = self.mock_save_data.call_args
        self.assertEqual(args[0], MOCK_USERS_FILE)
        self.assertEqual(len(args[1]), 0) # List should be empty now


if __name__ == '__main__':
    unittest.main()
