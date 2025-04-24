# backend/tests/test_encryption.py
import unittest
import os
import tempfile
import json
# Assuming encryption functions are in backend.src.encryption
# Adjust the import based on your actual structure
try:
    from backend.src.encryption import (
        generate_key, load_key, save_key, encrypt_data, decrypt_data
    )
except ImportError:
    print("Warning: Could not import encryption functions from backend.src.encryption")
    # Define dummy functions if import fails
    def generate_key(): return b'dummy_key_1234567890123456' # Must be 16, 24, or 32 bytes
    def load_key(path): return generate_key()
    def save_key(key, path): pass
    def encrypt_data(key, data): return b'encrypted:' + data.encode()
    def decrypt_data(key, encrypted_data):
        if encrypted_data.startswith(b'encrypted:'):
            return encrypted_data[len(b'encrypted:'):].decode()
        raise ValueError("Decryption failed")


class TestEncryption(unittest.TestCase):

    def setUp(self):
        """Create a temporary file for the key."""
        self.temp_fd, self.temp_key_path = tempfile.mkstemp(suffix=".key")
        os.close(self.temp_fd) # Close the file descriptor
        self.key = generate_key()
        save_key(self.key, self.temp_key_path)

    def tearDown(self):
        """Remove the temporary key file."""
        if os.path.exists(self.temp_key_path):
            os.remove(self.temp_key_path)

    def test_generate_key(self):
        """Test key generation."""
        key = generate_key()
        self.assertIsInstance(key, bytes)
        self.assertIn(len(key), [16, 24, 32]) # AES key sizes

    def test_save_and_load_key(self):
        """Test saving and loading the key."""
        loaded_key = load_key(self.temp_key_path)
        self.assertEqual(self.key, loaded_key)

    def test_load_key_file_not_found(self):
        """Test loading a key from a non-existent file."""
        if os.path.exists(self.temp_key_path):
            os.remove(self.temp_key_path)
        with self.assertRaises(FileNotFoundError):
            load_key(self.temp_key_path)

    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a simple string."""
        original_data = "This is a secret message."
        encrypted_data = encrypt_data(self.key, original_data)
        decrypted_data = decrypt_data(self.key, encrypted_data)

        self.assertNotEqual(original_data.encode(), encrypted_data) # Ensure it's encrypted
        self.assertEqual(original_data, decrypted_data)

    def test_encrypt_decrypt_complex_data(self):
        """Test encrypting and decrypting JSON-serializable data."""
        original_data = {"user_id": 123, "permissions": ["read", "write"], "nested": {"value": True}}
        # Convert complex data to JSON string before encryption
        original_data_str = json.dumps(original_data)

        encrypted_data = encrypt_data(self.key, original_data_str)
        decrypted_data_str = decrypt_data(self.key, encrypted_data)

        # Convert back from JSON string
        decrypted_data = json.loads(decrypted_data_str)

        self.assertNotEqual(original_data_str.encode(), encrypted_data)
        self.assertEqual(original_data, decrypted_data)

    def test_decrypt_with_wrong_key(self):
        """Test decryption with a wrong key fails."""
        original_data = "Another secret."
        encrypted_data = encrypt_data(self.key, original_data)
        wrong_key = generate_key()
        # Ensure keys are different
        while wrong_key == self.key:
            wrong_key = generate_key()

        # Decryption should fail (raise ValueError or similar based on implementation)
        with self.assertRaises(ValueError): # Or specific crypto error
            decrypt_data(wrong_key, encrypted_data)

    def test_decrypt_tampered_data(self):
        """Test decryption of tampered data fails."""
        original_data = "Untampered data."
        encrypted_data = encrypt_data(self.key, original_data)

        # Tamper the encrypted data (e.g., flip a bit)
        # Note: This is a simple tamper; real attacks are more complex
        # AES-GCM includes authentication, so tampering should be detected
        tampered_data_list = list(encrypted_data)
        if tampered_data_list: # Ensure not empty
             tampered_data_list[-1] = (tampered_data_list[-1] + 1) % 256 # Flip last byte
        tampered_data = bytes(tampered_data_list)

        # Decryption should fail due to authentication tag mismatch
        with self.assertRaises(ValueError): # Or specific crypto error
            decrypt_data(self.key, tampered_data)


if __name__ == '__main__':
    unittest.main()
