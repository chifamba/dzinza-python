# backend/src/encryption.py
import bcrypt
import os
import logging
import base64
import json
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
# Import db_utils for loading/saving the key
from .db_utils import load_data, save_data

# --- Password Hashing ---

def hash_password(password):
    """
    Hashes a password using bcrypt.

    Args:
        password (str): The plaintext password to hash.

    Returns:
        bytes: The hashed password, or None if hashing fails.
    """
    if not password:
        logging.error("Error hashing password: Password cannot be empty.")
        return None
    try:
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        return hashed_password
    except Exception as e:
        logging.error(f"Error hashing password: {e}", exc_info=True)
        return None

# --- Password Verification ---

def verify_password(plain_password, hashed_password):
    """
    Verifies a plaintext password against a stored bcrypt hash.

    Args:
        plain_password (str): The plaintext password entered by the user.
        hashed_password (bytes): The stored hashed password (must be bytes).

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    if not plain_password or not hashed_password:
        logging.error("Error verifying password: Both plain password and hashed password must be provided.")
        return False
    try:
        plain_password_bytes = plain_password.encode('utf-8')
        if not isinstance(hashed_password, bytes):
            logging.error(f"Type error during password verification: hashed_password must be bytes, got {type(hashed_password)}.")
            if isinstance(hashed_password, str):
                try:
                    hashed_password = base64.b64decode(hashed_password.encode('utf-8'))
                    logging.warning("Decoded potentially base64 encoded hash string during verification.")
                except Exception:
                     logging.error("Failed to decode potential base64 hash string during verification.")
                     return False
            else:
                return False
        return bcrypt.checkpw(plain_password_bytes, hashed_password)
    except TypeError as e:
         logging.error(f"Type error during password verification: {e}. Ensure hashed_password is bytes.", exc_info=True)
         return False
    except ValueError as e:
        logging.error(f"Value error during password verification: {e}. Ensure the hash format is correct.", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during password verification: {e}", exc_info=True)
        return False


# --- Data Encryption Class ---

class Encryption:
    """
    Handles AES encryption and decryption for data files using AES-GCM.
    Retrieves the 32-byte (256-bit) key from a storage file.
    If the key file or a valid key doesn't exist, it generates a new key,
    saves it (base64 encoded) to the file, and uses it.
    """
    _KEY_FILE_NAME = 'encryption_key.json'
    _KEY_DICT_KEY = 'key_b64' # Key within the JSON file

    def __init__(self):
        """
        Initializes the Encryption class. Loads or generates the encryption key.
        Raises ValueError if key loading/generation fails critically.
        """
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(backend_dir, 'data')
        os.makedirs(data_dir, exist_ok=True) # Ensure data directory exists
        self.key_file_path = os.path.join(data_dir, self._KEY_FILE_NAME)
        self.key = self._load_or_generate_key()
        if not self.key:
             # This should ideally not happen if _load_or_generate_key handles errors properly
             logging.critical("Failed to obtain a valid encryption key during initialization.")
             raise ValueError("Failed to obtain a valid encryption key.")

    def _generate_and_save_new_key(self):
        """Generates a new 32-byte AES key, saves it base64 encoded, and returns the raw bytes."""
        try:
            logging.warning(f"Generating new encryption key and saving to {self.key_file_path}")
            new_key_bytes = get_random_bytes(32)
            new_key_b64 = base64.b64encode(new_key_bytes).decode('utf-8')
            key_data = {self._KEY_DICT_KEY: new_key_b64}

            # Save the key UNENCRYPTED using db_utils
            save_data(self.key_file_path, key_data, is_encrypted=False)

            logging.info(f"Successfully generated and saved new encryption key.")
            return new_key_bytes
        except OSError as e:
            logging.critical(f"Failed to save new encryption key to {self.key_file_path}: {e}", exc_info=True)
            return None
        except Exception as e:
            logging.critical(f"An unexpected error occurred generating/saving key: {e}", exc_info=True)
            return None

    def _load_or_generate_key(self):
        """Loads the encryption key from the file or generates a new one if needed."""
        key_bytes = None
        try:
            # Attempt to load key data (load_data handles file not found)
            # Load the key file UNENCRYPTED
            key_data = load_data(self.key_file_path, default=None, is_encrypted=False)

            if key_data and isinstance(key_data, dict) and self._KEY_DICT_KEY in key_data:
                key_b64 = key_data[self._KEY_DICT_KEY]
                if key_b64 and isinstance(key_b64, str):
                    try:
                        key_bytes = base64.b64decode(key_b64)
                        if len(key_bytes) == 32:
                            logging.info(f"Successfully loaded encryption key from {self.key_file_path}")
                            return key_bytes
                        else:
                            logging.warning(f"Invalid key length ({len(key_bytes)} bytes) found in {self.key_file_path}. Expected 32 bytes. Generating new key.")
                            key_bytes = None # Force regeneration
                    except (base64.binascii.Error, ValueError, TypeError) as decode_err:
                        logging.warning(f"Invalid base64 format for key in {self.key_file_path}: {decode_err}. Generating new key.")
                        key_bytes = None # Force regeneration
                else:
                     logging.warning(f"Invalid key data structure or empty key found in {self.key_file_path}. Generating new key.")
            else:
                logging.info(f"Encryption key file {self.key_file_path} not found or invalid. Generating new key.")

            # If key_bytes is still None, generate and save a new one
            if key_bytes is None:
                key_bytes = self._generate_and_save_new_key()
                if key_bytes is None:
                     logging.critical("Failed to generate and save a new encryption key.")
                     # Raise or handle critical failure as appropriate for the application
                     raise ValueError("Failed to generate and save a new encryption key.")


            return key_bytes

        except Exception as e:
            logging.critical(f"An unexpected error occurred loading/generating encryption key: {e}", exc_info=True)
            # Depending on app requirements, might want to raise here or return None
            raise ValueError(f"Failed to load/generate encryption key: {e}")


    def encrypt(self, plaintext_data):
        """
        Encrypts plaintext data using AES-GCM.

        Args:
            plaintext_data (str): The data to encrypt (typically JSON string).

        Returns:
            str: Base64 encoded string containing nonce, ciphertext, and tag,
                 separated by ';'. Returns None on failure.
        """
        if not isinstance(plaintext_data, str):
            logging.error("Encryption input must be a string.")
            return None
        if not self.key: # Should not happen if constructor worked, but check anyway
             logging.error("Encryption key is not available.")
             return None
        try:
            plaintext_bytes = plaintext_data.encode('utf-8')
            cipher = AES.new(self.key, AES.MODE_GCM)
            nonce = cipher.nonce
            ciphertext, tag = cipher.encrypt_and_digest(plaintext_bytes)
            encrypted_parts = [
                base64.b64encode(nonce).decode('utf-8'),
                base64.b64encode(ciphertext).decode('utf-8'),
                base64.b64encode(tag).decode('utf-8')
            ]
            return ';'.join(encrypted_parts)
        except Exception as e:
            logging.error(f"Error during encryption: {e}", exc_info=True)
            return None

    def decrypt(self, encrypted_data):
        """
        Decrypts data previously encrypted with AES-GCM.

        Args:
            encrypted_data (str): Base64 encoded string containing nonce, ciphertext, and tag,
                                   separated by ';'.

        Returns:
            str: The original plaintext data, or None if decryption or verification fails.
        """
        if not isinstance(encrypted_data, str):
            logging.error("Decryption input must be a string.")
            return None
        if not self.key: # Should not happen if constructor worked
             logging.error("Encryption key is not available for decryption.")
             return None
        try:
            parts = encrypted_data.split(';')
            if len(parts) != 3:
                logging.error("Invalid encrypted data format: Expected 3 parts separated by ';'.")
                return None
            nonce = base64.b64decode(parts[0])
            ciphertext = base64.b64decode(parts[1])
            tag = base64.b64decode(parts[2])
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            plaintext_bytes = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext_bytes.decode('utf-8')
        except (ValueError, KeyError, base64.binascii.Error) as e:
            logging.error(f"Decryption failed (invalid data, key, or integrity check failed): {e}", exc_info=False) # Reduce noise for expected failures
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during decryption: {e}", exc_info=True)
            return None

# Note: Removed the standalone generate_new_encryption_key function as generation
# is now handled within the class initialization logic.

# --- Example Usage (Optional) ---
# if __name__ == '__main__':
#     # --- Password Hashing Example ---
#     # (Password hashing examples remain the same)
#
#     # --- Data Encryption Example ---
#     # The key is now managed internally by the class
#     try:
#         print("\nInitializing Encryption (will load or generate key)...")
#         # Ensure the directory backend/data exists relative to where you run this
#         encryptor = Encryption()
#         print("Encryption initialized successfully.")
#
#         original_data = '{"name": "Test Data", "value": 123, "nested": {"list": [1, 2]}}'
#         print(f"\nOriginal Data: {original_data}")
#
#         encrypted = encryptor.encrypt(original_data)
#         if encrypted:
#             print(f"Encrypted Data: {encrypted}")
#
#             decrypted = encryptor.decrypt(encrypted)
#             if decrypted:
#                 print(f"Decrypted Data: {decrypted}")
#                 assert original_data == decrypted
#             else:
#                 print("Decryption failed.")
#         else:
#             print("Encryption failed.")
#
#         # Test decryption failure
#         print("\nTesting decryption failure with tampered data:")
#         if encrypted:
#             tampered_encrypted = encrypted[:-5] + "XXXXX" # Change the tag part
#             failed_decryption = encryptor.decrypt(tampered_encrypted)
#             print(f"Decryption result for tampered data: {failed_decryption}") # Should be None
#
#     except ValueError as e:
#         print(f"\nEncryption/Decryption Initialization Error: {e}")

