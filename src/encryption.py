# src/encryption.py

import base64
import logging
import hashlib # For password hashing
import warnings # To warn about placeholder security

# --- Placeholder Encryption (Not Secure) ---
# Replace with actual encryption library (e.g., cryptography) for production use.

class DataEncryptor:
    """Interface/Base class for data encryption."""
    def encrypt(self, data: str) -> str:
        raise NotImplementedError

    def decrypt(self, encrypted_data: str) -> str:
        raise NotImplementedError

class PlaceholderDataEncryptor(DataEncryptor):
    """
    A placeholder implementation that 'encrypts' using Base64.
    WARNING: This is NOT secure encryption. It's easily reversible.
             Only for development/testing without real security needs.
    """
    def __init__(self):
        logging.warning("Initialized Placeholder DataEncryptor (Data is NOT encrypted).")

    def encrypt(self, data: str) -> str:
        """Encodes data using Base64."""
        try:
            data_bytes = data.encode('utf-8')
            encrypted_bytes = base64.b64encode(data_bytes)
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logging.error(f"Placeholder encryption failed: {e}")
            return "" # Return empty string or raise error

    def decrypt(self, encrypted_data: str) -> str:
        """Decodes data using Base64."""
        try:
            encrypted_bytes = encrypted_data.encode('utf-8')
            decrypted_bytes = base64.b64decode(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logging.error(f"Placeholder decryption failed: {e}")
            # Handle error appropriately, e.g., return empty string or raise
            # Be careful about errors caused by non-base64 input
            return ""


# --- Password Hashing (Placeholder - Needs Improvement) ---
# Replace with a strong password hashing library like passlib or bcrypt in production.

SALT_LENGTH = 16 # Example salt length (use os.urandom in real implementation)
HASH_ITERATIONS = 100000 # Example iterations (adjust based on performance/security needs)

def hash_password(password: str) -> str:
    """
    Hashes a password using a (placeholder) method.
    WARNING: Uses simple SHA256 with a fixed salt/iterations. NOT SECURE for production.
             Use libraries like passlib or bcrypt which handle salts and iterations properly.
    """
    # Use UserWarning instead of SecurityWarning if SecurityWarning causes NameError
    warnings.warn("Using placeholder password hashing (NOT SECURE).", UserWarning)
    # In a real implementation, generate a unique salt for each password
    # salt = os.urandom(SALT_LENGTH)
    salt = b'fixed_placeholder_salt' # DO NOT USE THIS IN PRODUCTION

    # Use PBKDF2_HMAC for better security than plain SHA256
    # Requires a proper salt and sufficient iterations
    hasher = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        HASH_ITERATIONS
    )
    # Store salt along with the hash (e.g., salt:hash or using a standard format)
    # For this placeholder, we just return the hash part
    return base64.b64encode(hasher).decode('utf-8') # Return base64 encoded hash


def check_password(stored_hash: str, provided_password: str) -> bool:
    """
    Checks if a provided password matches a stored hash (placeholder method).
    WARNING: Assumes the same fixed salt and iterations used in hash_password. NOT SECURE.
    """
    # Use UserWarning instead of SecurityWarning
    warnings.warn("Using placeholder password checking (NOT SECURE).", UserWarning)
    # In a real implementation, extract the salt from the stored value
    salt = b'fixed_placeholder_salt' # Retrieve the correct salt associated with the user

    try:
        # Re-hash the provided password with the same salt and iterations
        provided_hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt,
            HASH_ITERATIONS
        )
        provided_hash = base64.b64encode(provided_hash_bytes).decode('utf-8')

        # Compare the newly generated hash with the stored hash
        # Use a timing-attack-resistant comparison in production (hashlib.compare_digest)
        # Simple comparison for placeholder:
        is_match = (stored_hash == provided_hash)

        # Secure comparison (use this in production):
        # is_match = hashlib.compare_digest(
        #    base64.b64decode(stored_hash.encode('utf-8')), # Decode stored hash if needed
        #    provided_hash_bytes
        # )
        return is_match
    except Exception as e:
        logging.error(f"Error during password check: {e}")
        return False

# Example of how to integrate a real library (e.g., passlib)
# from passlib.context import CryptContext
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# def hash_password_secure(password: str) -> str:
#     return pwd_context.hash(password)
# def check_password_secure(stored_hash: str, provided_password: str) -> bool:
#     return pwd_context.verify(provided_password, stored_hash)

