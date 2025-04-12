# tests/test_user_management.py
import unittest
from unittest.mock import MagicMock

from src.user_management import UserManager
from src.user import User # Import User for type checks
from src.audit_log import AuditLog # Import placeholder

# Mock the placeholder password functions if needed, or assume they work as placeholders
# from src.user_management import placeholder_hash_password, placeholder_check_password

class TestUserManager(unittest.TestCase):
    """Test suite for the refactored UserManager class."""

    def setUp(self):
        """Set up a UserManager instance for tests."""
        self.mock_audit_log = MagicMock(spec=AuditLog)
        self.user_manager = UserManager(audit_log=self.mock_audit_log)

        # Pre-populate with a user for some tests
        self.user_manager.create_user("existing_user", "exists@example.com", "password123", role="trusted")

    def test_create_user_success(self):
        """Test creating a new user successfully."""
        user = self.user_manager.create_user("new_user", "new@example.com", "newpass", role="basic")
        self.assertIsInstance(user, User)
        self.assertEqual(user.user_id, "new_user")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.role, "basic")
        # Check placeholder hash (insecure, replace test when using real hashing)
        self.assertEqual(user.password_hash, "newpass")

        # Verify user is stored
        self.assertIn("new_user", self.user_manager.users)
        self.assertIn("new@example.com", self.user_manager.users_by_email)
        self.assertEqual(self.user_manager.get_user("new_user"), user)
        self.assertEqual(self.user_manager.get_user_by_email("new@example.com"), user)

        # Verify audit log call
        self.mock_audit_log.log_event.assert_called_with(
            "system", "user_created", "Created user: new_user (new@example.com), role: basic"
        )

    def test_create_user_duplicate_id(self):
        """Test creating a user with an existing ID raises ValueError."""
        with self.assertRaisesRegex(ValueError, "User ID 'existing_user' already exists"):
            self.user_manager.create_user("existing_user", "another@example.com", "password")

    def test_create_user_duplicate_email(self):
        """Test creating a user with an existing email raises ValueError."""
        with self.assertRaisesRegex(ValueError, "Email 'exists@example.com' is already in use"):
            self.user_manager.create_user("another_user", "exists@example.com", "password")

    def test_create_user_invalid_role(self):
        """Test creating a user with an invalid role raises ValueError."""
        with self.assertRaisesRegex(ValueError, "Invalid role"):
            self.user_manager.create_user("user_bad_role", "bad@example.com", "password", role="invalid")

    def test_get_user(self):
        """Test getting an existing user by ID."""
        user = self.user_manager.get_user("existing_user")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "existing_user")

    def test_get_user_not_found(self):
        """Test getting a non-existent user returns None."""
        self.assertIsNone(self.user_manager.get_user("nonexistent_user"))

    def test_get_user_by_email(self):
        """Test getting an existing user by email (case-insensitive)."""
        user = self.user_manager.get_user_by_email("exists@example.com")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "existing_user")

        user_upper = self.user_manager.get_user_by_email("EXISTS@EXAMPLE.COM")
        self.assertIsNotNone(user_upper)
        self.assertEqual(user_upper.user_id, "existing_user")


    def test_get_user_by_email_not_found(self):
        """Test getting a non-existent user by email returns None."""
        self.assertIsNone(self.user_manager.get_user_by_email("nonexistent@example.com"))

    def test_update_user_all_fields(self):
        """Test updating email, password, and role."""
        user_id_to_update = "existing_user"
        original_user = self.user_manager.get_user(user_id_to_update)
        original_email = original_user.email

        self.user_manager.update_user(
            user_id_to_update,
            new_email="updated@example.com",
            new_password="updated_password",
            new_role="administrator",
            acting_user_id="admin01"
        )

        updated_user = self.user_manager.get_user(user_id_to_update)
        self.assertEqual(updated_user.email, "updated@example.com")
        self.assertEqual(updated_user.role, "administrator")
        # Check placeholder hash/password
        self.assertEqual(updated_user.password_hash, "updated_password")
        self.assertTrue(updated_user.check_password("updated_password")) # Using placeholder check

        # Verify email mapping updated
        self.assertIsNone(self.user_manager.get_user_by_email(original_email))
        self.assertEqual(self.user_manager.get_user_by_email("updated@example.com"), updated_user)

        # Verify audit log
        self.mock_audit_log.log_event.assert_called_with(
            "admin01", "user_updated", "Updated user existing_user: email updated to updated@example.com, password updated, role updated to administrator"
        )

    def test_update_user_only_email(self):
        """Test updating only the email."""
        self.user_manager.update_user("existing_user", new_email="only_email@example.com")
        user = self.user_manager.get_user("existing_user")
        self.assertEqual(user.email, "only_email@example.com")
        self.assertEqual(user.role, "trusted") # Role unchanged
        self.assertEqual(user.password_hash, "password123") # Password unchanged

    def test_update_user_not_found(self):
        """Test updating a non-existent user raises ValueError."""
        with self.assertRaisesRegex(ValueError, "not found"):
            self.user_manager.update_user("nonexistent", new_email="fail@example.com")

    def test_update_user_email_conflict(self):
        """Test updating email to one that already exists raises ValueError."""
        self.user_manager.create_user("other_user", "other@example.com", "pass")
        with self.assertRaisesRegex(ValueError, "Email 'other@example.com' is already in use"):
            self.user_manager.update_user("existing_user", new_email="other@example.com")

    def test_update_user_invalid_role(self):
        """Test updating to an invalid role raises ValueError."""
        with self.assertRaisesRegex(ValueError, "Invalid role"):
            self.user_manager.update_user("existing_user", new_role="invalid")

    def test_delete_user(self):
        """Test deleting an existing user."""
        user_id_to_delete = "existing_user"
        user_email = self.user_manager.get_user(user_id_to_delete).email

        self.user_manager.delete_user(user_id_to_delete, acting_user_id="admin01")

        # Verify removed
        self.assertIsNone(self.user_manager.get_user(user_id_to_delete))
        self.assertIsNone(self.user_manager.get_user_by_email(user_email))
        self.assertNotIn(user_id_to_delete, self.user_manager.users)
        self.assertNotIn(user_email, self.user_manager.users_by_email)

        # Verify audit log
        self.mock_audit_log.log_event.assert_called_with(
            "admin01", "user_deleted", f"Deleted user: {user_id_to_delete} ({user_email})"
        )

    def test_delete_user_not_found(self):
        """Test deleting a non-existent user raises ValueError."""
        with self.assertRaisesRegex(ValueError, "not found"):
            self.user_manager.delete_user("nonexistent")

    def test_validate_user_credentials_success(self):
        """Test successful credential validation."""
        user = self.user_manager.validate_user_credentials("exists@example.com", "password123")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "existing_user")
        self.mock_audit_log.log_event.assert_called_with(
            "existing_user", "login_success", "User existing_user logged in successfully."
        )

    def test_validate_user_credentials_wrong_password(self):
        """Test credential validation with incorrect password."""
        user = self.user_manager.validate_user_credentials("exists@example.com", "wrong_password")
        self.assertIsNone(user)
        self.mock_audit_log.log_event.assert_called_with(
            "exists@example.com", "login_failed", "Login failed for email exists@example.com (incorrect password)."
        )

    def test_validate_user_credentials_user_not_found(self):
        """Test credential validation for non-existent user."""
        user = self.user_manager.validate_user_credentials("nonexistent@example.com", "password")
        self.assertIsNone(user)
        self.mock_audit_log.log_event.assert_called_with(
            "nonexistent@example.com", "login_failed", "Login failed for email nonexistent@example.com (user not found)."
        )

    def test_change_user_role(self):
        """Test changing a user's role."""
        self.user_manager.change_user_role("existing_user", "administrator", "admin01")
        user = self.user_manager.get_user("existing_user")
        self.assertEqual(user.role, "administrator")
        self.mock_audit_log.log_event.assert_called_with(
            "admin01", "role_change", "Changed role for user existing_user to administrator."
        )

    def test_change_user_role_invalid(self):
        """Test changing to an invalid role fails."""
        with self.assertRaises(ValueError):
            self.user_manager.change_user_role("existing_user", "invalid", "admin01")
        self.mock_audit_log.log_event.assert_called_with(
            "admin01", "role_change_failed", "Failed to change role for user existing_user to invalid: Invalid role: invalid. Valid roles are: ['basic', 'trusted', 'administrator', 'family_historian', 'guest']"
        )


    def test_add_remove_trust_points(self):
        """Test adding and removing trust points via manager."""
        user_id = "existing_user"
        self.user_manager.add_trust_points(user_id, 50, "Test add", "admin01")
        user = self.user_manager.get_user(user_id)
        self.assertEqual(user.trust_points, 50)
        self.mock_audit_log.log_event.assert_called_with(
             "admin01", "trust_points_added", f"Added 50 trust points to user {user_id}. Reason: Test add. New total: 50."
        )

        self.user_manager.remove_trust_points(user_id, 20, "Test remove", "admin01")
        self.assertEqual(user.trust_points, 30)
        self.mock_audit_log.log_event.assert_called_with(
             "admin01", "trust_points_removed", f"Removed 20 trust points from user {user_id}. Reason: Test remove. New total: 30."
        )

    def test_apply_trust_decay(self):
        """Test applying trust decay to inactive users."""
        # Make existing_user inactive
        user = self.user_manager.get_user("existing_user")
        user.add_trust_points(100) # Give some points
        user.last_login = datetime.now() - timedelta(days=31)

        # Add an active user
        active_user = self.user_manager.create_user("active_user", "active@example.com", "pass")
        active_user.add_trust_points(100)

        # Apply decay
        self.user_manager.apply_trust_decay(days_threshold=30, decay_points=50)

        # Verify inactive user lost points
        self.assertEqual(user.trust_points, 50) # 100 - 50
        # Verify active user did not lose points
        self.assertEqual(active_user.trust_points, 100)

        # Verify audit log calls
        self.mock_audit_log.log_event.assert_any_call("system", "trust_decay_start", "Starting trust decay check (threshold: 30 days).")
        self.mock_audit_log.log_event.assert_any_call("system", "trust_decay_applied", f"Applied trust decay (-50 points) to inactive user {user.user_id}. New total: 50.")
        self.mock_audit_log.log_event.assert_any_call("system", "trust_decay_end", "Trust decay check complete. Applied decay to 1 users.")


if __name__ == '__main__':
    unittest.main()
