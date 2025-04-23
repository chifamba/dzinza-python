diff
--- a/backend/tests/test_encryption.py
+++ b/backend/tests/test_encryption.py
@@ -1,6 +1,6 @@
 import unittest
 
-from src.encryption import encrypt_password, verify_password
+from ..src.encryption import encrypt_password, verify_password
 
 
 class TestEncryption(unittest.TestCase):