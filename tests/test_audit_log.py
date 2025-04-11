import unittest
from datetime import datetime, timedelta
from src.audit_log import AuditLog


class TestAuditLog(unittest.TestCase):
    def setUp(self):
        """Set up a fresh AuditLog instance for each test."""
        self.audit_log = AuditLog()

    def test_log_event(self):
        """Test adding a new event to the log."""
        self.audit_log.log_event("user1", "login", "User logged in")
        self.assertEqual(len(self.audit_log.log_entries), 1)
        entry = self.audit_log.log_entries[0]
        self.assertEqual(entry["user_id"], "user1")
        self.assertEqual(entry["event_type"], "login")
        self.assertEqual(entry["description"], "User logged in")
        self.assertIsInstance(entry["timestamp"], datetime)

    def test_get_log_entries_no_filter(self):
        """Test getting all log entries without any filters."""
        self.audit_log.log_event("user1", "login", "User logged in")
        self.audit_log.log_event("user2", "logout", "User logged out")
        entries = self.audit_log.get_log_entries()
        self.assertEqual(len(entries), 2)

    def test_get_log_entries_by_user(self):
        """Test getting log entries filtered by user ID."""
        self.audit_log.log_event("user1", "login", "User logged in")
        self.audit_log.log_event("user2", "logout", "User logged out")
        self.audit_log.log_event("user1", "action", "User performed action")
        entries = self.audit_log.get_log_entries(user_id="user1")
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertEqual(entry["user_id"], "user1")

    def test_get_log_entries_by_event_type(self):
        """Test getting log entries filtered by event type."""
        self.audit_log.log_event("user1", "login", "User logged in")
        self.audit_log.log_event("user2", "logout", "User logged out")
        self.audit_log.log_event("user1", "login", "User logged in again")
        entries = self.audit_log.get_log_entries(event_type="login")
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertEqual(entry["event_type"], "login")

    def test_get_log_entries_by_date_range(self):
        """Test getting log entries filtered by date range."""
        now = datetime.now()
        past = now - timedelta(days=1)
        future = now + timedelta(days=1)
        self.audit_log.log_event("user1", "login", "User logged in", timestamp=past)
        self.audit_log.log_event("user2", "logout", "User logged out", timestamp=now)
        self.audit_log.log_event("user1", "login", "User logged in again", timestamp=future)
        entries = self.audit_log.get_log_entries(start_date=now, end_date=future)
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertTrue(now <= entry["timestamp"] <= future)

    def test_get_log_entries_multiple_filters(self):
        """Test getting log entries filtered by multiple criteria."""
        now = datetime.now()
        past = now - timedelta(days=1)
        future = now + timedelta(days=1)
        self.audit_log.log_event("user1", "login", "User logged in", timestamp=past)
        self.audit_log.log_event("user2", "logout", "User logged out", timestamp=now)
        self.audit_log.log_event("user1", "login", "User logged in again", timestamp=future)
        entries = self.audit_log.get_log_entries(
            user_id="user1", event_type="login", start_date=past, end_date=future
        )
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertEqual(entry["user_id"], "user1")
            self.assertEqual(entry["event_type"], "login")
            self.assertTrue(past <= entry["timestamp"] <= future)
            

    def test_get_log_entries_invalid_date(self):
        """Test getting log entries with an invalid date."""
        self.audit_log.log_event("user1", "login", "User logged in")
        self.assertRaises(ValueError, self.audit_log.get_log_entries, start_date="invalid")

    def test_clear_log(self):
        """Test clearing all log entries."""
        self.audit_log.log_event("user1", "login", "User logged in")
        self.audit_log.log_event("user2", "logout", "User logged out")
        self.audit_log.clear_log()
        self.assertEqual(len(self.audit_log.log_entries), 0)


if __name__ == "__main__":
    unittest.main()