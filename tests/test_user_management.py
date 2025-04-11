import unittest
from src.user_management import UserManager, User


class TestUser(unittest.TestCase):
    def setUp(self):
        self.user_manager = UserManager()

    def test_create_user(self):
        """Test creating a new user."""
        user = self.user_manager.create_user("testuser", "test@test.com", "password")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "testuser")
        self.assertEqual(user.email, "test@test.com")
        self.assertEqual(user.password, "password")


    def test_get_user(self):
        """Test getting an existing user."""
        user = self.user_manager.create_user(
            "testuser2", "test2@test.com", "password"
        )
        retrieved_user = self.user_manager.get_user("testuser2")
        self.assertEqual(user, retrieved_user)

    def test_get_user_not_found(self):
        """Test getting a non-existing user."""
        with self.assertRaises(ValueError):
            self.user_manager.get_user("testuser_not_found")

    def test_update_user(self):
        """Test updating an existing user."""
        self.user_manager.create_user("testuser3", "test3@test.com", "password")
        self.user_manager.update_user("testuser3", "user1", "new@test.com", "newpassword")
        updated_user = self.user_manager.get_user("user1")
        self.assertEqual(updated_user.user_id, "user1")
        self.assertEqual(updated_user.email, "new@test.com")
        self.assertEqual(updated_user.password, "newpassword")

    def test_update_user_not_found(self):
        """Test updating a non-existing user."""
        with self.assertRaises(ValueError):
            self.user_manager.update_user("testuser_not_found", "user1", "new@test.com", "newpassword")

        self.user_manager.create_user("testuser4", "test4@test.com", "password")
        self.user_manager.delete_user("testuser4")

    def test_delete_user_not_found(self):
        """Test deleting a non-existing user."""
        with self.assertRaises(ValueError):
            self.user_manager.delete_user("nonexistent_user")

    def test_user_str(self):
        """Test user string representation."""
        user = self.user_manager.create_user("testuser7", "test7@test.com", "password")
        self.assertEqual(str(user), f"User: testuser7, Email: test7@test.com")

if __name__ == '__main__':
    unittest.main()