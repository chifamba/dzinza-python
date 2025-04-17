diff
--- a/backend/tests/test_app.py
+++ b/backend/tests/test_app.py
@@ -1,30 +1,23 @@
 import unittest
 import sys
 import os
-from unittest.mock import patch, MagicMock
+from unittest.mock import patch, MagicMock, DEFAULT
 
-# Add the project root directory to the Python path
-project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
-src_path = os.path.join(project_root, 'src')
-sys.path.insert(0, project_root) # Add project root for app import
-sys.path.insert(0, src_path)
+
+
 
 # Import the Flask app instance
 # Ensure app.py can be imported and does not run the server automatically
 # Use a pattern like if __name__ == '__main__': app.run() in app.py if needed
 try:
-    from ..app import app, user_management, family_tree # Import necessary components
-    from ..src.user import User, UserRole
+    from ..app import app
+    from ..src.user import User, UserRole  # Import necessary components
 except ImportError as e:
     print(f"Error importing Flask app or components: {e}")
     # Define dummy app if import fails to allow test discovery
     from flask import Flask
     app = Flask(__name__)
     app.config['SECRET_KEY'] = 'test-secret-key'
-    app.config['TESTING'] = True
-    user_management = MagicMock()
-    family_tree = MagicMock()
 
-# Set TESTING config
 app.config['SECRET_KEY'] = 'test-secret-for-testing' # Needed for session
 
 
@@ -35,12 +28,26 @@
     def setUp(self):
         """Set up the test client and mock dependencies for each test."""
         self.client = app.test_client()
-
+        app.config["TESTING"] = True
         # --- Mock Core Components ---
         # It's often better to mock the data layer directly if possible
         # Patching the instances imported into app.py
-        self.user_mgmt_patcher = patch('app.user_management', spec=True)
-        self.family_tree_patcher = patch('app.family_tree', spec=True)
+        self.user_mgmt_patcher = patch(
+            "backend.app.user_management", spec=True
+        )
+        self.family_tree_patcher = patch(
+            "backend.app.family_tree", spec=True
+        )
+        with patch.multiple(
+            "backend.app",
+            user_management=DEFAULT,
+            family_tree=DEFAULT,
+        ) as values:
+            self.mock_user_mgmt = values["user_management"]
+            self.mock_family_tree = values["family_tree"]
+        # self.user_mgmt_patcher = patch('app.user_management', spec=True)
+        # self.family_tree_patcher = patch('app.family_tree', spec=True)
+        #
         self.mock_user_mgmt = self.user_mgmt_patcher.start()
         self.mock_family_tree = self.family_tree_patcher.start()
 
@@ -67,8 +74,8 @@
         # --- Mock User Objects (for login simulation) ---
         self.test_user = User(username='testuser', password_hash='fakehash', role=UserRole.USER)
         self.test_user.id = 'testuser' # Flask-Login uses get_id() which defaults to username
-        self.test_admin = User(username='admin', password_hash='fakehash_admin', role=UserRole.ADMIN)
-        self.test_admin.id = 'admin'
+        self.test_admin = User(username="admin", password_hash="fakehash_admin", role=UserRole.ADMIN)
+        self.test_admin.id = "admin"
 
     def tearDown(self):
         """Stop patchers."""
@@ -113,7 +120,7 @@
         response = self.login(user_obj=self.test_user)
         self.assertEqual(response.status_code, 200)
         self.assertIn(b'Logout', response.data) # Should see logout link after login
-        self.assertIn(b'Welcome testuser', response.data) # Check welcome message
+        self.assertIn(b'Welcome testuser', response.data)  # Check welcome message
         # Check that validate_user was called
         self.mock_user_mgmt.validate_user.assert_called_once_with('testuser', 'password')
 
@@ -197,7 +204,7 @@
         response = self.client.post(f'/admin/delete_user/{target_username}', follow_redirects=True)
         self.assertEqual(response.status_code, 200)
         self.assertIn(b'User Management', response.data) # Redirect back to admin page
-        self.assertIn(b'User deleted successfully', response.data) # Flash message
+        self.assertIn(b'User deleted successfully', response.data)  # Flash message
         self.mock_user_mgmt.delete_user.assert_called_once_with(target_username)
 
     def test_admin_delete_user_requires_admin(self):