import os
from datetime import datetime

# Default log directory (can be overridden by path passed to log_audit)
LOG_DIR = 'data'

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
        # Ensure the directory for the log file exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir: # Check if path includes a directory
             os.makedirs(log_dir, exist_ok=True)

        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Format the log message
        log_message = f"{timestamp} - User: {user:<15} | Action: {action:<20} | Status/Details: {status_details}\n"

        # Append the message to the log file
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_message)

    except Exception as e:
        # Print error to console if logging fails (avoid infinite loop if logging itself fails)
        print(f"!!! FAILED TO WRITE AUDIT LOG to {log_file_path} !!!")
        print(f"!!! Error: {e} !!!")
        print(f"!!! Log details: User={user}, Action={action}, Details={status_details} !!!")


# Example usage (can be removed or kept for testing this module directly)
if __name__ == '__main__':
    # Define a test log file path
    test_log_file = os.path.join(LOG_DIR, 'test_audit.log')
    print(f"Testing audit log writing to: {test_log_file}")

    # Ensure the test log file is clean before test
    if os.path.exists(test_log_file):
        os.remove(test_log_file)

    log_audit(test_log_file, 'system', 'startup', 'Audit log test initialized')
    log_audit(test_log_file, 'testuser_1', 'login_attempt', 'Success')
    log_audit(test_log_file, 'testuser_2', 'add_person', 'failure - missing name')
    log_audit(test_log_file, 'admin', 'delete_user', 'success - user_id: abc-123')

    print(f"Test log entries written. Check the content of {test_log_file}")

    try:
        with open(test_log_file, 'r', encoding='utf-8') as f:
            print("\n--- Content of test_audit.log ---")
            print(f.read())
            print("---------------------------------")
    except FileNotFoundError:
        print("Test log file not found after writing attempts.")

