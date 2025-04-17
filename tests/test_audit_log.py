# tests/test_audit_log.py
import unittest
import os
import sys
from unittest.mock import patch, mock_open
from datetime import datetime

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Now import the modules from src
try:
    from audit_log import log_event, AUDIT_LOG_FILE
except ImportError as e:
    print(f"Error importing audit_log: {e}")
    # Define dummy function if import fails
    def log_event(username, action, details=""): pass
    AUDIT_LOG_FILE = "dummy_audit.log"


class TestAuditLog(unittest.TestCase):
    """
    Test cases for the audit_log module.
    Uses mocking to avoid actual file system operations.
    """

    @patch('audit_log.datetime') # Mock datetime within the audit_log module
    def test_log_event_success(self, mock_datetime):
        """
        Test that log_event writes the correct format to the log file.
        """
        # Setup mock datetime
        mock_now = datetime(2023, 10, 27, 10, 30, 0)
        mock_datetime.now.return_value = mock_now
        timestamp_str = mock_now.strftime('%Y-%m-%d %H:%M:%S')

        username = "testuser"
        action = "LOGIN_SUCCESS"
        details = "User logged in from IP 127.0.0.1"
        expected_log_entry = f"{timestamp_str} - {username} - {action} - {details}\n"

        # Mock open for the audit log file
        m = mock_open()
        with patch('builtins.open', m) as mocked_file, \
             patch('os.makedirs') as mock_makedirs, \
             patch('os.path.dirname', return_value=os.path.dirname(AUDIT_LOG_FILE)) as mock_dirname:

            log_event(username, action, details)

            # Assert directory creation was checked/attempted
            mock_dirname.assert_called_once_with(AUDIT_LOG_FILE)
            mock_makedirs.assert_called_once_with(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)

            # Assert file was opened in append mode
            mocked_file.assert_called_once_with(AUDIT_LOG_FILE, 'a', encoding='utf-8')

            # Assert the correct log entry was written
            handle = m()
            handle.write.assert_called_once_with(expected_log_entry)

    @patch('audit_log.datetime') # Mock datetime within the audit_log module
    def test_log_event_no_details(self, mock_datetime):
        """
        Test log_event when no details are provided.
        """
        # Setup mock datetime
        mock_now = datetime(2023, 10, 27, 10, 35, 0)
        mock_datetime.now.return_value = mock_now
        timestamp_str = mock_now.strftime('%Y-%m-%d %H:%M:%S')

        username = "admin"
        action = "DELETE_USER"
        expected_log_entry = f"{timestamp_str} - {username} - {action} - \n" # Note the trailing space and newline

        # Mock open
        m = mock_open()
        with patch('builtins.open', m) as mocked_file, \
             patch('os.makedirs'), \
             patch('os.path.dirname', return_value=os.path.dirname(AUDIT_LOG_FILE)):

            log_event(username, action) # No details argument

            mocked_file.assert_called_once_with(AUDIT_LOG_FILE, 'a', encoding='utf-8')
            handle = m()
            handle.write.assert_called_once_with(expected_log_entry)


    @patch('audit_log.datetime') # Mock datetime
    def test_log_event_io_error(self, mock_datetime):
        """
        Test log_event when an IOError occurs during file writing.
        It should catch the error and print a message (though we can't easily test print).
        The function should not crash.
        """
        # Setup mock datetime
        mock_now = datetime(2023, 10, 27, 10, 40, 0)
        mock_datetime.now.return_value = mock_now

        username = "user"
        action = "ACTION"
        details = "details"

        # Mock open to raise an IOError on write
        m = mock_open()
        m().write.side_effect = IOError("Permission denied")

        with patch('builtins.open', m) as mocked_file, \
             patch('os.makedirs'), \
             patch('os.path.dirname', return_value=os.path.dirname(AUDIT_LOG_FILE)), \
             patch('builtins.print') as mock_print: # Mock print to check error message

            # We expect the function to execute without raising the IOError further
            try:
                log_event(username, action, details)
            except IOError:
                self.fail("log_event() raised IOError unexpectedly!")

            # Assert that open was called
            mocked_file.assert_called_once_with(AUDIT_LOG_FILE, 'a', encoding='utf-8')
            # Assert that write was called
            handle = m()
            handle.write.assert_called_once()
            # Assert that an error message was printed
            mock_print.assert_called()
            # Check if the print call contains expected error parts
            args, kwargs = mock_print.call_args
            self.assertIn("Failed to write to audit log", args[0])
            self.assertIn("Permission denied", args[0])


if __name__ == '__main__':
    unittest.main()
