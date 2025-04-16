# tests/test_app_integration.py

import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile # To create temporary files for testing

# Import the Flask app instance and necessary classes
from app import app as flask_app, user_manager as real_user_manager, family_tree as real_family_tree
from src.user import User, hash_password
from src.user_management import UserManager, VALID_ROLES
from src.audit_log import AuditLog # For type hinting if needed
from src.family_tree import FamilyTree # Import FamilyTree
from src.person import Person # Import Person
from src.relationship import Relationship # Import Relationship


# Use a known, fixed secret key for testing sessions
TEST_SECRET_KEY = 'test-secret-key-for-flask-sessions'

# --- Helper Function for Logging In ---
def login(client, username, password):
    """Helper function to log in a user via the test client."""
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

def logout(client):
    """Helper function to log out a user via the test client."""
    return client.get('/logout', follow_redirects=True)


class TestAppIntegration(unittest.TestCase):
    """Integration tests for Flask app routes."""

    @classmethod
    def setUpClass(cls):
        """Set up the Flask test client and mock dependencies."""
        flask_app.config['TESTING'] = True
        flask_app.config['SECRET_KEY'] = TEST_SECRET_KEY
        flask_app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for easier testing

        # Mock UserManager instance used by the app
        cls.mock_user_manager = MagicMock(spec=UserManager)
        cls.user_patcher = patch('app.user_manager', cls.mock_user_manager)
        cls.user_patcher.start()

        # Mock Audit Log function used by the app
        cls.audit_patcher = patch('app.log_audit')
        cls.mock_log_audit = cls.audit_patcher.start()

        # Mock FamilyTree instance
        cls.mock_family_tree = MagicMock(spec=FamilyTree)
        cls.tree_patcher = patch('app.family_tree', cls.mock_family_tree)
        cls.tree_patcher.start()

        cls.client = flask_app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Stop the patchers."""
        cls.user_patcher.stop()
        cls.audit_patcher.stop()
        cls.tree_patcher.stop()

    def setUp(self):
        """Reset mocks and set up test users/data before each test."""
        self.mock_user_manager.reset_mock()
        self.mock_log_audit.reset_mock()
        self.mock_family_tree.reset_mock()

        # --- Test Users Setup ---
        self.admin_user = User("admin_id", "admin_user", hash_password("admin_pass"), role="admin")
        self.basic_user = User("basic_id", "basic_user", hash_password("basic_pass"), role="basic")
        self.other_user = User("other_id", "other_user", hash_password("other_pass"), role="basic")

        # Common mock configurations for UserManager
        self.mock_user_manager.find_user_by_id.side_effect = lambda user_id: {
            "admin_id": self.admin_user,
            "basic_id": self.basic_user,
            "other_id": self.other_user,
        }.get(user_id)
        self.mock_user_manager.find_user_by_username.side_effect = lambda username: {
            "admin_user": self.admin_user,
            "basic_user": self.basic_user,
            "other_user": self.other_user,
        }.get(username)
        self.mock_user_manager.login_user.side_effect = lambda username, password: {
            ("admin_user", "admin_pass"): self.admin_user,
            ("basic_user", "basic_pass"): self.basic_user,
            ("other_user", "other_pass"): self.other_user,
        }.get((username, password))
        self.mock_user_manager.users = {
            "admin_id": self.admin_user,
            "basic_id": self.basic_user,
            "other_id": self.other_user,
        }
        self.mock_user_manager.users.values.return_value = [self.admin_user, self.basic_user, self.other_user]

        # --- Test Family Tree Data Setup ---
        self.person1 = Person("basic_user", "Alice", "Smith", person_id="p1", date_of_birth="1990-01-15")
        self.person2 = Person("basic_user", "Bob", "Jones", person_id="p2", date_of_birth="1988-05-20")
        self.relationship1 = Relationship("p1", "p2", "spouse", relationship_id="r1")

        # Mock FamilyTree methods needed for tests
        self.mock_family_tree.get_people_summary.return_value = [
            {'id': 'p1', 'display_name': 'Alice Smith'},
            {'id': 'p2', 'display_name': 'Bob Jones'}
        ]
        self.mock_family_tree.get_relationships_summary.return_value = [
            {'id': 'r1', 'person1_name': 'Alice Smith', 'person2_name': 'Bob Jones', 'type': 'spouse'}
        ]
        self.mock_family_tree.find_person.side_effect = lambda person_id: {
            "p1": self.person1,
            "p2": self.person2,
        }.get(person_id)
        self.mock_family_tree.add_person.return_value = self.person1 # Mock successful add
        self.mock_family_tree.add_relationship.return_value = self.relationship1 # Mock successful add
        self.mock_family_tree._is_valid_date.return_value = True # Assume date validation passes by default


    def tearDown(self):
        """Log out after each test if a user might be logged in."""
        with self.client.session_transaction() as sess:
            if 'user_id' in sess:
                 logout(self.client)

    # --- Registration Form Error Tests ---
    def test_register_missing_username(self):
        response = self.client.post('/register', data={'username': '', 'password': 'pass'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Username is required.', response.data)
        self.assertIn(b'Please correct the errors below.', response.data) # Check flash message
        self.assertIn(b'value="pass"' not in response.data) # Password should NOT be repopulated
        self.mock_user_manager.register_user.assert_not_called()

    def test_register_missing_password(self):
        response = self.client.post('/register', data={'username': 'testuser', 'password': ''}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password is required.', response.data)
        self.assertIn(b'value="testuser"', response.data) # Username should be repopulated
        self.mock_user_manager.register_user.assert_not_called()

    def test_register_username_taken(self):
        # Mock find_user_by_username to indicate user exists
        self.mock_user_manager.find_user_by_username.return_value = self.basic_user
        response = self.client.post('/register', data={'username': 'basic_user', 'password': 'newpass'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Username 'basic_user' is already taken.', response.data)
        self.assertIn(b'value="basic_user"', response.data)
        self.mock_user_manager.register_user.assert_not_called()
        # Reset mock for subsequent tests
        self.mock_user_manager.find_user_by_username.side_effect = lambda username: {"admin_user": self.admin_user, "basic_user": self.basic_user, "other_user": self.other_user,}.get(username)

    # --- Login Form Error Tests ---
    def test_login_missing_username(self):
        response = self.client.post('/login', data={'username': '', 'password': 'pass'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Username is required.', response.data)
        self.assertIn(b'Please enter both username and password.', response.data) # Flash message
        self.mock_user_manager.login_user.assert_not_called()

    def test_login_missing_password(self):
        response = self.client.post('/login', data={'username': 'testuser', 'password': ''}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password is required.', response.data)
        self.assertIn(b'value="testuser"', response.data) # Username should be repopulated
        self.mock_user_manager.login_user.assert_not_called()

    def test_login_invalid_credentials(self):
        self.mock_user_manager.login_user.return_value = None # Mock failed login
        response = self.client.post('/login', data={'username': 'basic_user', 'password': 'wrongpass'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password.', response.data) # Check error message
        self.assertIn(b'value="basic_user"', response.data) # Username should be repopulated
        self.mock_user_manager.login_user.assert_called_once_with('basic_user', 'wrongpass')

    # --- Add Person Form Error Tests ---
    def test_add_person_missing_first_name(self):
        login(self.client, "basic_user", "basic_pass")
        response = self.client.post('/add_person', data={'first_name': '', 'last_name': 'Test'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Check error message is displayed *near* the first_name input (depends on template structure)
        self.assertIn(b'First name is required.', response.data)
        # Check other valid data is repopulated
        self.assertIn(b'value="Test"', response.data)
        self.assertIn(b'Please correct the errors in the Add Person form.', response.data) # Flash
        self.mock_family_tree.add_person.assert_not_called()

    def test_add_person_invalid_dob_format(self):
        login(self.client, "basic_user", "basic_pass")
        self.mock_family_tree._is_valid_date.side_effect = lambda d: d != "invalid-date"
        response = self.client.post('/add_person', data={'first_name': 'Test', 'dob': 'invalid-date'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid date format (YYYY-MM-DD).', response.data) # Check error message
        self.assertIn(b'value="Test"', response.data) # Repopulate first name
        self.assertIn(b'value="invalid-date"', response.data) # Repopulate invalid date
        self.mock_family_tree.add_person.assert_not_called()
        self.mock_family_tree._is_valid_date.assert_called_with('invalid-date')
        # Reset mock side effect
        self.mock_family_tree._is_valid_date.side_effect = None; self.mock_family_tree._is_valid_date.return_value = True

    def test_add_person_dod_before_dob(self):
        login(self.client, "basic_user", "basic_pass")
        response = self.client.post('/add_person', data={'first_name': 'Test', 'dob': '2000-01-01', 'dod': '1999-12-31'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Date of Death cannot be before Date of Birth.', response.data)
        self.assertIn(b'value="Test"', response.data)
        self.assertIn(b'value="2000-01-01"', response.data)
        self.assertIn(b'value="1999-12-31"', response.data)
        self.mock_family_tree.add_person.assert_not_called()


    # --- Add Relationship Form Error Tests ---
    def test_add_relationship_missing_person1(self):
        login(self.client, "basic_user", "basic_pass")
        response = self.client.post('/add_relationship', data={'person1_id': '', 'person2_id': 'p2', 'relationship_type': 'spouse'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Person 1 must be selected.', response.data)
        self.assertIn(b'option value="p2" selected', response.data) # Check person 2 repopulated
        self.assertIn(b'option value="spouse" selected', response.data) # Check type repopulated
        self.assertIn(b'Please correct the errors in the Add Relationship form.', response.data) # Flash
        self.mock_family_tree.add_relationship.assert_not_called()

    def test_add_relationship_same_person(self):
        login(self.client, "basic_user", "basic_pass")
        response = self.client.post('/add_relationship', data={'person1_id': 'p1', 'person2_id': 'p1', 'relationship_type': 'sibling'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cannot add relationship to the same person.', response.data)
        self.assertIn(b'option value="p1" selected', response.data) # Check person 1 repopulated
        self.mock_family_tree.add_relationship.assert_not_called()

    def test_add_relationship_already_exists(self):
        login(self.client, "basic_user", "basic_pass")
        # Mock find_relationship to return the existing one
        self.mock_family_tree.find_relationship.return_value = self.relationship1
        response = self.client.post('/add_relationship', data={'person1_id': 'p1', 'person2_id': 'p2', 'relationship_type': 'spouse'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'A 'spouse' relationship already exists between these two people.', response.data)
        self.mock_family_tree.find_relationship.assert_called_once_with('p1', 'p2', 'spouse')
        self.mock_family_tree.add_relationship.assert_not_called()
        # Reset mock
        self.mock_family_tree.find_relationship.return_value = None

    # --- Admin UI Tests ---
    # (Keep existing tests from previous steps)
    def test_set_role_success_by_admin(self):
        login(self.client, "admin_user", "admin_pass")
        self.mock_user_manager.set_user_role.return_value = True
        target_user_id = "basic_id"; new_role = "trusted"
        response = self.client.post(f'/admin/set_role/{target_user_id}', data={'role': new_role}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Role for user 'basic_user' successfully updated', response.data)
        self.mock_user_manager.set_user_role.assert_called_once_with(target_user_id, new_role, actor_username="admin_user")

    # ... (other admin tests remain the same) ...
    def test_set_role_invalid_role_by_admin(self):
        login(self.client, "admin_user", "admin_pass")
        target_user_id = "basic_id"; invalid_role = "superhero"
        response = self.client.post(f'/admin/set_role/{target_user_id}', data={'role': invalid_role}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid role specified', response.data)
        self.mock_user_manager.set_user_role.assert_not_called()

    def test_set_role_user_not_found_by_admin(self):
        login(self.client, "admin_user", "admin_pass")
        self.mock_user_manager.find_user_by_id.return_value = None
        target_user_id = "ghost_id"
        response = self.client.post(f'/admin/set_role/{target_user_id}', data={'role': 'basic'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'User with ID {target_user_id} not found.'.encode('utf-8'), response.data)
        self.mock_user_manager.set_user_role.assert_not_called()

    def test_set_role_by_non_admin(self):
        login(self.client, "basic_user", "basic_pass")
        response = self.client.post('/admin/set_role/other_id', data={'role': 'admin'})
        self.assertEqual(response.status_code, 403)
        self.mock_user_manager.set_user_role.assert_not_called()

    def test_set_role_not_logged_in(self):
        response = self.client.post('/admin/set_role/basic_id', data={'role': 'admin'}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith('/login'))
        self.mock_user_manager.set_user_role.assert_not_called()

    def test_delete_user_success_by_admin(self):
        login(self.client, "admin_user", "admin_pass")
        self.mock_user_manager.delete_user.return_value = True
        target_user_id = "basic_id"
        response = self.client.post(f'/admin/delete_user/{target_user_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'User 'basic_user' deleted successfully.', response.data)
        self.mock_user_manager.delete_user.assert_called_once_with(target_user_id, actor_username="admin_user")

    def test_delete_user_self_by_admin(self):
        login(self.client, "admin_user", "admin_pass")
        target_user_id = "admin_id"
        response = self.client.post(f'/admin/delete_user/{target_user_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Administrators cannot delete their own account.', response.data)
        self.mock_user_manager.delete_user.assert_not_called()

    def test_delete_user_not_found_by_admin(self):
        login(self.client, "admin_user", "admin_pass")
        self.mock_user_manager.find_user_by_id.return_value = None
        target_user_id = "ghost_id"
        response = self.client.post(f'/admin/delete_user/{target_user_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'User with ID {target_user_id} not found.'.encode('utf-8'), response.data)
        self.mock_user_manager.delete_user.assert_not_called()

    def test_delete_user_by_non_admin(self):
        login(self.client, "basic_user", "basic_pass")
        response = self.client.post('/admin/delete_user/other_id')
        self.assertEqual(response.status_code, 403)
        self.mock_user_manager.delete_user.assert_not_called()

    def test_delete_user_not_logged_in(self):
        response = self.client.post('/admin/delete_user/basic_id', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith('/login'))
        self.mock_user_manager.delete_user.assert_not_called()

    # --- Password Reset Flow Tests ---
    # (Keep existing tests from previous steps)
    def test_request_password_reset_success(self):
        test_token = "mock_reset_token_123"
        self.mock_user_manager.generate_reset_token.return_value = test_token
        response = self.client.post('/request_password_reset', data={'username': 'basic_user'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password reset requested for 'basic_user'', response.data)
        self.mock_user_manager.generate_reset_token.assert_called_once_with('basic_user')
        self.mock_log_audit.assert_called_with(flask_app.config['AUDIT_LOG_FILE'], 'basic_user', 'request_password_reset', 'success (token generated)')

    # ... (other password reset tests remain the same) ...
    def test_request_password_reset_user_not_found(self):
        self.mock_user_manager.generate_reset_token.return_value = None
        response = self.client.post('/request_password_reset', data={'username': 'ghost_user'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'If a user with that username exists', response.data)
        self.mock_user_manager.generate_reset_token.assert_called_once_with('ghost_user')
        self.mock_log_audit.assert_called_with(flask_app.config['AUDIT_LOG_FILE'], 'ghost_user', 'request_password_reset', 'failure or user not found')

    def test_request_password_reset_no_username(self):
        response = self.client.post('/request_password_reset', data={'username': ''}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter your username.', response.data)
        self.mock_user_manager.generate_reset_token.assert_not_called()

    def test_reset_password_view_valid_token(self):
        test_token = "valid_token_abc"
        self.mock_user_manager.verify_reset_token.return_value = self.basic_user
        response = self.client.get(f'/reset_password/{test_token}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reset Your Password', response.data)
        self.assertIn(f'value="{test_token}"'.encode('utf-8'), response.data)
        self.mock_user_manager.verify_reset_token.assert_called_once_with(test_token)
        self.mock_log_audit.assert_called_with(flask_app.config['AUDIT_LOG_FILE'], f'user: {self.basic_user.username}', 'reset_password_view', 'success - token valid')

    def test_reset_password_view_invalid_token(self):
        test_token = "invalid_token_xyz"
        self.mock_user_manager.verify_reset_token.return_value = None
        response = self.client.get(f'/reset_password/{test_token}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid or expired password reset token.', response.data)
        self.assertIn(b'Request Password Reset', response.data)
        self.mock_user_manager.verify_reset_token.assert_called_once_with(test_token)
        self.mock_log_audit.assert_called_with(flask_app.config['AUDIT_LOG_FILE'], f'token: {test_token[:8]}...', 'reset_password_view', 'failure - invalid/expired token')

    def test_reset_password_submit_success(self):
        test_token = "valid_token_for_submit"
        new_password = "newSecurePassword123"
        self.mock_user_manager.verify_reset_token.return_value = self.basic_user
        self.mock_user_manager.reset_password.return_value = True
        response = self.client.post(f'/reset_password/{test_token}', data=dict(
            password=new_password,
            confirm_password=new_password
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your password has been reset successfully', response.data)
        self.assertIn(b'Please Log In', response.data)
        self.mock_user_manager.verify_reset_token.assert_called_once_with(test_token)
        self.mock_user_manager.reset_password.assert_called_once_with(test_token, new_password)

    def test_reset_password_submit_mismatch(self):
        test_token = "valid_token_for_mismatch"
        self.mock_user_manager.verify_reset_token.return_value = self.basic_user
        response = self.client.post(f'/reset_password/{test_token}', data=dict(
            password="newPass1",
            confirm_password="newPass2"
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reset Your Password', response.data)
        self.assertIn(b'Passwords do not match.', response.data)
        self.mock_user_manager.reset_password.assert_not_called()

    def test_reset_password_submit_invalid_token(self):
        test_token = "expired_token_on_submit"
        new_password = "newSecurePassword123"
        self.mock_user_manager.verify_reset_token.return_value = self.basic_user # GET ok
        response_get = self.client.get(f'/reset_password/{test_token}')
        self.assertEqual(response_get.status_code, 200)
        self.mock_user_manager.verify_reset_token.return_value = None # Fails on POST
        self.mock_user_manager.reset_password.return_value = False
        response_post = self.client.post(f'/reset_password/{test_token}', data=dict(
            password=new_password,
            confirm_password=new_password
        ), follow_redirects=True)
        self.assertEqual(response_post.status_code, 200)
        self.assertIn(b'Invalid or expired password reset token.', response_post.data)
        self.assertIn(b'Request Password Reset', response_post.data)
        self.mock_user_manager.verify_reset_token.assert_called_with(test_token)
        self.mock_user_manager.reset_password.assert_called_once_with(test_token, new_password)


if __name__ == '__main__':
    unittest.main()
