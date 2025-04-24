# backend/tests/test_audit_log.py
import unittest
import os
import tempfile
from datetime import datetime
# Assuming log_audit is in backend.src.audit_log
# Adjust the import based on your actual structure
try:
    from backend.src.audit_log import log_audit, read_audit_log
except ImportError:
    print("Warning: Could not import audit log functions from backend.src.audit_log")
    # Define dummy functions if import fails, so tests can run structurally
    def log_audit(*args, **kwargs): pass
    def read_audit_log(*args, **kwargs): return []


class TestAuditLog(unittest.TestCase):

    def setUp(self):
        """Create a temporary file for logging."""
        # Create a temporary file and get its path
        self.temp_fd, self.temp_log_path = tempfile.mkstemp(suffix=".log")
        # Ensure the file descriptor is closed immediately, we only need the path
        os.close(self.temp_fd)

    def tearDown(self):
        """Remove the temporary log file."""
        # Check if the file exists before trying to remove it
        if os.path.exists(self.temp_log_path):
            os.remove(self.temp_log_path)

    def test_log_audit_creates_file(self):
        """Test that logging creates the file if it doesn't exist."""
        # Ensure file is removed before test
        if os.path.exists(self.temp_log_path):
            os.remove(self.temp_log_path)
        self.assertFalse(os.path.exists(self.temp_log_path))
        log_audit(self.temp_log_path, "testuser", "login", "success")
        self.assertTrue(os.path.exists(self.temp_log_path))

    def test_log_audit_writes_correct_format(self):
        """Test that the log entry has the expected format."""
        user = "testuser"
        action = "create_person"
        details = "id: 123, name: John Doe"
        log_audit(self.temp_log_path, user, action, details)

        with open(self.temp_log_path, 'r') as f:
            log_content = f.readline().strip()

        # Check parts of the log entry
        self.assertIn(user, log_content)
        self.assertIn(action, log_content)
        self.assertIn(details, log_content)
        # Check for timestamp format (e.g., YYYY-MM-DD HH:MM:SS)
        try:
            # Extract timestamp part (assuming it's at the beginning)
            timestamp_str = log_content.split(" - ")[0]
            datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, IndexError):
            self.fail("Log timestamp format is incorrect or missing.")

    def test_read_audit_log_returns_list(self):
        """Test that reading the log returns a list of entries."""
        log_audit(self.temp_log_path, "user1", "action1", "details1")
        log_audit(self.temp_log_path, "user2", "action2", "details2")

        log_entries = read_audit_log(self.temp_log_path)
        self.assertIsInstance(log_entries, list)
        self.assertEqual(len(log_entries), 2)
        self.assertIn("user1 - action1 - details1", log_entries[0])
        self.assertIn("user2 - action2 - details2", log_entries[1])

    def test_read_audit_log_empty_file(self):
        """Test reading an empty log file."""
        log_entries = read_audit_log(self.temp_log_path)
        self.assertEqual(log_entries, [])

    def test_read_audit_log_file_not_found(self):
        """Test reading a non-existent log file."""
        # Ensure file is removed
        if os.path.exists(self.temp_log_path):
            os.remove(self.temp_log_path)
        log_entries = read_audit_log(self.temp_log_path)
        self.assertEqual(log_entries, [])


if __name__ == '__main__':
    unittest.main()
