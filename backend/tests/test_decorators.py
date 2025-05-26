import unittest
import uuid
from flask import Flask, g, session, jsonify, request
from unittest.mock import MagicMock, patch

from decorators import require_auth, require_admin, require_tree_access
from models import User, Tree, TreeAccess, UserRole, TreePrivacySettingEnum

# Helper function to create a mock user object (already provided in previous attempt)
def create_mock_user(user_id, username, role, is_active=True):
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.username = username
    mock_user.role = role # This should be a UserRole enum member, e.g., UserRole.admin
    mock_user.is_active = is_active
    return mock_user

# Helper function to create a mock tree object (already provided)
def create_mock_tree(tree_id, name, created_by_id, privacy_setting=TreePrivacySettingEnum.PRIVATE):
    mock_tree = MagicMock(spec=Tree)
    mock_tree.id = tree_id
    mock_tree.name = name
    mock_tree.created_by = created_by_id
    mock_tree.privacy_setting = privacy_setting # This should be a TreePrivacySettingEnum member
    return mock_tree

# Helper function to create a mock tree access object (already provided)
def create_mock_tree_access(tree_id, user_id, access_level):
    mock_access = MagicMock(spec=TreeAccess)
    mock_access.tree_id = tree_id
    mock_access.user_id = user_id
    mock_access.access_level = access_level # e.g., 'view', 'edit', 'admin'
    return mock_access


class TestDecorators(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'testsecretkeyforsession'
        self.app.config['TESTING'] = True

        self.user_id_normal = uuid.uuid4()
        self.user_id_admin = uuid.uuid4()
        self.tree_owner_id = uuid.uuid4() 
        self.other_user_id = uuid.uuid4()

        # --- Route for @require_auth ---
        @self.app.route('/protected_auth_test') # Changed route name to avoid potential conflicts
        @require_auth
        def protected_auth_route_test():
            # Accessing session directly in the test route for verification
            return jsonify(message="Auth Success", user_id_in_session=session.get('user_id')), 200

        # --- Route for @require_admin ---
        @self.app.route('/protected_admin_test') # Changed route name
        @require_admin
        def protected_admin_route_test():
            return jsonify(message="Admin Success", user_id_in_session=session.get('user_id'), role_in_session=session.get('role')), 200

        # --- Routes for @require_tree_access ---
        # Using active_tree_id from session
        @self.app.route('/protected_tree_session_view_test') # Changed
        @require_tree_access(level='view')
        def protected_tree_session_view_route_test():
            return jsonify(message="Tree View Success (Session)", 
                           user_id=session.get('user_id'), 
                           tree_id=str(g.active_tree_id),
                           access_level=g.tree_access_level), 200
        
        @self.app.route('/protected_tree_session_edit_test') # Changed
        @require_tree_access(level='edit')
        def protected_tree_session_edit_route_test():
            return jsonify(message="Tree Edit Success (Session)", 
                           user_id=session.get('user_id'), 
                           tree_id=str(g.active_tree_id),
                           access_level=g.tree_access_level), 200

        # Using tree_id_param from URL
        @self.app.route('/trees/<uuid:tree_id_param>/protected_tree_param_view_test') # Changed
        @require_tree_access(level='view')
        def protected_tree_param_view_route_test(tree_id_param):
            return jsonify(message="Tree View Success (Param)", 
                           user_id=session.get('user_id'), 
                           tree_id=str(g.active_tree_id),
                           access_level=g.tree_access_level), 200
        
        @self.app.route('/trees/<uuid:tree_id_param>/protected_tree_param_admin_test') # Changed
        @require_tree_access(level='admin')
        def protected_tree_param_admin_route_test(tree_id_param):
            return jsonify(message="Tree Admin Success (Param)", 
                           user_id=session.get('user_id'), 
                           tree_id=str(g.active_tree_id),
                           access_level=g.tree_access_level), 200

        self.client = self.app.test_client()

    # --- Tests for @require_auth ---
    def test_require_auth_no_session_user_id(self):
        # No session modification, so 'user_id' is not in session
        response = self.client.get('/protected_auth_test')
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authentication required", response.json['description'])

    def test_require_auth_with_session_user_id(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id_normal)
            # Add role as require_admin (which calls require_auth) might expect it
            sess['role'] = UserRole.user.value 
        response = self.client.get('/protected_auth_test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['user_id_in_session'], str(self.user_id_normal))

    # --- Tests for @require_admin ---
    def test_require_admin_no_session(self):
        response = self.client.get('/protected_admin_test')
        self.assertEqual(response.status_code, 401) # Caught by @require_auth

    def test_require_admin_non_admin_user(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id_normal)
            sess['role'] = UserRole.user.value # Non-admin role
        response = self.client.get('/protected_admin_test')
        self.assertEqual(response.status_code, 403)
        self.assertIn("Administrator access is required", response.json['description'])

    def test_require_admin_admin_user(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id_admin)
            sess['role'] = UserRole.admin.value # Admin role
        response = self.client.get('/protected_admin_test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['user_id_in_session'], str(self.user_id_admin))
        self.assertEqual(response.json['role_in_session'], UserRole.admin.value)

    # --- Tests for @require_tree_access ---
    # Patch 'g' where the decorator is defined
    @patch('backend.decorators.g') 
    def test_require_tree_access_auth_fail(self, mock_g_decorator):
        # No session for user_id, @require_auth within @require_tree_access should catch this
        response = self.client.get('/protected_tree_session_view_test')
        self.assertEqual(response.status_code, 401)

    @patch('backend.decorators.g')
    def test_require_tree_access_no_tree_id(self, mock_g_decorator):
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id_normal)
            sess['role'] = UserRole.user.value
            # 'active_tree_id' is NOT set in session for this route
        
        # Mock g.db for the decorator if it's reached
        mock_g_decorator.db = MagicMock()

        response = self.client.get('/protected_tree_session_view_test')
        self.assertEqual(response.status_code, 400)
        self.assertIn("No active tree selected", response.json['description']['message'])
        self.assertEqual(response.json['description']['code'], "NO_TREE_CONTEXT")

    @patch('backend.decorators.g')
    def test_require_tree_access_invalid_tree_id_session(self, mock_g_decorator):
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id_normal)
            sess['active_tree_id'] = "invalid-uuid-format"
        mock_g_decorator.db = MagicMock() # Mock db in case it's reached
        response = self.client.get('/protected_tree_session_view_test')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid tree ID format", response.json['description']['message'])

    @patch('backend.decorators.g')
    def test_require_tree_access_tree_not_found_db(self, mock_g_decorator):
        test_tree_id = uuid.uuid4()
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id_normal)
        
        mock_db_session = MagicMock()
        # Configure the mock query for Tree to return None
        mock_db_session.query(Tree).filter(Tree.id == test_tree_id).one_or_none.return_value = None
        mock_g_decorator.db = mock_db_session # Set the mocked db on g used by decorator

        response = self.client.get(f'/trees/{test_tree_id}/protected_tree_param_view_test')
        self.assertEqual(response.status_code, 404)
        self.assertIn(f"Tree with ID {test_tree_id} not found", response.json['description'])

    @patch('backend.decorators.g')
    def test_require_tree_access_public_tree_view_access(self, mock_g_decorator):
        test_tree_id = uuid.uuid4()
        mock_tree = create_mock_tree(test_tree_id, "Public Tree", self.tree_owner_id, privacy_setting=TreePrivacySettingEnum.PUBLIC)
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.other_user_id) # A user who is not owner
            sess['role'] = UserRole.user.value

        mock_db_session = MagicMock()
        mock_db_session.query(Tree).filter(Tree.id == test_tree_id).one_or_none.return_value = mock_tree
        # User has no specific TreeAccess record
        mock_db_session.query(TreeAccess).filter(TreeAccess.tree_id == test_tree_id, TreeAccess.user_id == self.other_user_id).one_or_none.return_value = None
        mock_g_decorator.db = mock_db_session

        response = self.client.get(f'/trees/{test_tree_id}/protected_tree_param_view_test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['access_level'], 'view') # Public access grants 'view'
        self.assertEqual(uuid.UUID(response.json['tree_id']), test_tree_id)

    @patch('backend.decorators.g')
    def test_require_tree_access_owner_has_admin_privileges(self, mock_g_decorator):
        test_tree_id = uuid.uuid4()
        # User self.tree_owner_id is the owner
        mock_tree = create_mock_tree(test_tree_id, "Owned Tree", self.tree_owner_id, privacy_setting=TreePrivacySettingEnum.PRIVATE)

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.tree_owner_id)
            sess['role'] = UserRole.user.value # Owner doesn't need to be system admin

        mock_db_session = MagicMock()
        mock_db_session.query(Tree).filter(Tree.id == test_tree_id).one_or_none.return_value = mock_tree
        # No TreeAccess record needed for owner
        mock_db_session.query(TreeAccess).filter(TreeAccess.tree_id == test_tree_id, TreeAccess.user_id == self.tree_owner_id).one_or_none.return_value = None
        mock_g_decorator.db = mock_db_session

        response = self.client.get(f'/trees/{test_tree_id}/protected_tree_param_admin_test') # Requesting 'admin' level
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['access_level'], 'admin') # Owner gets 'admin'

    @patch('backend.decorators.g')
    def test_require_tree_access_sufficient_permission_from_treeaccess(self, mock_g_decorator):
        test_tree_id = uuid.uuid4()
        mock_tree = create_mock_tree(test_tree_id, "Shared Tree", self.tree_owner_id, privacy_setting=TreePrivacySettingEnum.PRIVATE)
        # User self.user_id_normal has 'edit' access
        mock_access_entry = create_mock_tree_access(test_tree_id, self.user_id_normal, 'edit')

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id_normal)
            sess['role'] = UserRole.user.value
            sess['active_tree_id'] = str(test_tree_id) # Use session-based route

        mock_db_session = MagicMock()
        mock_db_session.query(Tree).filter(Tree.id == test_tree_id).one_or_none.return_value = mock_tree
        mock_db_session.query(TreeAccess).filter(TreeAccess.tree_id == test_tree_id, TreeAccess.user_id == self.user_id_normal).one_or_none.return_value = mock_access_entry
        mock_g_decorator.db = mock_db_session

        response = self.client.get('/protected_tree_session_edit_test') # Requesting 'edit'
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['access_level'], 'edit')

    @patch('backend.decorators.g')
    def test_require_tree_access_insufficient_permission_from_treeaccess(self, mock_g_decorator):
        test_tree_id = uuid.uuid4()
        mock_tree = create_mock_tree(test_tree_id, "Shared Tree", self.tree_owner_id, privacy_setting=TreePrivacySettingEnum.PRIVATE)
        # User self.user_id_normal has 'view' access
        mock_access_entry = create_mock_tree_access(test_tree_id, self.user_id_normal, 'view')

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.user_id_normal)
            sess['role'] = UserRole.user.value
            sess['active_tree_id'] = str(test_tree_id)

        mock_db_session = MagicMock()
        mock_db_session.query(Tree).filter(Tree.id == test_tree_id).one_or_none.return_value = mock_tree
        mock_db_session.query(TreeAccess).filter(TreeAccess.tree_id == test_tree_id, TreeAccess.user_id == self.user_id_normal).one_or_none.return_value = mock_access_entry
        mock_g_decorator.db = mock_db_session

        response = self.client.get('/protected_tree_session_edit_test') # Requesting 'edit'
        self.assertEqual(response.status_code, 403)
        self.assertIn("You do not have sufficient permissions ('edit' required)", response.json['description']['message'])

    @patch('backend.decorators.g')
    def test_require_tree_access_no_explicit_access_private_tree(self, mock_g_decorator):
        test_tree_id = uuid.uuid4()
        mock_tree = create_mock_tree(test_tree_id, "Private Tree", self.tree_owner_id, privacy_setting=TreePrivacySettingEnum.PRIVATE)

        with self.client.session_transaction() as sess:
            sess['user_id'] = str(self.other_user_id) # Not the owner
            sess['role'] = UserRole.user.value
        
        mock_db_session = MagicMock()
        mock_db_session.query(Tree).filter(Tree.id == test_tree_id).one_or_none.return_value = mock_tree
        # No TreeAccess record for self.other_user_id
        mock_db_session.query(TreeAccess).filter(TreeAccess.tree_id == test_tree_id, TreeAccess.user_id == self.other_user_id).one_or_none.return_value = None
        mock_g_decorator.db = mock_db_session

        response = self.client.get(f'/trees/{test_tree_id}/protected_tree_param_view_test') # Requesting 'view'
        self.assertEqual(response.status_code, 403)
        self.assertIn("You do not have sufficient permissions ('view' required)", response.json['description']['message'])


if __name__ == '__main__':
    unittest.main()
