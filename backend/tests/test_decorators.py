import unittest
from unittest.mock import MagicMock, patch
import uuid

from flask import Flask, g, session, jsonify, current_app
from werkzeug.exceptions import HTTPException, Unauthorized, Forbidden, NotFound

# Adjust import path as per your project structure
from models import Tree, TreeAccess, User, TreePrivacySettingEnum
from decorators import require_tree_access, require_auth # Assuming require_auth is also in decorators.py

class TestDecorators(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'test_secret_key_decorators' # For session
        self.client = self.app.test_client()

        self.test_user_id = uuid.uuid4()
        self.test_owner_id = uuid.uuid4()
        self.test_tree_id = uuid.uuid4()

        # Mock DB session for g.db
        self.mock_db_session = MagicMock()
        
        # This is a dummy endpoint that will be protected by the decorator
        @self.app.route('/test_tree_route/<uuid:tree_id_param>')
        @require_tree_access(level='view') # Default level, can be overridden in specific tests
        def test_view_route(tree_id_param):
            return jsonify(message="View access granted", tree_id=str(g.active_tree_id), access_level=g.tree_access_level), 200

        @self.app.route('/test_edit_route/<uuid:tree_id_param>')
        @require_tree_access(level='edit')
        def test_edit_route(tree_id_param):
            return jsonify(message="Edit access granted", tree_id=str(g.active_tree_id), access_level=g.tree_access_level), 200

        @self.app.route('/test_admin_route/<uuid:tree_id_param>')
        @require_tree_access(level='admin')
        def test_admin_route(tree_id_param):
            return jsonify(message="Admin access granted", tree_id=str(g.active_tree_id), access_level=g.tree_access_level), 200

    def _setup_mocks_for_request(self, mock_tree_instance=None, mock_tree_access_instance=None):
        # Mock g.db
        g.db = self.mock_db_session
        
        # Mock DB query results
        self.mock_db_session.query.return_value.filter.return_value.one_or_none.side_effect = \
            lambda *args, **kwargs: mock_tree_instance if args[0].__class__ == Tree else \
                                   mock_tree_access_instance if args[0].__class__ == TreeAccess else None
        
        # If Tree model is directly queried (it is)
        if mock_tree_instance:
            self.mock_db_session.query(Tree).filter(Tree.id == self.test_tree_id).one_or_none.return_value = mock_tree_instance
        
        # If TreeAccess model is directly queried
        if mock_tree_access_instance:
             self.mock_db_session.query(TreeAccess).filter(
                TreeAccess.tree_id == self.test_tree_id, 
                TreeAccess.user_id == self.test_user_id
            ).one_or_none.return_value = mock_tree_access_instance
        else: # Ensure it returns None if no specific access entry
            self.mock_db_session.query(TreeAccess).filter(
                TreeAccess.tree_id == self.test_tree_id, 
                TreeAccess.user_id == self.test_user_id
            ).one_or_none.return_value = None


    # Scenario 1: Tree is PUBLIC. User (not owner/not in TreeAccess) requests with level='view'. Should pass.
    def test_public_tree_view_access_non_owner_no_entry(self):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_owner_id # Different from test_user_id
        mock_tree.privacy_setting = TreePrivacySettingEnum.PUBLIC
        
        with self.app.test_request_context(f'/test_view_route/{self.test_tree_id}'):
            with self.client: # Use client context for session
                with client.session_transaction() as sess:
                    sess['user_id'] = str(self.test_user_id)
                
                self._setup_mocks_for_request(mock_tree_instance=mock_tree, mock_tree_access_instance=None)
                
                response = self.client.get(f'/test_view_route/{self.test_tree_id}')
                
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['access_level'], 'view')


    # Scenario 2: Tree is PUBLIC. User requests with level='edit'. Should fail (unless user is owner/has 'edit' in TreeAccess).
    def test_public_tree_edit_access_non_owner_no_entry_fails(self):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_owner_id
        mock_tree.privacy_setting = TreePrivacySettingEnum.PUBLIC
        
        with self.app.test_request_context(f'/test_edit_route/{self.test_tree_id}'):
            with self.client:
                with client.session_transaction() as sess:
                    sess['user_id'] = str(self.test_user_id)
                self._setup_mocks_for_request(mock_tree_instance=mock_tree, mock_tree_access_instance=None)
                response = self.client.get(f'/test_edit_route/{self.test_tree_id}')
        self.assertEqual(response.status_code, 403) # Forbidden

    # Scenario 3: Tree is PRIVATE. User (not owner/not in TreeAccess) requests with level='view'. Should fail.
    def test_private_tree_view_access_non_owner_no_entry_fails(self):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_owner_id
        mock_tree.privacy_setting = TreePrivacySettingEnum.PRIVATE
        
        with self.app.test_request_context(f'/test_view_route/{self.test_tree_id}'):
            with self.client:
                with client.session_transaction() as sess:
                    sess['user_id'] = str(self.test_user_id)
                self._setup_mocks_for_request(mock_tree_instance=mock_tree, mock_tree_access_instance=None)
                response = self.client.get(f'/test_view_route/{self.test_tree_id}')
        self.assertEqual(response.status_code, 403)

    # Scenario 4: Tree is PRIVATE. User is owner. Requests with level='admin'. Should pass.
    def test_private_tree_admin_access_owner_succeeds(self):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_user_id # User IS the owner
        mock_tree.privacy_setting = TreePrivacySettingEnum.PRIVATE
        
        with self.app.test_request_context(f'/test_admin_route/{self.test_tree_id}'):
            with self.client:
                with client.session_transaction() as sess:
                    sess['user_id'] = str(self.test_user_id)
                self._setup_mocks_for_request(mock_tree_instance=mock_tree, mock_tree_access_instance=None)
                response = self.client.get(f'/test_admin_route/{self.test_tree_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['access_level'], 'admin')

    # Scenario 5: Tree is PRIVATE. User has 'view' access in TreeAccess. Requests with level='view'. Should pass.
    def test_private_tree_view_access_with_view_entry_succeeds(self):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_owner_id 
        mock_tree.privacy_setting = TreePrivacySettingEnum.PRIVATE
        
        mock_access_entry = MagicMock(spec=TreeAccess)
        mock_access_entry.access_level = 'view'
        
        with self.app.test_request_context(f'/test_view_route/{self.test_tree_id}'):
            with self.client:
                with client.session_transaction() as sess:
                    sess['user_id'] = str(self.test_user_id)
                self._setup_mocks_for_request(mock_tree_instance=mock_tree, mock_tree_access_instance=mock_access_entry)
                response = self.client.get(f'/test_view_route/{self.test_tree_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['access_level'], 'view')

    # Scenario 5b: Tree is PRIVATE. User has 'view' access in TreeAccess. Requests with level='edit'. Should fail.
    def test_private_tree_edit_access_with_view_entry_fails(self):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_owner_id
        mock_tree.privacy_setting = TreePrivacySettingEnum.PRIVATE
        
        mock_access_entry = MagicMock(spec=TreeAccess)
        mock_access_entry.access_level = 'view'
        
        with self.app.test_request_context(f'/test_edit_route/{self.test_tree_id}'):
            with self.client:
                with client.session_transaction() as sess:
                    sess['user_id'] = str(self.test_user_id)
                self._setup_mocks_for_request(mock_tree_instance=mock_tree, mock_tree_access_instance=mock_access_entry)
                response = self.client.get(f'/test_edit_route/{self.test_tree_id}')
        self.assertEqual(response.status_code, 403)

    def test_require_tree_access_no_tree_id_context(self):
        # Test case where neither tree_id_param nor active_tree_id in session is available
        with self.app.test_request_context(f'/test_view_route/'): # No tree_id_param in URL
             with self.client:
                with client.session_transaction() as sess:
                    sess['user_id'] = str(self.test_user_id)
                    # No active_tree_id in session
                
                # Simulate route that might be defined without tree_id_param, if decorator was used differently
                # For this test, we call a route that expects it, to see if decorator handles missing context
                # This will likely result in a 404 from Flask before decorator, but if decorator was on a route
                # that didn't take tree_id_param, it should abort 400.
                # The test routes are defined with <uuid:tree_id_param>, so this test is more conceptual
                # for a scenario where tree_id is solely from session.
                # Let's call a modified route for this.
                
                @self.app.route('/test_no_tree_id_route')
                @require_tree_access(level='view')
                def test_no_tree_id_route_func():
                    return "Should not reach here", 200

                self._setup_mocks_for_request(mock_tree_instance=None) # No tree will be found
                response = self.client.get('/test_no_tree_id_route')

        self.assertEqual(response.status_code, 400) # Expecting decorator to abort
        self.assertIn("NO_TREE_CONTEXT", response.json['message']['code'])


if __name__ == '__main__':
    unittest.main()
