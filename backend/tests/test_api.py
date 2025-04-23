# backend/tests/test_api.py
import unittest
import json
import os
from unittest.mock import patch, MagicMock
from flask import session

# Assuming your Flask app instance is named 'app' in 'backend.app'
# Adjust the import path if your structure is different
try:
    from backend.app import app, user_manager, family_tree
    from backend.src.user import User, UserRole # Import UserRole if needed
    # Import other necessary components if used directly in tests
except ImportError as e:
    print(f"Error importing Flask app or components: {e}")
    # Define dummy app if import fails to allow test discovery
    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-for-testing'
    app.config['TESTING'] = True
    user_manager = MagicMock()
    family_tree = MagicMock()


class TestAPI(unittest.TestCase):

    def setUp(self):
        """Set up test client and configure app for testing."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing forms if any
        app.config['SECRET_KEY'] = 'test-secret-for-api-tests' # Consistent secret key
        # Use a separate, temporary data store for tests if possible
        # For now, we rely on mocking or careful cleanup
        self.app = app.test_client()
        self.user_manager = user_manager # Use the imported instance
        self.family_tree = family_tree   # Use the imported instance

        # Reset mocks or clear data before each test if necessary
        # Example: If using in-memory dicts in components, clear them
        if hasattr(self.user_manager, 'users'): self.user_manager.users.clear()
        if hasattr(self.family_tree, 'people'): self.family_tree.people.clear()
        if hasattr(self.family_tree, 'relationships'): self.family_tree.relationships.clear()

        # Mock dependencies like email sending if needed
        self.send_email_patcher = patch('backend.src.user_management.send_email', return_value=True)
        self.mock_send_email = self.send_email_patcher.start()

        # Add initial users for testing roles
        self.setup_initial_users()

    def tearDown(self):
        """Clean up after tests."""
        # Stop patchers
        self.send_email_patcher.stop()
        # Clear session data
        with self.app as client:
            with client.session_transaction() as sess:
                sess.clear()
        # Clear data stores if necessary
        if hasattr(self.user_manager, 'users'): self.user_manager.users.clear()
        if hasattr(self.family_tree, 'people'): self.family_tree.people.clear()
        if hasattr(self.family_tree, 'relationships'): self.family_tree.relationships.clear()
        # You might need to mock _save_users/_save_tree to prevent writing empty files


    def setup_initial_users(self):
        """Helper to create standard and admin users for tests."""
        # Use the actual registration method if possible, otherwise mock add
        self.basic_user_pw = "password123"
        self.admin_user_pw = "adminpass"
        self.basic_user = self.user_manager.register_user("testuser", self.basic_user_pw, role="basic")
        self.admin_user = self.user_manager.register_user("adminuser", self.admin_user_pw, role="admin")
        if not self.basic_user or not self.admin_user:
             self.fail("Failed to set up initial users for testing.")


    def login(self, username, password):
        """Helper function to log in a user via the API."""
        return self.app.post('/api/login',
                             data=json.dumps({'username': username, 'password': password}),
                             content_type='application/json',
                             follow_redirects=True)

    def logout(self):
        """Helper function to log out via the API."""
        return self.app.post('/api/logout', follow_redirects=True)

    # --- Authentication Tests ---
    def test_register_success(self):
        """Test successful user registration."""
        response = self.app.post('/api/register',
                                 data=json.dumps({'username': 'newbie', 'password': 'newpassword'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Registration successful!')
        self.assertEqual(data['user']['username'], 'newbie')
        self.assertEqual(data['user']['role'], 'basic') # Default role

    def test_register_duplicate_username(self):
        """Test registration with an existing username."""
        response = self.app.post('/api/register',
                                 data=json.dumps({'username': 'testuser', 'password': 'anotherpassword'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 409) # Conflict
        data = json.loads(response.data)
        self.assertIn('already taken', data['error'])

    def test_register_missing_fields(self):
        """Test registration with missing username or password."""
        response = self.app.post('/api/register', data=json.dumps({'username': 'onlyuser'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response = self.app.post('/api/register', data=json.dumps({'password': 'onlypass'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response = self.app.post('/api/register', data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_login_success(self):
        """Test successful user login."""
        response = self.login('testuser', self.basic_user_pw)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Login successful!')
        self.assertEqual(data['user']['username'], 'testuser')
        # Check session state after login
        with self.app as client:
            self.assertEqual(session.get('username'), 'testuser')
            self.assertIsNotNone(session.get('user_id'))
            self.assertEqual(session.get('user_role'), 'basic')

    def test_login_invalid_password(self):
        """Test login with incorrect password."""
        response = self.login('testuser', 'wrongpassword')
        self.assertEqual(response.status_code, 401)

    def test_login_invalid_username(self):
        """Test login with non-existent username."""
        response = self.login('nosuchuser', self.basic_user_pw)
        self.assertEqual(response.status_code, 401)

    def test_logout(self):
        """Test user logout."""
        self.login('testuser', self.basic_user_pw) # Login first
        with self.app as client: # Check session exists
            self.assertIsNotNone(session.get('user_id'))
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Logout successful')
        with self.app as client: # Check session is cleared
            self.assertIsNone(session.get('user_id'))

    def test_session_check(self):
        """Test checking session status when logged out and logged in."""
        # Logged out
        response = self.app.get('/api/session')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['isAuthenticated'])
        self.assertIsNone(data['user'])

        # Logged in
        self.login('testuser', self.basic_user_pw)
        response = self.app.get('/api/session')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['isAuthenticated'])
        self.assertIsNotNone(data['user'])
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['role'], 'basic')

    # --- People CRUD Tests ---
    def test_people_crud_workflow(self):
        """Test full CRUD workflow for people."""
        self.login('testuser', self.basic_user_pw)

        # 1. Create Person
        person_data = {'first_name': 'Api', 'last_name': 'Tester', 'birth_date': '1999-12-31', 'gender': 'Other'}
        response = self.app.post('/api/people', data=json.dumps(person_data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        created_person = json.loads(response.data)
        person_id = created_person['person_id']
        self.assertEqual(created_person['first_name'], 'Api')
        self.assertEqual(created_person['gender'], 'Other')

        # 2. Read All People
        response = self.app.get('/api/people')
        self.assertEqual(response.status_code, 200)
        people_list = json.loads(response.data)
        self.assertEqual(len(people_list), 1)
        self.assertEqual(people_list[0]['person_id'], person_id)

        # 3. Read Specific Person
        response = self.app.get(f'/api/people/{person_id}')
        self.assertEqual(response.status_code, 200)
        read_person = json.loads(response.data)
        self.assertEqual(read_person['last_name'], 'Tester')

        # 4. Update Person
        update_data = {'last_name': 'Tested', 'notes': 'Updated via API'}
        response = self.app.put(f'/api/people/{person_id}', data=json.dumps(update_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        updated_person = json.loads(response.data)
        self.assertEqual(updated_person['last_name'], 'Tested')
        self.assertEqual(updated_person['notes'], 'Updated via API')

        # 5. Delete Person
        response = self.app.delete(f'/api/people/{person_id}')
        self.assertEqual(response.status_code, 204) # No Content

        # 6. Verify Deletion
        response = self.app.get(f'/api/people/{person_id}')
        self.assertEqual(response.status_code, 404) # Not Found

    def test_add_person_validation_fail(self):
        """Test adding a person with invalid data."""
        self.login('testuser', self.basic_user_pw)
        invalid_data = {'first_name': '', 'last_name': 'Invalid'} # Empty first name
        response = self.app.post('/api/people', data=json.dumps(invalid_data), content_type='application/json')
        self.assertEqual(response.status_code, 400)

        invalid_data = {'first_name': 'Valid', 'birth_date': 'invalid-date'} # Invalid DOB
        response = self.app.post('/api/people', data=json.dumps(invalid_data), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_edit_person_not_found(self):
        """Test editing a non-existent person."""
        self.login('testuser', self.basic_user_pw)
        update_data = {'last_name': 'NotFound'}
        response = self.app.put('/api/people/non-existent-id', data=json.dumps(update_data), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    # --- Relationship CRUD Tests ---
    def test_relationship_crud_workflow(self):
        """Test full CRUD workflow for relationships."""
        self.login('testuser', self.basic_user_pw)

        # Setup: Create two people
        p1_resp = self.app.post('/api/people', data=json.dumps({'first_name': 'Rel1'}), content_type='application/json')
        p2_resp = self.app.post('/api/people', data=json.dumps({'first_name': 'Rel2'}), content_type='application/json')
        p1_id = json.loads(p1_resp.data)['person_id']
        p2_id = json.loads(p2_resp.data)['person_id']

        # 1. Create Relationship
        rel_data = {'person1': p1_id, 'person2': p2_id, 'relationshipType': 'spouse'}
        response = self.app.post('/api/relationships', data=json.dumps(rel_data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        created_rel = json.loads(response.data)
        rel_id = created_rel['rel_id'] # Assuming backend adds rel_id
        self.assertEqual(created_rel['person1_id'], p1_id)
        self.assertEqual(created_rel['rel_type'], 'spouse')

        # 2. Read All Relationships
        response = self.app.get('/api/relationships')
        self.assertEqual(response.status_code, 200)
        rel_list = json.loads(response.data)
        self.assertEqual(len(rel_list), 1)
        self.assertEqual(rel_list[0]['rel_id'], rel_id)

        # 3. Read Specific Relationship (Requires GET /api/relationships/{id} endpoint)
        # Assuming endpoint exists:
        # response = self.app.get(f'/api/relationships/{rel_id}')
        # self.assertEqual(response.status_code, 200)
        # read_rel = json.loads(response.data)
        # self.assertEqual(read_rel['person2_id'], p2_id)

        # 4. Update Relationship
        update_data = {'relationshipType': 'sibling'} # Change type
        response = self.app.put(f'/api/relationships/{rel_id}', data=json.dumps(update_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        updated_rel = json.loads(response.data)
        self.assertEqual(updated_rel['rel_type'], 'sibling')

        # 5. Delete Relationship
        response = self.app.delete(f'/api/relationships/{rel_id}')
        self.assertEqual(response.status_code, 204)

        # 6. Verify Deletion
        response = self.app.get('/api/relationships')
        rel_list_after_delete = json.loads(response.data)
        self.assertEqual(len(rel_list_after_delete), 0)

    # --- Tree Data Test ---
    def test_get_tree_data(self):
        """Test retrieving tree data."""
        self.login('testuser', self.basic_user_pw)
        # Add some people/relationships first if needed for a non-empty tree
        response = self.app.get('/api/tree_data')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('nodes', data)
        self.assertIn('links', data)
        # Add more specific checks based on expected data structure

    # --- Password Reset Tests ---
    @patch('backend.src.user_management.UserManagement.generate_password_reset_token')
    def test_request_password_reset_success(self, mock_generate):
        """Test requesting password reset successfully."""
        # Mock token generation to avoid dependency on serializer/timing
        mock_generate.return_value = ('mock_token', None) # Return mock token, ignore expiry

        response = self.app.post('/api/request-password-reset',
                                 data=json.dumps({'email': 'testuser'}), # Use existing user email/username
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('reset link has been sent', data['message'])
        # Assert email was called
        self.mock_send_email.assert_called_once()
        # Assert token generation was called for the correct user
        user = self.user_manager.find_user_by_username('testuser')
        mock_generate.assert_called_once_with(user.user_id)

    def test_request_password_reset_user_not_found(self):
        """Test requesting reset for non-existent user."""
        response = self.app.post('/api/request-password-reset',
                                 data=json.dumps({'email': 'nosuchuser'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200) # Should still return 200 OK
        self.mock_send_email.assert_not_called() # Email should not be sent

    @patch('backend.src.user_management.UserManagement.validate_password_reset_token')
    def test_reset_password_success(self, mock_validate):
        """Test resetting password with a valid token."""
        # Mock token validation to return the user ID
        user = self.user_manager.find_user_by_username('testuser')
        mock_validate.return_value = user.user_id

        response = self.app.post(f'/api/reset-password/valid_token',
                                 data=json.dumps({'new_password': 'newSecurePassword'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Password reset successfully.')
        mock_validate.assert_called_once_with('valid_token')
        # Verify password actually changed (requires checking stored hash)
        updated_user = self.user_manager.find_user_by_id(user.user_id)
        self.assertTrue(updated_user.check_password('newSecurePassword')) # Assuming check_password method exists

    @patch('backend.src.user_management.UserManagement.validate_password_reset_token')
    def test_reset_password_invalid_token(self, mock_validate):
        """Test resetting password with an invalid/expired token."""
        mock_validate.return_value = None # Simulate invalid token

        response = self.app.post(f'/api/reset-password/invalid_token',
                                 data=json.dumps({'new_password': 'newSecurePassword'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400) # Bad Request
        data = json.loads(response.data)
        self.assertIn('Invalid or expired', data['message'])

    # --- Admin User Management Tests ---
    def test_admin_get_all_users_success(self):
        """Test admin getting all users."""
        self.login('adminuser', self.admin_user_pw)
        response = self.app.get('/api/users')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        # Should contain 'testuser' and 'adminuser' (check length or specific users)
        self.assertEqual(len(data), 2)
        usernames = {u['username'] for u in data}
        self.assertIn('testuser', usernames)
        self.assertIn('adminuser', usernames)
        # Ensure password hash is not included
        self.assertNotIn('password_hash_b64', data[0])

    def test_admin_get_all_users_forbidden(self):
        """Test non-admin trying to get all users."""
        self.login('testuser', self.basic_user_pw) # Login as basic user
        response = self.app.get('/api/users')
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_admin_delete_user_success(self):
        """Test admin deleting another user."""
        self.login('adminuser', self.admin_user_pw)
        user_to_delete = self.user_manager.find_user_by_username('testuser')
        response = self.app.delete(f'/api/users/{user_to_delete.user_id}')
        self.assertEqual(response.status_code, 204)
        # Verify user is deleted
        self.assertIsNone(self.user_manager.find_user_by_id(user_to_delete.user_id))

    def test_admin_delete_self_fail(self):
        """Test admin trying to delete themselves."""
        self.login('adminuser', self.admin_user_pw)
        admin_user_obj = self.user_manager.find_user_by_username('adminuser')
        response = self.app.delete(f'/api/users/{admin_user_obj.user_id}')
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_admin_delete_user_forbidden(self):
        """Test non-admin trying to delete a user."""
        self.login('testuser', self.basic_user_pw)
        user_to_delete = self.user_manager.find_user_by_username('adminuser') # Try deleting admin
        response = self.app.delete(f'/api/users/{user_to_delete.user_id}')
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_admin_set_user_role_success(self):
        """Test admin changing another user's role."""
        self.login('adminuser', self.admin_user_pw)
        user_to_modify = self.user_manager.find_user_by_username('testuser')
        response = self.app.put(f'/api/users/{user_to_modify.user_id}/role',
                                data=json.dumps({'role': 'admin'}),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['role'], 'admin')
        # Verify role change in user manager
        updated_user = self.user_manager.find_user_by_id(user_to_modify.user_id)
        self.assertEqual(updated_user.role, 'admin')

    def test_admin_set_user_role_invalid_role(self):
        """Test admin setting an invalid role."""
        self.login('adminuser', self.admin_user_pw)
        user_to_modify = self.user_manager.find_user_by_username('testuser')
        response = self.app.put(f'/api/users/{user_to_modify.user_id}/role',
                                data=json.dumps({'role': 'superadmin'}), # Invalid role
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_admin_set_user_role_forbidden(self):
        """Test non-admin trying to set a role."""
        self.login('testuser', self.basic_user_pw)
        user_to_modify = self.user_manager.find_user_by_username('adminuser')
        response = self.app.put(f'/api/users/{user_to_modify.user_id}/role',
                                data=json.dumps({'role': 'basic'}),
                                content_type='application/json')
        self.assertEqual(response.status_code, 403) # Forbidden


if __name__ == '__main__':
    unittest.main()
