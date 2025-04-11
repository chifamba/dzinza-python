import unittest
from src.user_management import UserManager, User
from src.audit_log import AuditLog


class TestUser(unittest.TestCase):
    def setUp(self):
        self.audit_log = AuditLog()
        self.user_manager = UserManager(self.audit_log)

    def test_create_user(self):
        """Test creating a new user."""
        user = self.user_manager.create_user(
            "testuser", "test@test.com", "password"
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@test.com")
        self.assertEqual(user.access_level, "user")
        self.assertEqual(user.trust_level, 0)
        self.assertIn("User with email test@test.com created", [log["description"] for log in self.audit_log.get_log_entries(event_type="user_created")])

    def test_get_user(self):
        """Test getting an existing user."""
        user = self.user_manager.create_user(
            "testuser2", "test2@test.com", "password"
        )
        retrieved_user = self.user_manager.get_user(user.user_id)
        self.assertEqual(user, retrieved_user)

    def test_get_user_not_found(self):
        """Test getting a non-existing user."""
        retrieved_user = self.user_manager.get_user("nonexistent_user")
        self.assertIsNone(retrieved_user)

    def test_update_user(self):
        """Test updating an existing user."""
        user = self.user_manager.create_user(
            "testuser3", "test3@test.com", "password"
        )
        self.user_manager.update_user(user.user_id, "newuser", "new@test.com", 10)
        updated_user = self.user_manager.get_user(user.user_id)
        self.assertEqual(updated_user.username, "newuser")
        self.assertEqual(updated_user.email, "new@test.com")
        self.assertEqual(updated_user.trust_level, 10)
        self.assertIn("User with email new@test.com updated", [log["description"] for log in self.audit_log.get_log_entries(event_type="user_updated")])

    def test_update_user_not_found(self):
        """Test updating a non-existing user."""
        with self.assertRaises(ValueError):
            self.user_manager.update_user(
                "nonexistent_user", "newuser", "new@test.com", 10
            )

    def test_delete_user(self):
        """Test deleting an existing user."""
        user = self.user_manager.create_user(
            "testuser4", "test4@test.com", "password"
        )
        self.user_manager.delete_user(user.user_id)
        deleted_user = self.user_manager.get_user(user.user_id)
        self.assertIsNone(deleted_user)
        self.assertIn("User testuser4 deleted", [log["description"] for log in self.audit_log.get_log_entries(event_type="user_deleted")])

    def test_delete_user_not_found(self):
        """Test deleting a non-existing user."""
        with self.assertRaises(ValueError):
            self.user_manager.delete_user("nonexistent_user")

    def test_user_password(self):
        """Test user password management"""
        user = self.user_manager.create_user(
            "testuser5", "test5@test.com", "password"
        )
        self.assertTrue(user.check_password("password"))
        self.assertFalse(user.check_password("wrong"))
        user.set_password("newpassword")
        self.assertTrue(user.check_password("newpassword"))
        self.assertFalse(user.check_password("password"))

    def test_user_str(self):
        """Test the __str__ method of the User class"""
        user = self.user_manager.create_user(
            "testuser6", "test6@test.com", "password"
        )
        self.assertEqual(str(user), "User: testuser6, Email: test6@test.com")


if __name__ == "__main__":
    unittest.main()