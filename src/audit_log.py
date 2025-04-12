# src/audit_log.py

import logging
from datetime import datetime
import abc # Abstract Base Classes

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - AUDIT - %(message)s')

class AuditLog(abc.ABC):
    """Abstract base class for audit logging."""

    @abc.abstractmethod
    def log_event(self, user: str, event: str, description: str) -> None:
        """Logs an audit event."""
        pass

    @abc.abstractmethod
    def get_logs(self, count: int = 100) -> list:
        """Retrieves recent log entries."""
        pass

class SimpleAuditLog(AuditLog):
    """A simple in-memory audit log implementation."""

    def __init__(self, max_entries: int = 1000):
        self.logs = []
        self.max_entries = max_entries
        logging.info(f"Initialized SimpleAuditLog with max_entries={max_entries}")

    def log_event(self, user: str, event: str, description: str) -> None:
        """Logs an event with timestamp, user, event type, and description."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "user": user,
            "event": event,
            "description": description
        }
        # Basic logging to console/file
        logging.info(f"User: {user}, Event: {event}, Desc: {description}")
        # Store in memory, maintaining max size
        self.logs.append(log_entry)
        if len(self.logs) > self.max_entries:
            self.logs.pop(0) # Remove the oldest entry

    def get_logs(self, count: int = 100) -> list:
        """Returns the most recent 'count' log entries."""
        return self.logs[-count:]

class PlaceholderAuditLog(AuditLog):
    """
    A placeholder implementation that does nothing but print a message
    on initialization. Useful when audit logging is not required or
    configured.
    """
    def __init__(self):
        # Log only once during initialization that this is a placeholder
        print("Initialized Placeholder AuditLog.") # Use print as basic logging might not be set up yet
        logging.info("Initialized Placeholder AuditLog (Events will not be stored).")

    def log_event(self, user: str, event: str, description: str) -> None:
        """Placeholder: Does not store or log events."""
        # Optionally print here for debugging during development
        # print(f"AUDIT LOG PLACEHOLDER [User: {user}, Event: {event}, Desc: {description}]")
        pass # Intentionally does nothing

    def get_logs(self, count: int = 100) -> list:
        """Placeholder: Returns an empty list."""
        return []

# Example usage (optional)
if __name__ == "__main__":
    audit_logger = SimpleAuditLog()
    audit_logger.log_event("system", "startup", "Application started.")
    audit_logger.log_event("user1", "login", "User logged in successfully.")
    print("\nRecent Logs:")
    for entry in audit_logger.get_logs(5):
        print(entry)

    placeholder_logger = PlaceholderAuditLog()
    placeholder_logger.log_event("user2", "action", "This action won't be logged.")
    print("\nPlaceholder Logs:")
    print(placeholder_logger.get_logs())
