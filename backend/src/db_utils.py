# backend/src/db_utils.py
import json
import os
import logging
# Import the actual Encryption class
from .encryption import Encryption

# Cache the Encryption instance to avoid recreating it and reading env var repeatedly
_encryption_instance = None

def _get_encryption_instance():
    """Gets or creates the Encryption instance."""
    global _encryption_instance
    if _encryption_instance is None:
        try:
            _encryption_instance = Encryption()
        except ValueError as e:
            # Log critical error if key is missing/invalid, but allow app to continue
            # if encryption isn't strictly required for all operations.
            # load/save will fail later if is_encrypted=True is passed.
            logging.critical(f"Failed to initialize Encryption instance: {e}. Encrypted operations will fail.")
            _encryption_instance = None # Ensure it stays None if init fails
    return _encryption_instance

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
    encryption = None
    if is_encrypted:
        encryption = _get_encryption_instance()
        if not encryption:
            logging.error(f"load_data: Cannot load encrypted file {file_path}, Encryption service not available.")
            return default

    if not os.path.exists(file_path):
        logging.warning(f"load_data: Data file not found: {file_path}. Returning default.")
        return default

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = f.read()
            if not raw_data:
                logging.warning(f"load_data: Data file is empty: {file_path}. Returning default.")
                return default

            if is_encrypted:
                decrypted_data_str = encryption.decrypt(raw_data)
                if decrypted_data_str is None:
                    logging.error(f"load_data: Failed to decrypt data from {file_path}. Returning default.")
                    return default
                data = json.loads(decrypted_data_str)
            else:
                # If not encrypted, parse directly from the raw data read
                data = json.loads(raw_data)
        return data

    except json.JSONDecodeError as e:
        logging.error(f"load_data: Error decoding JSON from {file_path}: {e}", exc_info=True)
        return default
    except OSError as e:
        logging.error(f"load_data: OSError while loading data from {file_path}: {e}", exc_info=True)
        return default
    except TypeError as e:
        # More likely during decryption or JSON parsing if data is malformed
        logging.error(f"load_data: Type error while processing data from {file_path}: {e}", exc_info=True)
        return default
    except Exception as e:
        logging.error(f"load_data: An unexpected error occurred while loading data from {file_path}: {e}", exc_info=True)
        return default

def save_data(file_path, data, is_encrypted=False, append=False):
    """
    Saves data to a file (JSON or plain text if appending).

    Args:
        file_path (str): The path to the file.
        data (dict or list or str): The data to save. If not appending, expected to be JSON-serializable. If appending, must be a string.
        is_encrypted (bool): Encrypt the data before saving (only if not appending). Defaults to False.
        append (bool): Append the data string to the file instead of overwriting. Defaults to False.
    """
    encryption = None
    if is_encrypted and not append:
        encryption = _get_encryption_instance()
        if not encryption:
            logging.error(f"save_data: Cannot save encrypted file {file_path}, Encryption service not available.")
            return # Prevent saving unencrypted data when encryption is requested but unavailable

    try:
        # Ensure the directory exists before writing
        dir_name = os.path.dirname(file_path)
        if dir_name: # Avoid error if file_path is just a filename in the current dir
            os.makedirs(dir_name, exist_ok=True)

        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            if append:
                if not isinstance(data, str):
                    logging.error("save_data: When appending, data must be a string.")
                    raise ValueError("When appending, data must be a string.")
                f.write(data)
            else:
                # Handle overwriting file (normal JSON behavior)
                if is_encrypted:
                    json_data_str = json.dumps(data, indent=4) # Serialize first
                    encrypted_data_str = encryption.encrypt(json_data_str)
                    if encrypted_data_str is None:
                        logging.error(f"save_data: Failed to encrypt data for {file_path}.")
                        # Optionally raise an error or just return to prevent writing partial/bad data
                        return
                    f.write(encrypted_data_str)
                else:
                    json.dump(data, f, indent=4) # Save as formatted JSON

    except TypeError as e:
        # Typically happens if 'data' is not JSON serializable when not appending
        logging.error(f"save_data: TypeError saving data to {file_path} (is data JSON serializable?): {e}", exc_info=True)
    except OSError as e:
        logging.error(f"save_data: OSError saving data to {file_path}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"save_data: An unexpected error occurred saving data to {file_path}: {e}", exc_info=True)

