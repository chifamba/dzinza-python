# backend/src/encryption.py
import bcrypt
import os
import logging
import base64
import json
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
# from Crypto.Util.Padding import pad, unpad # Not used in GCM mode

# Import db_utils for loading/saving the key
from .db_utils import load_data, save_data

# --- Password Hashing ---

def hash_password(password):
    """Hashes a password using bcrypt."""
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
    """Verifies a plaintext password against a stored bcrypt hash."""
    if not plain_password or not hashed_password:
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
         logging.error(f"Type error during password verification: {e}. Ensure hash format is correct.", exc_info=True)
         return False
    except ValueError as e:
        logging.warning(f"Password verification failed for hash: {e}.")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during password verification: {e}", exc_info=True)
        return False


# --- Data Encryption Class ---

class Encryption:
    """Handles AES encryption and decryption using AES-GCM."""
    _KEY_FILE_NAME = 'encryption_key.json'
    _KEY_DICT_KEY = 'key_b64'

    def __init__(self):
        """Initializes Encryption, loads/generates the key."""
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(backend_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.key_file_path = os.path.join(data_dir, self._KEY_FILE_NAME)
        self.key = self._load_or_generate_key()
        if not self.key:
             logging.critical("Failed to obtain a valid encryption key during initialization.")
             raise ValueError("Failed to obtain a valid encryption key.")

    def _generate_and_save_new_key(self):
        """Generates and saves a new 32-byte AES key."""
        try:
            logging.warning(f"Generating new encryption key and saving to {self.key_file_path}")
            new_key_bytes = get_random_bytes(32)
            new_key_b64 = base64.b64encode(new_key_bytes).decode('utf-8')
            key_data = {self._KEY_DICT_KEY: new_key_b64}
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
        """Loads the encryption key or generates a new one."""
        key_bytes = None
        try:
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
                            logging.warning(f"Invalid key length ({len(key_bytes)} bytes) in {self.key_file_path}. Generating new key.")
                            key_bytes = None
                    except (base64.binascii.Error, ValueError, TypeError) as decode_err:
                        logging.warning(f"Invalid base64 format for key in {self.key_file_path}: {decode_err}. Generating new key.")
                        key_bytes = None
                else:
                     logging.warning(f"Invalid key data structure or empty key in {self.key_file_path}. Generating new key.")
            else:
                logging.info(f"Encryption key file {self.key_file_path} not found or invalid. Generating new key.")

            if key_bytes is None:
                key_bytes = self._generate_and_save_new_key()
                if key_bytes is None:
                     raise ValueError("Failed to generate and save a new encryption key.")

            return key_bytes
        except Exception as e:
            logging.critical(f"An unexpected error occurred loading/generating encryption key: {e}", exc_info=True)
            raise ValueError(f"Failed to load/generate encryption key: {e}")


    def encrypt(self, plaintext_data):
        """Encrypts plaintext data using AES-GCM."""
        if not isinstance(plaintext_data, str):
            logging.error("Encryption input must be a string.")
            return None
        if not self.key:
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
        """Decrypts data previously encrypted with AES-GCM."""
        if not isinstance(encrypted_data, str):
            logging.error("Decryption input must be a string.")
            return None
        if not self.key:
             logging.error("Encryption key is not available for decryption.")
             return None
        try:
            parts = encrypted_data.split(';')
            if len(parts) != 3:
                # Log specific format error instead of generic decryption failure
                logging.error(f"Invalid encrypted data format: Expected 3 parts separated by ';', got {len(parts)} parts.")
                return None

            nonce = base64.b64decode(parts[0])
            ciphertext = base64.b64decode(parts[1])
            tag = base64.b64decode(parts[2])

            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            plaintext_bytes = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext_bytes.decode('utf-8')
        except (ValueError, KeyError, base64.binascii.Error) as e:
            logging.error(f"Decryption failed (invalid data, key, or integrity check failed): {e}", exc_info=False) # Keep exc_info False here
            return None
        # --- MODIFIED EXCEPTION LOGGING ---
        except Exception as e:
             # Check if it's a RecursionError to avoid deep traceback logging
             if isinstance(e, RecursionError):
                  logging.error(f"An unexpected RecursionError occurred during decryption: {e}")
             else:
                  # Log other exceptions with full traceback
                  logging.error(f"An unexpected error occurred during decryption: {e}", exc_info=True)
             return None
        # --- END MODIFIED EXCEPTION LOGGING ---

