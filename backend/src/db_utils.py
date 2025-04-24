# backend/src/db_utils.py
import json
import os
import logging
# Import the actual Encryption class - REMOVED FROM TOP LEVEL

# Cache the Encryption instance
_encryption_instance = None

def _get_encryption_instance():
    """Gets or creates the Encryption instance. Handles import internally."""
    global _encryption_instance
    if _encryption_instance is None:
        try:
            # Import moved inside the function
            from .encryption import Encryption
            _encryption_instance = Encryption()
        except ImportError as e:
            logging.critical(f"Failed to import Encryption class: {e}. Encrypted ops fail.", exc_info=True)
            _encryption_instance = None
        except ValueError as e:
            logging.critical(f"Failed to initialize Encryption instance: {e}. Encrypted ops fail.")
            _encryption_instance = None
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
            logging.error(f"load_data: Cannot load encrypted file {file_path}, Encryption service unavailable.")
            return default if default is not None else {}

    if not os.path.exists(file_path):
        logging.warning(f"load_data: Data file not found: {file_path}. Returning default.")
        return default if default is not None else {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = f.read()
            if not raw_data.strip():
                logging.warning(f"load_data: Data file is empty: {file_path}. Returning default.")
                return default if default is not None else {}

            if is_encrypted:
                if not encryption:
                    logging.error(f"load_data: Encryption instance not available for decryption of {file_path}.")
                    return default if default is not None else {}
                decrypted_data_str = encryption.decrypt(raw_data)
                if decrypted_data_str is None:
                    logging.error(f"load_data: Failed to decrypt data from {file_path}. Returning default.")
                    return default if default is not None else {}
                # Correct indentation for json.loads
                data = json.loads(decrypted_data_str)
            else:
                # Correct indentation for json.loads
                data = json.loads(raw_data)
        return data

    except json.JSONDecodeError as e:
        logging.error(f"load_data: Error decoding JSON from {file_path}: {e}", exc_info=True)
        return default if default is not None else {}
    except OSError as e:
        logging.error(f"load_data: OSError while loading data from {file_path}: {e}", exc_info=True)
        return default if default is not None else {}
    except TypeError as e:
        logging.error(f"load_data: Type error while processing data from {file_path}: {e}", exc_info=True)
        return default if default is not None else {}
    except Exception as e:
        if isinstance(e, RecursionError):
             logging.error(f"load_data: RecursionError occurred while loading data from {file_path}: {e}")
        else:
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
    encryption = None
    if is_encrypted and not append:
        encryption = _get_encryption_instance()
        if not encryption:
            logging.error(f"save_data: Cannot save encrypted file {file_path}, Encryption service not available.")
            return

    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            if append:
                if not isinstance(data, str):
                    logging.error("save_data: When appending, data must be a string.")
                    return
                f.write(data)
            else:
                if is_encrypted:
                    if not encryption:
                         logging.error(f"save_data: Encryption instance not available for encryption of {file_path}.")
                         return
                    json_data_str = json.dumps(data, indent=4)
                    encrypted_data_str = encryption.encrypt(json_data_str)
                    if encrypted_data_str is None:
                        logging.error(f"save_data: Failed to encrypt data for {file_path}.")
                        return
                    # Correct indentation for f.write
                    f.write(encrypted_data_str)
                else:
                    # Correct indentation for json.dump
                    json.dump(data, f, indent=4)

    except TypeError as e:
        logging.error(f"save_data: TypeError saving data to {file_path}: {e}", exc_info=True)
    except OSError as e:
        logging.error(f"save_data: OSError saving data to {file_path}: {e}", exc_info=True)
    except Exception as e:
         if isinstance(e, RecursionError):
              logging.error(f"save_data: RecursionError occurred while saving data to {file_path}: {e}")
         else:
              logging.error(f"save_data: An unexpected error occurred saving data to {file_path}: {e}", exc_info=True)

# Ensure no trailing blank lines or code below this line
