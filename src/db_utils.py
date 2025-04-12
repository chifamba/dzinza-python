import json
import os

def load_data(file_path):
    """
    Loads JSON data from a file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict or list: The loaded data, or None if the file doesn't exist or is empty/invalid.
    """
    if not os.path.exists(file_path):
        print(f"Data file not found: {file_path}")
        return None  # Return None if file doesn't exist

    # Check if file is empty before trying to load
    if os.path.getsize(file_path) == 0:
        print(f"Data file is empty: {file_path}")
        return None # Return None for empty file

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        # Decide how to handle invalid JSON: return None, raise error, or return default
        return None # Return None for invalid JSON
    except Exception as e:
        print(f"An error occurred loading data from {file_path}: {e}")
        # Log this error appropriately in a real application
        return None # Return None on other errors

def save_data(file_path, data):
    """
    Saves data to a JSON file.

    Args:
        file_path (str): The path to the JSON file.
        data (dict or list): The data to save.
    """
    try:
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4) # Use indent for readability
    except Exception as e:
        print(f"An error occurred saving data to {file_path}: {e}")
        # Log this error appropriately
        # Consider raising the exception depending on desired behavior
