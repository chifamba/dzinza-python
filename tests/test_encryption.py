# tests/test_encryption.py
import unittest
import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Now import the modules from src
from encryption import encrypt_password, verify_password

class TestEncryption(unittest.TestCase):
    """
    Test cases for the encryption module functions.
    """

    def test_encrypt_password(self):
        """
        Test that encrypt_password returns a non-empty string
        and that it's different from the original password.
        """
        password = "mysecretpassword"
        hashed_password = encrypt_password(password)

        # Check if the hashed password is a string and not empty
        self.assertIsInstance(hashed_password, str)
        self.assertNotEqual(hashed_password, "")
        # Check if the hashed password is different from the original
        self.assertNotEqual(hashed_password, password)
        # Check if hashing the same password again yields a different hash (due to salt)
        hashed_password_2 = encrypt_password(password)
        self.assertNotEqual(hashed_password, hashed_password_2)

    def test_verify_password_correct(self):
        """
        Test that verify_password returns True for the correct password.
        """
        password = "mysecretpassword"
        hashed_password = encrypt_password(password)
        self.assertTrue(verify_password(hashed_password, password))

    def test_verify_password_incorrect(self):
        """
        Test that verify_password returns False for an incorrect password.
        """
        password = "mysecretpassword"
        hashed_password = encrypt_password(password)
        self.assertFalse(verify_password(hashed_password, "wrongpassword"))

    def test_verify_password_empty(self):
        """
        Test verifying an empty password against a hash.
        """
        password = ""
        hashed_password = encrypt_password(password)
        self.assertTrue(verify_password(hashed_password, password))
        self.assertFalse(verify_password(hashed_password, "nonempty"))

    def test_verify_password_with_empty_hash(self):
        """
        Test verifying a password against an empty or invalid hash.
        It should ideally handle this gracefully (e.g., return False).
        bcrypt will raise ValueError for malformed hash.
        """
        with self.assertRaises(ValueError):
             verify_password("", "somepassword") # Malformed hash
        with self.assertRaises(ValueError):
             verify_password("notavalidhash", "somepassword") # Malformed hash


if __name__ == '__main__':
    unittest.main()
