import json
import os

import logging
from .encryption import Encryption 

def load_data(file_path, is_encrypted=False):
    """
    Loads JSON data from a file.

    Args:
        file_path (str): The path to the JSON file.
        is_encrypted (bool): Indicates if the data needs to be decrypted.

    Returns:
        dict or list: The loaded data, or None if the file doesn't exist or is empty/invalid.
    """
    encryption = Encryption() if is_encrypted else None
    if not os.path.exists(file_path):
        logging.warning(f"load_data: Data file not found: {file_path}")
        return None
    if os.path.getsize(file_path) == 0:
        logging.warning(f"load_data: Data file is empty: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if is_encrypted:
                encrypted_data = f.read()
                if not encrypted_data:
                    logging.warning(f"load_data: Encrypted data file is empty: {file_path}")
                    return None  
                decrypted_data = encryption.decrypt(encrypted_data)
                data = json.loads(decrypted_data)
            else:
                data = json.load(f)
        return data

    except json.JSONDecodeError as e:
        logging.error(f"load_data: Error decoding JSON from {file_path}: {e}", exc_info=True)
        return None  # Return None for invalid JSON
    except OSError as e:
        logging.error(f"load_data: OSError while loading data from {file_path}: {e}", exc_info=True)
        return None
    except TypeError as e:
        logging.error(f"load_data: Type error while loading data from {file_path}: {e}", exc_info=True)
        return None
    except Exception as e:  # Catching other exceptions
        logging.error(f"load_data: An error occurred while loading data from {file_path}: {e}", exc_info=True)
        return None
    
def save_data(file_path, data, is_encrypted=False, append=False):
    """
    Saves data to a JSON file.

    Args:
        file_path (str): The path to the JSON file.
        data (dict or list): The data to save.
    """
    encryption = Encryption() if is_encrypted else None
    try:
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if append:
            # Handle appending to file
            if not isinstance(data, str):
                raise ValueError("When appending, data must be a string.")
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(data)
        else:
            # Handle overwriting file (normal behavior)
            with open(file_path, 'w', encoding='utf-8') as f:
                if is_encrypted:
                    json_data = json.dumps(data)
                    encrypted_data = encryption.encrypt(json_data)
                    f.write(encrypted_data)
                else:
                    json.dump(data, f, indent=4)

    except Exception as e:
        logging.error(f"save_data: An error occurred saving data to {file_path}: {e}", exc_info=True)


