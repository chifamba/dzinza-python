import unittest
from src.encryption import DataEncryptor


class TestDataEncryptor(unittest.TestCase):
    """
    Test suite for the DataEncryptor class.
    """

    def setUp(self):
        """
        Set up method to create a DataEncryptor instance before each test.
        """
        self.encryptor = DataEncryptor()
        self.encryption_key = "mysecretkey"  # Example encryption key

    def test_encrypt_decrypt_data(self):
        """
        Test that encrypting and then decrypting data returns the original data.
        """
        data = "This is a secret message."
        encrypted_data = self.encryptor.encrypt_data(data, self.encryption_key)
        self.assertNotEqual(data, encrypted_data)

        decrypted_data = self.encryptor.decrypt_data(encrypted_data, self.encryption_key)
        self.assertEqual(data, decrypted_data)

    def test_encrypt_with_invalid_key(self):
        """
        Test that encrypting with an invalid key raises a ValueError.
        """
        data = "This is a secret message."
        with self.assertRaises(ValueError):
            self.encryptor.encrypt_data(data, "")

    def test_decrypt_with_invalid_key(self):
        """
        Test that decrypting with an invalid key raises a ValueError.
        """
        data = "This is a secret message."
        encrypted_data = self.encryptor.encrypt_data(data, self.encryption_key)
        with self.assertRaises(ValueError):
            self.encryptor.decrypt_data(encrypted_data, "wrongkey")

    def test_encrypt_empty_data(self):
        """
        Test encrypting empty data.
        """
        data = ""
        encrypted_data = self.encryptor.encrypt_data(data, self.encryption_key)
        self.assertNotEqual(data, encrypted_data)
        decrypted_data = self.encryptor.decrypt_data(encrypted_data, self.encryption_key)
        self.assertEqual(data, decrypted_data)


if __name__ == "__main__":
    unittest.main()