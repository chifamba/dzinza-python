import bcrypt
import os # Often needed for salt generation or management, though bcrypt handles salts internally
import logging

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
        logging.error("Error: Password cannot be empty.")
        return None
    try:
        # Encode the password string to bytes (UTF-8 is common)
        password_bytes = password.encode('utf-8')
        # Generate salt and hash the password
        # bcrypt.gensalt() determines the work factor (rounds); default is usually sufficient
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        return hashed_password
    except Exception as e:
        logging.error(f"Error hashing password: {e}", exc_info=True)
        # Log this error in a real application
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
        logging.error("Error: Both plain password and hashed password must be provided for verification.")
        return False
    try:
        # Ensure the plaintext password is in bytes
        plain_password_bytes = plain_password.encode('utf-8')

        # bcrypt.checkpw handles comparing the plaintext (bytes) against the hash (bytes)
        return bcrypt.checkpw(plain_password_bytes, hashed_password)
    except TypeError as e:
         # This might happen if hashed_password is not bytes (e.g., loaded incorrectly as string)
         logging.error(f"Type error during password verification: {e}. Ensure hashed_password is bytes.", exc_info=True)
         return False
    except ValueError as e:
        # This can happen if the hash format is invalid
        logging.error(f"Value error during password verification: {e}. Ensure the hash format is correct.", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during password verification: {e}", exc_info=True)

        return False

# --- Example Usage (Optional) ---
# if __name__ == '__main__':
#     # Example of hashing
#     password_to_hash = "mysecretp@ssw0rd"
#     hashed = hash_password(password_to_hash)
#     if hashed:
#         print(f"Original: {password_to_hash}")
#         print(f"Hashed: {hashed}") # Note: This is bytes

#         # Example of verification
#         is_valid_correct = verify_password(password_to_hash, hashed)
#         print(f"Verification (correct password): {is_valid_correct}") # Should be True

#         is_valid_incorrect = verify_password("wrongpassword", hashed)
#         print(f"Verification (incorrect password): {is_valid_incorrect}") # Should be False

#         # Example with incorrect hash type (string instead of bytes)
#         try:
#             verify_password(password_to_hash, hashed.decode('utf-8')) # Pass hash as string
#         except Exception as e:
#             print(f"Caught expected error with wrong hash type: {e}")

