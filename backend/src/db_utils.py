# backend/src/db_utils.py
import json
import os
import logging
# Import specific encryption functions
from src.encryption import encrypt_data, decrypt_data, load_key, KEY_FILE # Import key file path constant

def load_data(file_path, default=None, is_encrypted=False):
    """
    Loads JSON data from a file.

    Args:
        file_path (str): The path to the JSON file.
        default (any, optional): Value to return if file not found or invalid. Defaults to None.
        is_encrypted (bool): Indicates if the data needs to be decrypted. Defaults to False.

    Returns:
        dict or list or any: The loaded data, or the default value on error/not found.
    """
    key = None
    if is_encrypted:
        try:
            key = load_key(KEY_FILE) # Load the encryption key
        except FileNotFoundError:
            logging.error(f"load_data: Encryption key file not found at {KEY_FILE}. Cannot decrypt {file_path}.")
            return default if default is not None else {}
        except ValueError as e:
            logging.error(f"load_data: Invalid encryption key in file {KEY_FILE}: {e}. Cannot decrypt {file_path}.")
            return default if default is not None else {}
        except Exception as e:
            logging.error(f"load_data: Unexpected error loading encryption key from {KEY_FILE}: {e}. Cannot decrypt {file_path}.", exc_info=True)
            return default if default is not None else {}


    if not os.path.exists(file_path):
        logging.warning(f"load_data: Data file not found: {file_path}. Returning default.")
        return default if default is not None else {}

    try:
        with open(file_path, 'rb' if is_encrypted else 'r', encoding='utf-8' if not is_encrypted else None) as f:
            raw_data = f.read()
            if not raw_data: # Check for empty file content
                logging.warning(f"load_data: Data file is empty: {file_path}. Returning default.")
                return default if default is not None else {}

            if is_encrypted:
                if key is None: # Should not happen if load_key raised exceptions, but as a safeguard
                     logging.error(f"load_data: Encryption key is None for encrypted file {file_path}.")
                     return default if default is not None else {}
                try:
                    # decrypt_data expects bytes, raw_data is bytes when reading in 'rb' mode
                    decrypted_data_str = decrypt_data(key, raw_data)
                except ValueError as e: # Catch decryption errors
                    logging.error(f"load_data: Failed to decrypt data from {file_path}: {e}. Returning default.")
                    return default if default is not None else {}
                except Exception as e:
                     logging.error(f"load_data: Unexpected error during decryption of {file_path}: {e}", exc_info=True)
                     return default if default is not None else {}

                # Decrypted data should be JSON string
                data = json.loads(decrypted_data_str)
            else:
                # raw_data is str when reading in 'r' mode
                data = json.loads(raw_data)

        return data

    except json.JSONDecodeError as e:
        logging.error(f"load_data: Error decoding JSON from {file_path}: {e}", exc_info=True)
        return default if default is not None else {}
    except OSError as e:
        logging.error(f"load_data: OSError while loading data from {file_path}: {e}", exc_info=True)
        return default if default is not None else {}
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"load_data: An unexpected error occurred loading data from {file_path}: {e}", exc_info=True)
        return default if default is not None else {}


def save_data(file_path, data, is_encrypted=False, append=False):
    """
    Saves data to a file (JSON or plain text if appending).

    Args:
        file_path (str): The path to the file.
        data (dict or list or str): The data to save. If not appending, expected to be JSON-serializable. If appending, must be a string.
        is_encrypted (bool): Encrypt the data before saving (only if not appending). Defaults to False.
        append (bool): Append the data string to the file instead of overwriting. Defaults to False.
    """
    key = None
    if is_encrypted and not append:
        try:
            key = load_key(KEY_FILE) # Load the encryption key
        except FileNotFoundError:
            logging.error(f"save_data: Encryption key file not found at {KEY_FILE}. Cannot encrypt {file_path}.")
            return
        except ValueError as e:
            logging.error(f"save_data: Invalid encryption key in file {KEY_FILE}: {e}. Cannot encrypt {file_path}.")
            return
        except Exception as e:
            logging.error(f"save_data: Unexpected error loading encryption key from {KEY_FILE}: {e}. Cannot encrypt {file_path}.", exc_info=True)
            return


    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        mode = 'a' if append else ('wb' if is_encrypted else 'w') # Use 'wb' for encrypted data (bytes)
        with open(file_path, mode, encoding='utf-8' if not is_encrypted or append else None) as f:
            if append:
                if not isinstance(data, str):
                    logging.error("save_data: When appending, data must be a string.")
                    return
                f.write(data)
            else:
                # Data should be JSON-serializable for non-append mode
                json_data_str = json.dumps(data, indent=4)

                if is_encrypted:
                    if key is None: # Should not happen if load_key raised exceptions, but as a safeguard
                         logging.error(f"save_data: Encryption key is None for encrypted file {file_path}.")
                         return
                    try:
                        # encrypt_data returns bytes
                        encrypted_data_bytes = encrypt_data(key, json_data_str)
                    except ValueError as e: # Catch encryption errors
                        logging.error(f"save_data: Failed to encrypt data for {file_path}: {e}.")
                        return
                    except Exception as e:
                         logging.error(f"save_data: Unexpected error during encryption of {file_path}: {e}", exc_info=True)
                         return

                    f.write(encrypted_data_bytes) # Write bytes
                else:
                    f.write(json_data_str) # Write string

    except TypeError as e:
        logging.error(f"save_data: TypeError saving data to {file_path}: {e}", exc_info=True)
    except OSError as e:
        logging.error(f"save_data: OSError saving data to {file_path}: {e}", exc_info=True)
    except Exception as e:
         # Catch any other unexpected errors
         logging.error(f"save_data: An unexpected error occurred saving data to {file_path}: {e}", exc_info=True)

# Ensure no trailing blank lines or code below this line
