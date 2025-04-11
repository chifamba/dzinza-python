from datetime import datetime
from dateutil import parser

class AuditLog:
    def __init__(self):
        self.log_entries = []

    def log_event(self, user_id, event_type, description):
        timestamp = datetime.now()
        log_entry = {
            "timestamp": timestamp,
            "user_id": user_id,
            "event_type": event_type,
            "description": description,
        }
        self.log_entries.append(log_entry)

    def get_log_entries(self, user_id=None, event_type=None, start_date=None, end_date=None):
        filtered_logs = []
        try:
            if start_date:
                start_date = parser.parse(start_date)
            if end_date:
                end_date = parser.parse(end_date)
        except ValueError:
            raise ValueError("Invalid date format. Please use a format like 'YYYY-MM-DD' or similar.")

        for entry in self.log_entries:
            if user_id is not None and entry["user_id"] != user_id:
                continue
            if event_type is not None and entry["event_type"] != event_type:
                continue
            if start_date is not None and entry["timestamp"] < start_date:
                continue
            if end_date is not None and entry["timestamp"] > end_date:
                continue
            filtered_logs.append(entry)
        return filtered_logs
    
    def clear_log(self):
        self.log_entries = []