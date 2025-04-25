# backend/src/encryption.py
import os
import base64
# Removed unused json import
import logging # Added logging import
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey, InvalidTag # Import InvalidTag for decryption errors

# --- Constants ---
KEY_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'encryption_key.key') # Adjusted path relative to src
# For password hashing/key derivation
SALT_SIZE = 16
ITERATIONS = 390000 # Recommended iterations for PBKDF2

# --- Key Management ---
def generate_key() -> bytes:
    """Generates a new Fernet key."""
    return Fernet.generate_key()

def save_key(key: bytes, key_file_path: str = KEY_FILE):
    """Saves the key to a file."""
    os.makedirs(os.path.dirname(key_file_path), exist_ok=True) # Ensure directory exists
    with open(key_file_path, "wb") as key_file:
        key_file.write(key)

def load_key(key_file_path: str = KEY_FILE) -> bytes:
    """Loads the key from a file."""
    if not os.path.exists(key_file_path):
        raise FileNotFoundError(f"Encryption key file not found at {key_file_path}")
    with open(key_file_path, "rb") as key_file:
        key = key_file.read()
    # Basic validation: Fernet keys are base64 encoded and 32 bytes long after decoding
    try:
        if len(base64.urlsafe_b64decode(key)) != 32:
            raise ValueError("Invalid key length loaded from file.")
    except Exception as e:
         raise ValueError(f"Invalid key format in file: {e}")
    return key

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derives an encryption key from a password using PBKDF2."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    if not isinstance(salt, bytes) or len(salt) != SALT_SIZE:
        raise ValueError(f"Salt must be {SALT_SIZE} bytes.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32, # Fernet key length
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    # Encode password to bytes before deriving key
    key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
    return key

def generate_salt(size: int = SALT_SIZE) -> bytes:
    """Generates a cryptographically secure salt."""
    return os.urandom(size)

# --- Encryption/Decryption ---
def encrypt_data(key: bytes, data: str) -> bytes:
    """Encrypts string data using the provided Fernet key."""
    if not isinstance(data, str):
        # If you need to encrypt non-string data, serialize it first (e.g., json.dumps)
        raise TypeError("Data to encrypt must be a string.")
    try:
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode('utf-8'))
        return encrypted_data
    except (InvalidKey, TypeError) as e:
        # Log error appropriately
        raise ValueError(f"Encryption failed due to invalid key or data type: {e}")

def decrypt_data(key: bytes, encrypted_data: bytes) -> str:
    """Decrypts data using the provided Fernet key."""
    if not isinstance(encrypted_data, bytes):
        raise TypeError("Encrypted data must be bytes.")
    try:
        f = Fernet(key)
        decrypted_data_bytes = f.decrypt(encrypted_data)
        return decrypted_data_bytes.decode('utf-8')
    except (InvalidKey, InvalidTag, TypeError) as e:
        # InvalidTag means decryption failed (wrong key or tampered data)
        # Log error appropriately
        raise ValueError(f"Decryption failed. Invalid key, tampered data, or incorrect data type: {e}")

# --- Password Hashing and Verification (Placeholders) ---
def hash_password(password: str) -> str:
    """Hashes a password (Placeholder)."""
    logging.warning("Encryption service 'hash_password' is a placeholder.")
    # TODO: Implement actual password hashing using a secure library (e.g., bcrypt, argon2)
    # This placeholder just returns the password prefixed, NOT secure
    return f"hashed_placeholder_{password}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a password against a hashed password (Placeholder)."""
    logging.warning("Encryption service 'verify_password' is a placeholder.")
    # TODO: Implement actual password verification using the same secure library as hashing
    # This placeholder just checks the prefix, NOT secure
    return hashed_password == f"hashed_placeholder_{password}"


# --- Example Usage (Optional) ---
if __name__ == "__main__":
    # This block is for demonstration or manual key generation/testing.
    # It shouldn't run as part of the main application flow.

    # 1. Generate and save a key if it doesn't exist
    if not os.path.exists(KEY_FILE):
        print(f"Key file not found at {KEY_FILE}. Generating a new key.")
        new_key = generate_key()
        save_key(new_key, KEY_FILE)
        print("New key generated and saved.")
    else:
        print(f"Key file found at {KEY_FILE}.")

    # 2. Load the key
    try:
        loaded_key = load_key()
        print("Key loaded successfully.")

        # 3. Encrypt/Decrypt Example
        secret = "My secret data point!"
        print(f"Original: {secret}")

        encrypted = encrypt_data(loaded_key, secret)
        # Fixed F541: Added placeholder or removed f-prefix
        print(f"Encrypted: {encrypted}") # Show bytes representation

        decrypted = decrypt_data(loaded_key, encrypted)
        print(f"Decrypted: {decrypted}")

        assert secret == decrypted
        print("Encryption/Decryption test successful.")

        # 4. Password Derivation Example
        password = "mysecretpassword"
        salt = generate_salt()
        derived_key = derive_key_from_password(password, salt)
        print(f"\nDerived key from password (example): {derived_key}")
        print(f"Salt used (store this with the user/data): {salt.hex()}")

        # You would store the salt and use it to re-derive the key for decryption later
        re_derived_key = derive_key_from_password(password, salt)
        assert derived_key == re_derived_key
        print("Key derivation test successful.")

        # Example encrypting with derived key
        data_for_derived = "Data encrypted with derived key"
        encrypted_derived = encrypt_data(derived_key, data_for_derived)
        decrypted_derived = decrypt_data(derived_key, encrypted_derived)
        assert data_for_derived == decrypted_derived
        print("Encryption/Decryption with derived key successful.")

        # Example Password Hashing/Verification (using placeholders)
        test_password = "securepassword123"
        hashed = hash_password(test_password)
        print(f"\nTest Password: {test_password}")
        print(f"Placeholder Hashed: {hashed}")
        print(f"Verification (correct): {verify_password(test_password, hashed)}")
        print(f"Verification (incorrect): {verify_password('wrongpassword', hashed)}")


    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

