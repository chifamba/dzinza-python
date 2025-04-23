import os
import logging
from datetime import datetime
from .db_utils import save_data

# Default log directory (can be overridden by path passed to log_audit)
LOG_DIR = 'backend'


def log_audit(log_file_path, user, action, status_details=""):
    """
    Logs an audit event to the specified file.

    Args:
        log_file_path (str): The full path to the audit log file.
        user (str): The username or identifier of the actor performing the action.
        action (str): A short description of the action being performed (e.g., 'login', 'add_person').
        status_details (str, optional): Additional details or status (e.g., 'success', 'failure - invalid password', 'id: xyz'). Defaults to "".
    """
    try:
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Format the log message
        log_message = f"{timestamp} - User: {user:<15} | Action: {action:<20} | Status/Details: {status_details}\n"

        # Append the message to the log file using save_data
        save_data(log_file_path, log_message, append=True)

    except Exception as e:
        # Log error if logging fails (avoid infinite loop if logging itself fails)
        logging.error(f"log_audit - Failed to write audit log to {log_file_path}", exc_info=True)
        logging.error(f"log_audit - Error details: {e}")
        logging.error(f"log_audit - Log details: User={user}, Action={action}, Details={status_details}")


