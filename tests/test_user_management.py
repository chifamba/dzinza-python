# tests/test_user_management.py

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone # Import datetime, timedelta, timezone

from src.user_management import UserManager
from src.user import User, hash_password
from src.audit_log import AuditLog # Assuming AuditLog is needed for mock type hint
from src.encryption import DataEncryptor # Assuming for mock type hint

# Mock placeholder classes if needed
class MockAuditLog:
    def log_event(self, user, event, description):
        print(f"AUDIT LOG MOCK [{user}] {event}: {description}")

class MockDataEncryptor:
    def encrypt(self, data): return data
    def decrypt(self, data): return data

class TestUserManager(unittest.TestCase):
    """Unit tests for the UserManager class."""

    def setUp(self):
        """Set up a UserManager instance with mock dependencies."""
        self.mock_audit_log = MagicMock(spec=AuditLog)
        self.mock_encryptor = MagicMock(spec=DataEncryptor)
        self.mock_encryptor.encrypt.side_effect = lambda d: d # Mock encryption passthrough
        self.mock_encryptor.decrypt.side_effect = lambda d: d # Mock decryption passthrough

        self.user_manager = UserManager(audit_log=self.mock_audit_log, encryptor=self.mock_encryptor)

        # Add some initial users for tests
        self.user1_data = {"user_id": "user1", "email": "user1@example.com", "password_hash": hash_password("pass1"), "role": "basic", "trust_level": 50, "last_login": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()}
        self.user2_data = {"user_id": "user2", "email": "user2@example.com", "password_hash": hash_password("pass2"), "role": "administrator", "trust_level": 100, "last_login": (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()}
        self.user3_data = {"user_id": "user3", "email": "user3@example.com", "password_hash": hash_password("pass3"), "role": "trusted", "trust_level": 80, "last_login": None} # Never logged in

        self.user_manager.add_user(User.from_dict(self.user1_data))
        self.user_manager.add_user(User.from_dict(self.user2_data))
        self.user_manager.add_user(User.from_dict(self.user3_data))

        # Reset mocks called during setup
        self.mock_audit_log.reset_mock()

    def test_add_user(self):
        """Test adding a new user."""
        new_user_data = {"user_id": "newbie", "email": "new@example.com", "password_hash": hash_password("newpass"), "role": "guest"}
        new_user = User.from_dict(new_user_data)
        result = self.user_manager.add_user(new_user, actor_user_id="admin1")

        self.assertTrue(result)
        self.assertIn("newbie", self.user_manager.users)
        self.assertEqual(self.user_manager.users["newbie"].email, "new@example.com")
        self.mock_audit_log.log_event.assert_called_once_with(
            "admin1", "user_added", "Added user: newbie (new@example.com)"
        )

    def test_add_user_duplicate_id(self):
        """Test adding a user with a duplicate user_id."""
        duplicate_user = User("user1", "dup@example.com", hash_password("passdup"))
        result = self.user_manager.add_user(duplicate_user, actor_user_id="admin1")

        self.assertFalse(result)
        # Ensure the original user1 data wasn't overwritten
        self.assertEqual(self.user_manager.users["user1"].email, "user1@example.com")
        # Ensure no audit log for failed addition
        self.mock_audit_log.log_event.assert_not_called()

    def test_get_user(self):
        """Test retrieving an existing user."""
        user = self.user_manager.get_user("user1")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "user1")
        self.assertEqual(user.email, "user1@example.com")

    def test_get_user_not_found(self):
        """Test retrieving a non-existent user."""
        user = self.user_manager.get_user("nonexistent")
        self.assertIsNone(user)

    def test_update_user(self):
        """Test updating an existing user's details."""
        update_data = {"email": "user1.updated@example.com", "role": "trusted"}
        result = self.user_manager.update_user("user1", update_data, actor_user_id="admin1")

        self.assertTrue(result)
        updated_user = self.user_manager.get_user("user1")
        self.assertEqual(updated_user.email, "user1.updated@example.com")
        self.assertEqual(updated_user.role, "trusted")
        # Check audit log for specific changes if implemented, or a general update message
        self.mock_audit_log.log_event.assert_called_once_with(
            "admin1", "user_updated", f"Updated user 'user1'. Changes: {update_data}" # Example log format
        )

    def test_update_user_not_found(self):
        """Test updating a non-existent user."""
        update_data = {"email": "nope@example.com"}
        result = self.user_manager.update_user("nonexistent", update_data, actor_user_id="admin1")
        self.assertFalse(result)
        self.mock_audit_log.log_event.assert_not_called()

    def test_update_user_invalid_role(self):
        """Test updating a user with an invalid role."""
        update_data = {"role": "super_admin"}
        result = self.user_manager.update_user("user1", update_data, actor_user_id="admin1")
        self.assertFalse(result) # Should fail validation
        self.assertEqual(self.user_manager.get_user("user1").role, "basic") # Role should not change
        self.mock_audit_log.log_event.assert_not_called() # Or log a failed attempt if desired

    def test_delete_user(self):
        """Test deleting an existing user."""
        result = self.user_manager.delete_user("user1", actor_user_id="admin1")
        self.assertTrue(result)
        self.assertNotIn("user1", self.user_manager.users)
        self.mock_audit_log.log_event.assert_called_once_with(
            "admin1", "user_deleted", "Deleted user: user1 (user1@example.com)"
        )

    def test_delete_user_not_found(self):
        """Test deleting a non-existent user."""
        result = self.user_manager.delete_user("nonexistent", actor_user_id="admin1")
        self.assertFalse(result)
        self.mock_audit_log.log_event.assert_not_called()

    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        authenticated_user = self.user_manager.authenticate_user("user1", "pass1")
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.user_id, "user1")
        # Check if last_login was updated (implementation detail)
        # Check audit log for successful login
        self.mock_audit_log.log_event.assert_called_once_with(
            "user1", "login_success", "User 'user1' authenticated successfully."
        )

    def test_authenticate_user_incorrect_password(self):
        """Test authentication with an incorrect password."""
        authenticated_user = self.user_manager.authenticate_user("user1", "wrongpass")
        self.assertIsNone(authenticated_user)
        # Check audit log for failed login attempt
        self.mock_audit_log.log_event.assert_called_once_with(
            "user1", "login_failed", "Failed login attempt for user 'user1': Incorrect password."
        )

    def test_authenticate_user_not_found(self):
        """Test authentication for a non-existent user."""
        authenticated_user = self.user_manager.authenticate_user("nonexistent", "anypass")
        self.assertIsNone(authenticated_user)
        # Check audit log for failed login attempt
        self.mock_audit_log.log_event.assert_called_once_with(
            "nonexistent", "login_failed", "Failed login attempt for user 'nonexistent': User not found."
        )

    # --- Persistence Tests ---

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_users(self, mock_json_dump, mock_file):
        """Test saving users to a file."""
        file_path = "users.json"
        self.user_manager.save_users(file_path, actor_user_id="system_save")

        # Check that open was called correctly
        mock_file.assert_called_once_with(file_path, 'w', encoding='utf-8')

        # Check that json.dump was called
        mock_json_dump.assert_called_once()

        # Check the data passed to json.dump (first argument)
        args, kwargs = mock_json_dump.call_args
        saved_data = args[0]
        self.assertIsInstance(saved_data, dict)
        self.assertIn("users", saved_data)
        self.assertEqual(len(saved_data["users"]), 3) # user1, user2, user3
        # Verify structure of one user
        user1_saved = next((u for u in saved_data["users"] if u.get("user_id") == "user1"), None)
        self.assertIsNotNone(user1_saved)
        self.assertEqual(user1_saved["email"], self.user1_data["email"])
        self.assertEqual(user1_saved["password_hash"], self.user1_data["password_hash"]) # Ensure hash is saved

        # Check encryption was called (assuming save encrypts)
        self.mock_encryptor.encrypt.assert_called_once()

        # Check audit log
        self.mock_audit_log.log_event.assert_called_with(
            "system_save", "users_saved", f"User data saved to {file_path}"
        )


    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.loads")
    def test_load_users(self, mock_json_loads, mock_file, mock_exists):
        """Test loading users from a file."""
        file_path = "users.json"
        # Prepare mock data returned by json.loads and decryptor
        loaded_data = {
            "users": [
                {"user_id": "loaded1", "email": "load1@example.com", "password_hash": "hash_l1", "role": "basic"},
                {"user_id": "loaded2", "email": "load2@example.com", "password_hash": "hash_l2", "role": "administrator"}
            ]
        }
        # Mock decryptor to return the string version of loaded_data
        self.mock_encryptor.decrypt.return_value = json.dumps(loaded_data)
        # Mock json.loads to return the actual dictionary
        mock_json_loads.return_value = loaded_data

        # Clear existing users before load
        self.user_manager.users.clear()
        self.user_manager.load_users(file_path, actor_user_id="system_load")

        # Check mocks
        mock_exists.assert_called_once_with(file_path)
        mock_file.assert_called_once_with(file_path, 'r', encoding='utf-8')
        self.mock_encryptor.decrypt.assert_called_once()
        mock_json_loads.assert_called_once()

        # Check loaded users
        self.assertEqual(len(self.user_manager.users), 2)
        self.assertIn("loaded1", self.user_manager.users)
        self.assertIn("loaded2", self.user_manager.users)
        self.assertEqual(self.user_manager.users["loaded1"].email, "load1@example.com")
        self.assertEqual(self.user_manager.users["loaded2"].role, "administrator")

        # Check audit log
        self.mock_audit_log.log_event.assert_called_with(
            "system_load", "users_loaded", f"User data loaded from {file_path}. Found 2 users."
        )

    @patch("os.path.exists", return_value=False) # Mock file not existing
    def test_load_users_file_not_found(self, mock_exists):
        """Test loading users when the file doesn't exist."""
        file_path = "nonexistent_users.json"
        self.user_manager.load_users(file_path, actor_user_id="system_load")

        mock_exists.assert_called_once_with(file_path)
        # Ensure no users were loaded
        self.assertEqual(len(self.user_manager.users), 3) # Should still have setup users
        # Check audit log for appropriate message
        self.mock_audit_log.log_event.assert_called_with(
            "system_load", "users_load_skipped", f"User data file not found: {file_path}. Skipping load."
        )

    # --- Trust Decay Test ---
    def test_apply_trust_decay(self):
        """Test applying trust decay to inactive users."""
        # Setup:
        # user1: last login 10 days ago (active) - trust 50
        # user2: last login 40 days ago (inactive) - trust 100
        # user3: last login None (inactive) - trust 80
        initial_trust_user1 = self.user_manager.users["user1"].trust_level
        initial_trust_user2 = self.user_manager.users["user2"].trust_level
        initial_trust_user3 = self.user_manager.users["user3"].trust_level

        # Define decay parameters for test
        inactivity_threshold_days = 30
        decay_amount = 5
        min_trust_level = 10 # Example minimum

        self.user_manager.apply_trust_decay(inactivity_threshold_days, decay_amount, min_trust_level, actor_user_id="cron_job")

        # Assertions:
        # user1 (active) should not decay
        self.assertEqual(self.user_manager.users["user1"].trust_level, initial_trust_user1)

        # user2 (inactive) should decay
        expected_trust_user2 = max(min_trust_level, initial_trust_user2 - decay_amount)
        self.assertEqual(self.user_manager.users["user2"].trust_level, expected_trust_user2) # 100 - 5 = 95

        # user3 (inactive - never logged in) should decay
        expected_trust_user3 = max(min_trust_level, initial_trust_user3 - decay_amount)
        self.assertEqual(self.user_manager.users["user3"].trust_level, expected_trust_user3) # 80 - 5 = 75

        # Check audit logs (should log for decayed users)
        self.mock_audit_log.log_event.assert_any_call(
             "cron_job", "trust_decay_applied", f"Applied trust decay to user 'user2'. New level: {expected_trust_user2}"
        )
        self.mock_audit_log.log_event.assert_any_call(
             "cron_job", "trust_decay_applied", f"Applied trust decay to user 'user3'. New level: {expected_trust_user3}"
        )
        # Ensure user1 was not logged for decay
        log_calls = self.mock_audit_log.log_event.call_args_list
        self.assertFalse(any("user 'user1'" in call.args[2] for call in log_calls if call.args[1] == "trust_decay_applied"))


if __name__ == '__main__':
    unittest.main()
