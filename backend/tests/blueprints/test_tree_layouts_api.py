import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, jsonify, g
import uuid
import json

# Import the blueprint and model (model might be used for constructing mock return values)
from backend.blueprints.tree_layouts import tree_layouts_bp, get_service
from backend.models import TreeLayout # For constructing mock service return values
from backend.services.tree_layout_service import TreeLayoutService # For type hinting mocks

# Helper to generate UUID strings
def new_uuid_str():
    return str(uuid.uuid4())

class TestTreeLayoutsAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        # Minimal app setup for testing blueprint
        # In a real app, you might have a test_app factory

        # Mock the db session for the get_service helper in the blueprint
        self.mock_db_session_for_g = MagicMock()

        def mock_get_db_session_for_g():
            return self.mock_db_session_for_g

        self.app.before_request(lambda: setattr(g, 'db', mock_get_db_session_for_g()))

        self.app.register_blueprint(tree_layouts_bp, url_prefix='/api/tree_layouts')
        self.client = self.app.test_client()

        # Patch the TreeLayoutService directly where it's instantiated or used.
        # The blueprint uses a get_service() helper which instantiates TreeLayoutService.
        # So we patch 'backend.blueprints.tree_layouts.TreeLayoutService'
        self.mock_service_patch = patch('backend.blueprints.tree_layouts.TreeLayoutService')
        self.MockTreeLayoutServiceClass = self.mock_service_patch.start()

        # Configure the mock instance that the service factory (get_service) will return
        self.mock_service_instance = MagicMock(spec=TreeLayoutService)
        self.MockTreeLayoutServiceClass.return_value = self.mock_service_instance


    def tearDown(self):
        self.mock_service_patch.stop()

    def test_save_or_update_tree_layout_create_new(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        layout_data = {"positions": [{"id": "node1", "x": 10, "y": 20}]}

        mock_created_layout = TreeLayout(id=new_uuid_str(), user_id=user_id, tree_id=tree_id, layout_data=layout_data)
        self.mock_service_instance.create_or_update_layout.return_value = mock_created_layout

        response = self.client.post(f'/api/tree_layouts',
                                     json={'user_id': user_id, 'tree_id': tree_id, 'layout_data': layout_data})

        self.assertEqual(response.status_code, 200) # Or 201 if you distinguish
        self.mock_service_instance.create_or_update_layout.assert_called_once_with(user_id=user_id, tree_id=tree_id, layout_data=layout_data)
        self.assertIn('layout saved successfully', response.json['message'].lower())
        self.assertEqual(response.json['layout']['id'], mock_created_layout.id)


    def test_save_or_update_tree_layout_missing_fields(self):
        response = self.client.post(f'/api/tree_layouts', json={'user_id': new_uuid_str()})
        self.assertEqual(response.status_code, 400)
        self.assertIn('missing required fields', response.json['error'].lower())

    def test_get_tree_layout_found(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        layout_data = {"positions": [{"id": "node1", "x": 10, "y": 20}]}
        mock_layout = TreeLayout(id=new_uuid_str(), user_id=user_id, tree_id=tree_id, layout_data=layout_data)

        self.mock_service_instance.get_layout.return_value = mock_layout

        response = self.client.get(f'/api/tree_layouts/{tree_id}/{user_id}')

        self.assertEqual(response.status_code, 200)
        self.mock_service_instance.get_layout.assert_called_once_with(user_id=user_id, tree_id=tree_id)
        self.assertEqual(response.json['id'], mock_layout.id)
        self.assertEqual(response.json['layout_data'], layout_data)

    def test_get_tree_layout_not_found(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        self.mock_service_instance.get_layout.return_value = None

        response = self.client.get(f'/api/tree_layouts/{tree_id}/{user_id}')

        self.assertEqual(response.status_code, 404)
        self.mock_service_instance.get_layout.assert_called_once_with(user_id=user_id, tree_id=tree_id)
        self.assertIn('layout not found', response.json['error'].lower())

    def test_delete_tree_layout_success(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        self.mock_service_instance.delete_layout.return_value = True # Simulate successful deletion

        response = self.client.delete(f'/api/tree_layouts/{tree_id}/{user_id}')

        self.assertEqual(response.status_code, 200)
        self.mock_service_instance.delete_layout.assert_called_once_with(user_id=user_id, tree_id=tree_id)
        self.assertIn('layout deleted successfully', response.json['message'].lower())

    def test_delete_tree_layout_not_found_or_failed(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        self.mock_service_instance.delete_layout.return_value = False # Simulate layout not found or delete failed

        response = self.client.delete(f'/api/tree_layouts/{tree_id}/{user_id}')

        self.assertEqual(response.status_code, 404) # Or 500 depending on desired response for "failed"
        self.mock_service_instance.delete_layout.assert_called_once_with(user_id=user_id, tree_id=tree_id)
        self.assertIn('failed to delete layout or layout not found', response.json['error'].lower())

    def test_save_layout_service_failure(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        layout_data = {"positions": []}
        self.mock_service_instance.create_or_update_layout.return_value = None # Simulate service returning None due to internal error

        response = self.client.post(f'/api/tree_layouts',
                                     json={'user_id': user_id, 'tree_id': tree_id, 'layout_data': layout_data})

        self.assertEqual(response.status_code, 500)
        self.assertIn('failed to save tree layout', response.json['error'].lower())

    def test_get_service_no_db_in_g(self):
        # Temporarily remove g.db to test the error handling in get_service
        with self.app.test_request_context():
            if hasattr(g, 'db'):
                delattr(g, 'db')

            # This test needs to call a route to trigger get_service()
            # We expect a 500 if g.db is not available.
            # The actual service call doesn't matter here, just that get_service() is invoked.
            self.mock_service_instance.get_layout.return_value = None # Set up a default return
            response = self.client.get(f'/api/tree_layouts/{new_uuid_str()}/{new_uuid_str()}')
            self.assertEqual(response.status_code, 500)
            self.assertIn('db session not available', response.json['error'].lower())
            # Restore g.db for other tests if necessary, though setUp should handle it.


if __name__ == '__main__':
    unittest.main()
