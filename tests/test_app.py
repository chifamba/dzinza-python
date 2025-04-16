# tests/test_app.py
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root) # Add project root for app import
sys.path.insert(0, src_path)

# Import the Flask app instance
# Ensure app.py can be imported and doesn't run the server automatically
# Use a pattern like if __name__ == '__main__': app.run() in app.py
try:
    from app import app, user_management, family_tree # Import necessary components
    from user import User, UserRole
except ImportError as e:
    print(f"Error importing Flask app or components: {e}")
    # Define dummy app if import fails to allow test discovery
    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TESTING'] = True
    user_management = MagicMock()
    family_tree = MagicMock()

# Set TESTING config
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for simpler testing
app.config['SECRET_KEY'] = 'test-secret-for-testing' # Needed for session


class TestAppRoutes(unittest.TestCase):
    """Test cases for the Flask application routes."""

    def setUp(self):
        """Set up the test client and mock dependencies for each test."""
        self.client = app.test_client()

        # --- Mock Core Components ---
        # It's often better to mock the data layer directly if possible
        # Patching the instances imported into app.py
        self.user_mgmt_patcher = patch('app.user_management', spec=True)
        self.family_tree_patcher = patch('app.family_tree', spec=True)
        self.mock_user_mgmt = self.user_mgmt_patcher.start()
        self.mock_family_tree = self.family_tree_patcher.start()

        # --- Mock Specific Methods ---
        # User Management Mocks
        self.mock_user_mgmt.validate_user.return_value = None # Default: validation fails
        self.mock_user_mgmt.get_user.return_value = None
        self.mock_user_mgmt.add_user.return_value = True # Default: adding succeeds
        self.mock_user_mgmt.delete_user.return_value = True # Default: deletion succeeds
        self.mock_user_mgmt.get_all_users.return_value = [] # Default: no users

        # Family Tree Mocks
        self.mock_family_tree.get_person.return_value = None
        self.mock_family_tree.get_relationship.return_value = None
        self.mock_family_tree.add_person.return_value = None # Methods might not return values
        self.mock_family_tree.remove_person.return_value = None
        self.mock_family_tree.add_relationship.return_value = None
        self.mock_family_tree.remove_relationship.return_value = None
        self.mock_family_tree.get_all_people.return_value = [] # Assuming this method exists
        self.mock_family_tree.search_person.return_value = [] # Assuming this method exists

        # --- Mock User Objects (for login simulation) ---
        self.test_user = User(username='testuser', password_hash='fakehash', role=UserRole.USER)
        self.test_user.id = 'testuser' # Flask-Login uses get_id() which defaults to username
        self.test_admin = User(username='admin', password_hash='fakehash_admin', role=UserRole.ADMIN)
        self.test_admin.id = 'admin'

    def tearDown(self):
        """Stop patchers."""
        self.user_mgmt_patcher.stop()
        self.family_tree_patcher.stop()
        # Clear session context if needed (though test_client usually handles this)
        with self.client:
             with self.client.session_transaction() as sess:
                 sess.clear()


    # --- Helper Methods ---
    def login(self, username="testuser", password="password", user_obj=None):
        """Helper method to simulate login."""
        if user_obj is None:
            user_obj = self.test_user
        # Mock validate_user to succeed for this login attempt
        self.mock_user_mgmt.validate_user.return_value = user_obj
        # Mock get_user for flask_login user_loader
        self.mock_user_mgmt.get_user.return_value = user_obj

        response = self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)
        return response

    def logout(self):
        """Helper method to simulate logout."""
        return self.client.get('/logout', follow_redirects=True)

    # --- Test Cases ---

    def test_index_route_get(self):
        """Test the index route (GET)."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome', response.data) # Check for expected content

    def test_login_route_get(self):
        """Test the login route (GET)."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_login_success_post(self):
        """Test successful login (POST)."""
        response = self.login(user_obj=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Logout', response.data) # Should see logout link after login
        self.assertIn(b'Welcome testuser', response.data) # Check welcome message
        # Check that validate_user was called
        self.mock_user_mgmt.validate_user.assert_called_once_with('testuser', 'password')

    def test_login_failure_post(self):
        """Test failed login (POST)."""
        # Ensure validate_user returns None (default setUp behavior)
        self.mock_user_mgmt.validate_user.return_value = None
        response = self.client.post('/login', data=dict(
            username='testuser',
            password='wrongpassword'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200) # Still 200 because it re-renders login page
        self.assertIn(b'Login', response.data) # Should still be on login page
        self.assertIn(b'Invalid username or password', response.data) # Check flash message
        self.mock_user_mgmt.validate_user.assert_called_once_with('testuser', 'wrongpassword')

    def test_logout_route(self):
        """Test the logout route."""
        self.login() # Need to be logged in first
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data) # Should see login link again
        self.assertNotIn(b'Logout', response.data)

    def test_add_person_get_requires_login(self):
        """Test accessing add_person (GET) requires login."""
        response = self.client.get('/add_person', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data) # Should be redirected to login
        self.assertIn(b'Please log in to access this page', response.data) # Flash message

    def test_add_person_get_logged_in(self):
        """Test accessing add_person (GET) when logged in."""
        self.login()
        response = self.client.get('/add_person')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Add New Person', response.data)

    def test_add_person_post_success(self):
        """Test successfully adding a person (POST)."""
        self.login()
        person_data = {'name': 'New Person', 'birth_date': '2000-01-01', 'death_date': '', 'notes': 'Test note'}
        response = self.client.post('/add_person', data=person_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Person added successfully!', response.data) # Check flash message
        # Check that family_tree.add_person was called (argument checking is tricky with object creation)
        self.mock_family_tree.add_person.assert_called_once()
        # Check the argument passed to add_person
        added_person_arg = self.mock_family_tree.add_person.call_args[0][0]
        self.assertEqual(added_person_arg.name, 'New Person')
        self.assertEqual(added_person_arg.birth_date, '2000-01-01')

    def test_add_person_post_validation_error(self):
        """Test adding a person (POST) with missing data (form validation)."""
        self.login()
        person_data = {'name': '', 'birth_date': '2000-01-01'} # Missing name
        response = self.client.post('/add_person', data=person_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertIn(b'Add New Person', response.data)
        self.assertIn(b'This field is required.', response.data) # Check WTForms error message
        self.mock_family_tree.add_person.assert_not_called() # Should not be called if form invalid


    # --- Admin Route Tests ---
    def test_admin_users_get_requires_admin(self):
        """Test accessing admin users page requires admin role."""
        # Try as logged-out user
        response_logout = self.client.get('/admin/users', follow_redirects=True)
        self.assertIn(b'Login', response_logout.data) # Redirected to login

        # Try as regular user
        self.login(user_obj=self.test_user)
        response_user = self.client.get('/admin/users', follow_redirects=True)
        self.assertEqual(response_user.status_code, 403) # Forbidden
        self.assertIn(b'Forbidden', response_user.data)
        self.logout() # Clean up session

        # Try as admin user
        self.login(username="admin", password="adminpass", user_obj=self.test_admin)
        self.mock_user_mgmt.get_all_users.return_value = [self.test_user, self.test_admin] # Mock data for page
        response_admin = self.client.get('/admin/users')
        self.assertEqual(response_admin.status_code, 200)
        self.assertIn(b'User Management', response_admin.data)
        self.assertIn(b'testuser', response_admin.data) # Check user data is displayed
        self.assertIn(b'admin', response_admin.data)

    def test_admin_delete_user_success(self):
        """Test admin successfully deleting a user."""
        self.login(username="admin", password="adminpass", user_obj=self.test_admin)
        target_username = 'user_to_delete'
        response = self.client.post(f'/admin/delete_user/{target_username}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'User Management', response.data) # Redirect back to admin page
        self.assertIn(b'User deleted successfully', response.data) # Flash message
        self.mock_user_mgmt.delete_user.assert_called_once_with(target_username)

    def test_admin_delete_user_requires_admin(self):
        """Test deleting a user requires admin role."""
        self.login(user_obj=self.test_user) # Login as regular user
        target_username = 'user_to_delete'
        response = self.client.post(f'/admin/delete_user/{target_username}', follow_redirects=True)
        self.assertEqual(response.status_code, 403) # Forbidden
        self.mock_user_mgmt.delete_user.assert_not_called()

    # --- Error Handling ---
    def test_404_not_found(self):
        """Test accessing a non-existent route."""
        response = self.client.get('/nonexistent-route')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Page Not Found', response.data) # Check content of 404 page

    # Add more tests for edit_person (GET/POST), add/edit_relationship (GET/POST), search (GET/POST) etc.
    # Remember to test both success cases and validation/error cases.
    # Test authentication (@login_required) and authorization (@admin_required) thoroughly.


if __name__ == '__main__':
    unittest.main()
