import unittest
from backend.main import _hash_password, _verify_password

class TestPasswordHashing(unittest.TestCase):

    def test_hash_and_verify_password(self):
        # Define a test password
        test_password = "01Admin_2025"

        # Hash the password
        hashed_password = _hash_password(test_password)

        # Verify the password against the hash
        self.assertTrue(
            _verify_password(test_password, hashed_password),
            "Password verification failed"
        )

    def test_verify_incorrect_password(self):
        # Define a test password and an incorrect password
        test_password = "01Admin_2025"
        incorrect_password = "WrongPassword123!"

        # Hash the correct password
        hashed_password = _hash_password(test_password)

        # Verify the incorrect password against the hash
        self.assertFalse(
            _verify_password(incorrect_password, hashed_password),
            "Incorrect password verification passed"
        )

if __name__ == "__main__":
    unittest.main()
