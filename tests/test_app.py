# tests/test_app.py

import unittest
import os
from flask import Flask, session, flash # Import flask components
from unittest.mock import patch, MagicMock
import tempfile # For creating temporary directories/files
import shutil # For removing temporary directories
import json

# Import the Flask app instance and core components
# Need to ensure imports work relative to the test execution context
# Assuming tests are run from the project root
from app import app, user_manager, family_tree
from src.user import User, hash_password, VALID_ROLES

# --- Test Configuration ---
TEST_DATA_DIR = tempfile.mkdtemp()
TEST_USERS_FILE = os.path.join(TEST_DATA_DIR, 'test_users.json')
TEST_TREE_FILE = os.path.join(TEST_DATA_DIR, 'test_tree.json')
TEST_AUDIT_LOG = os.path.join(TEST_DATA_DIR, 'test_audit.log')

# --- Helper Functions ---
def create_test_user(username, password, role='basic', user_id=None):
    """Creates a User object for testing."""
    return User(
        user_id=user_id or f"test_{username}_id",
        username=username,
        password_hash=hash_password(password),
        role=role
    )

def setup_test_environment():
    """Sets up clean data files and mock dependencies for tests."""
    # Ensure the temp directory is clean
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    os.makedirs(TEST_DATA_DIR)

    # Configure app for testing
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key' # Consistent key for session tests
    app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing forms if applicable
    # Point app components to test files *before* creating client
    user_manager.users_file_path = TEST_USERS_FILE
    user_manager.audit_log_path = TEST_AUDIT_LOG
    family_tree.file_path = TEST_TREE_FILE
    family_tree.audit_log_path = TEST_AUDIT_LOG
    # Ensure components start fresh (clear in-memory data)
    user_manager.users = {}
    family_tree.people = {}
    family_tree.relationships = {}
    # Create empty files
    open(TEST_USERS_FILE, 'w').close()
    open(TEST_TREE_FILE, 'w').close()
    open(TEST_AUDIT_LOG, 'w').close()
    # Load from empty files (optional, depends on initialization logic)
    # user_manager._load_users()
    # family_tree.load_tree()

def cleanup_test_environment():
    """Removes temporary data files."""
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)

# --- Base Test Case ---
class BaseAppTestCase(unittest.TestCase):
    """Base class for Flask app tests."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for the class."""
        setup_test_environment()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment once after all tests."""
        cleanup_test_environment()

    def setUp(self):
        """Set up fresh app client and test users for each test."""
        setup_test_environment() # Re-setup files to ensure isolation
        self.app = app.test_client() # Create a test client

        # Add standard test users to the user_manager directly
        self.admin_user = create_test_user("admin", "password", "admin", "admin_id_1")
        self.basic_user = create_test_user("basic", "password", "basic", "basic_id_1")
        self.other_user = create_test_user("other", "password", "basic", "other_id_1")

        user_manager.users = {
            self.admin_user.user_id: self.admin_user,
            self.basic_user.user_id: self.basic_user,
            self.other_user.user_id: self.other_user
        }
        user_manager._save_users() # Save initial test users

    def tearDown(self):
        """Clean up after each test (e.g., logout)."""
        # No specific action needed here usually, as setUp resets the environment
        pass

    def login(self, username, password):
        """Helper method to log in a user."""
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        """Helper method to log out."""
        return self.app.get('/logout', follow_redirects=True)

# --- Test Cases ---

class TestAdminUserManagement(BaseAppTestCase):
    """Tests for the admin user management UI routes."""

    def test_manage_users_page_access_admin(self):
        """Test admin can access the manage users page."""
        self.login(self.admin_user.username, "password")
        response = self.app.get('/admin/users')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Manage Users", response.data)
        self.assertIn(bytes(self.basic_user.username, 'utf-8'), response.data)
        self.assertIn(bytes(self.other_user.username, 'utf-8'), response.data)
        self.assertIn(b'name="role"', response.data) # Check role selector is present
        self.assertIn(b'action="/admin/delete_user/', response.data) # Check delete button form

    def test_manage_users_page_access_basic_user(self):
        """Test basic user cannot access the manage users page (403)."""
        self.login(self.basic_user.username, "password")
        response = self.app.get('/admin/users')
        self.assertEqual(response.status_code, 403) # Forbidden
        self.assertIn(b"Forbidden", response.data) # Check default forbidden message

    def test_manage_users_page_access_logged_out(self):
        """Test logged out user cannot access manage users page (redirects to login)."""
        response = self.app.get('/admin/users', follow_redirects=False) # Don't follow redirect
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertTrue(response.location.startswith('/login'))

    def test_set_user_role_success(self):
        """Test admin successfully sets a user's role."""
        self.login(self.admin_user.username, "password")
        target_user_id = self.basic_user.user_id
        new_role = 'trusted' # Assuming 'trusted' is a valid role
        self.assertIn(new_role, VALID_ROLES) # Ensure role is valid for test

        response = self.app.post(f'/admin/set_role/{target_user_id}', data=dict(
            role=new_role
        ), follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Role for user", response.data) # Check success flash message
        self.assertIn(b"successfully updated", response.data)
        self.assertIn(bytes(new_role, 'utf-8'), response.data)

        # Verify change in user_manager
        updated_user = user_manager.find_user_by_id(target_user_id)
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.role, new_role)

    def test_set_user_role_invalid_role(self):
        """Test setting an invalid role fails."""
        self.login(self.admin_user.username, "password")
        target_user_id = self.basic_user.user_id
        invalid_role = 'superadmin'
        self.assertNotIn(invalid_role, VALID_ROLES) # Ensure role is invalid for test

        response = self.app.post(f'/admin/set_role/{target_user_id}', data=dict(
            role=invalid_role
        ), follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid role specified", response.data) # Check error flash message

        # Verify role did not change
        original_user = user_manager.find_user_by_id(target_user_id)
        self.assertEqual(original_user.role, self.basic_user.role)

    def test_set_user_role_user_not_found(self):
        """Test setting role for a non-existent user fails."""
        self.login(self.admin_user.username, "password")
        target_user_id = "nonexistent_user_id"
        new_role = 'trusted'

        response = self.app.post(f'/admin/set_role/{target_user_id}', data=dict(
            role=new_role
        ), follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"User with ID", response.data) # Check error flash message
        self.assertIn(b"not found", response.data)

    def test_set_user_role_by_basic_user_fails(self):
        """Test basic user cannot set roles (403)."""
        self.login(self.basic_user.username, "password")
        target_user_id = self.other_user.user_id
        new_role = 'admin'

        response = self.app.post(f'/admin/set_role/{target_user_id}', data=dict(
            role=new_role
        ), follow_redirects=True)

        # The decorator should catch this before the view logic
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Forbidden", response.data)

    def test_delete_user_success(self):
        """Test admin successfully deletes another user."""
        self.login(self.admin_user.username, "password")
        target_user_id = self.other_user.user_id
        target_username = self.other_user.username
        self.assertIn(target_user_id, user_manager.users) # Ensure user exists before delete

        response = self.app.post(f'/admin/delete_user/{target_user_id}', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"User", response.data) # Check success flash message
        self.assertIn(bytes(target_username, 'utf-8'), response.data)
        self.assertIn(b"deleted successfully", response.data)

        # Verify user is deleted from user_manager
        deleted_user = user_manager.find_user_by_id(target_user_id)
        self.assertIsNone(deleted_user)
        self.assertNotIn(target_user_id, user_manager.users)

    def test_delete_user_self_fails(self):
        """Test admin cannot delete their own account."""
        self.login(self.admin_user.username, "password")
        target_user_id = self.admin_user.user_id # Attempt self-deletion
        self.assertIn(target_user_id, user_manager.users)

        response = self.app.post(f'/admin/delete_user/{target_user_id}', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Administrators cannot delete their own account", response.data) # Check error flash message

        # Verify user was NOT deleted
        self.assertIn(target_user_id, user_manager.users)

    def test_delete_user_not_found(self):
        """Test deleting a non-existent user fails."""
        self.login(self.admin_user.username, "password")
        target_user_id = "nonexistent_user_id"

        response = self.app.post(f'/admin/delete_user/{target_user_id}', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"User with ID", response.data) # Check error flash message
        self.assertIn(b"not found", response.data)

    def test_delete_user_by_basic_user_fails(self):
        """Test basic user cannot delete users (403)."""
        self.login(self.basic_user.username, "password")
        target_user_id = self.other_user.user_id

        response = self.app.post(f'/admin/delete_user/{target_user_id}', follow_redirects=True)

        # Decorator should catch this
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Forbidden", response.data)

# Add more test classes for other app features (Auth, Tree Management, etc.) later

if __name__ == '__main__':
    unittest.main()
