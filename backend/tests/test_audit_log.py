diff
--- a/backend/tests/test_audit_log.py
+++ b/backend/tests/test_audit_log.py
@@ -6,7 +6,7 @@
 
 
 try:
-    from src.audit_log import log_event, AUDIT_LOG_FILE
+    from ..src.audit_log import log_event, AUDIT_LOG_FILE
 except ImportError as e:
     print(f"Error importing src.audit_log: {e}")
     # Define dummy function if import fails
@@ -21,7 +21,7 @@
     Uses mocking to avoid actual file system operations.
     """
 
-    @patch('src.audit_log.datetime') # Mock datetime within the audit_log module
+    @patch('..src.audit_log.datetime') # Mock datetime within the audit_log module
     def test_log_event_success(self, mock_datetime):
         """
         Test that log_event writes the correct format to the log file.
@@ -60,7 +60,7 @@
             handle.write.assert_called_once_with(expected_log_entry)
 
     @patch('src.audit_log.datetime') # Mock datetime within the audit_log module
-    def test_log_event_no_details(self, mock_datetime):
+    def test_log_event_no_details(self, mock_datetime): # Mock datetime within the audit_log module
         """
         Test log_event when no details are provided.
         """