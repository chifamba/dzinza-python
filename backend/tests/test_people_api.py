import unittest
import json
import uuid
from unittest.mock import patch, MagicMock

from flask import Flask, jsonify, g, session

# Assuming your blueprint and service are importable
# Adjust paths as necessary
from blueprints.people import people_bp 
# Import the actual services that will be mocked
import services.person_service as person_service_module

class TestPeopleAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(people_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Mock session and g for decorators and user context
        # self.app.before_request(self.mock_before_request)
        
        self.test_user_id = str(uuid.uuid4())
        self.test_tree_id = str(uuid.uuid4())
        self.test_person_id = str(uuid.uuid4())

        # Patch the actual service functions used by the blueprint endpoints
        self.patcher_create_person_db = patch('blueprints.people.create_person_db')
        self.patcher_update_person_db = patch('blueprints.people.update_person_db')
        self.patcher_get_person_db = patch('blueprints.people.get_person_db') # If needed for PUT setup
        self.patcher_require_tree_access = patch('blueprints.people.require_tree_access')


        self.mock_create_person_db = self.patcher_create_person_db.start()
        self.mock_update_person_db = self.patcher_update_person_db.start()
        self.mock_get_person_db = self.patcher_get_person_db.start()
        self.mock_require_tree_access = self.patcher_require_tree_access.start()
        
        # Configure the decorator mock to just run the decorated function
        self.mock_require_tree_access.side_effect = lambda level: (lambda func: func)


    def tearDown(self):
        self.patcher_create_person_db.stop()
        self.patcher_update_person_db.stop()
        self.patcher_get_person_db.stop()
        self.patcher_require_tree_access.stop()


    def test_create_person_endpoint_with_new_fields(self):
        person_data_to_send = {
            "first_name": "ApiTest", "last_name": "User",
            "profile_picture_url": "http://api.example.com/profile.jpg",
            "custom_fields": {"department": "api_dev", "employee_id": "A123"}
        }
        
        # Mock the service layer response
        mock_service_response = {
            "id": self.test_person_id, 
            **person_data_to_send # Service should return the data as saved
        }
        self.mock_create_person_db.return_value = mock_service_response

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id # For @require_tree_access if it checks session

            # Simulate g.db and g.active_tree_id if @require_tree_access uses them directly
            # This is a bit of a workaround for not having full app context.
            # A better way might involve a custom test app_context processor.
            with self.app.test_request_context('/api/people', method='POST'):
                if hasattr(g, 'db'): g.db = MagicMock() 
                if hasattr(g, 'active_tree_id'): g.active_tree_id = self.test_tree_id


                response = client.post('/api/people', json=person_data_to_send)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, mock_service_response)
        self.mock_create_person_db.assert_called_once_with(
            ANY, # db session mock
            uuid.UUID(self.test_user_id), 
            uuid.UUID(self.test_tree_id), 
            person_data_to_send
        )

    def test_create_person_endpoint_without_new_fields(self):
        person_data_to_send = {"first_name": "ApiSimple", "last_name": "User"}
        
        mock_service_response = {
            "id": self.test_person_id, 
            **person_data_to_send,
            "profile_picture_url": None, # Expected default
            "custom_fields": {}          # Expected default
        }
        self.mock_create_person_db.return_value = mock_service_response

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            
            with self.app.test_request_context('/api/people', method='POST'):
                 if hasattr(g, 'db'): g.db = MagicMock() 
                 if hasattr(g, 'active_tree_id'): g.active_tree_id = self.test_tree_id

                 response = client.post('/api/people', json=person_data_to_send)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, mock_service_response)


    def test_update_person_endpoint_with_new_fields(self):
        update_data_to_send = {
            "profile_picture_url": "http://updated.com/new_profile.png",
            "custom_fields": {"status": "promoted", "office": "corner"}
        }
        
        mock_service_response = {
            "id": self.test_person_id, 
            "first_name": "OriginalName", # Assuming some original data
            **update_data_to_send
        }
        self.mock_update_person_db.return_value = mock_service_response

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id

            with self.app.test_request_context(f'/api/people/{self.test_person_id}', method='PUT'):
                 if hasattr(g, 'db'): g.db = MagicMock()
                 if hasattr(g, 'active_tree_id'): g.active_tree_id = self.test_tree_id
            
                 response = client.put(f'/api/people/{self.test_person_id}', json=update_data_to_send)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_service_response)
        self.mock_update_person_db.assert_called_once_with(
            ANY, # db session mock
            uuid.UUID(self.test_person_id), 
            uuid.UUID(self.test_tree_id), 
            update_data_to_send
        )

    def test_update_person_endpoint_clear_fields(self):
        update_data_to_send = {
            "profile_picture_url": None,
            "custom_fields": {}
        }
        
        mock_service_response = {
            "id": self.test_person_id,
            "first_name": "OriginalName",
            "profile_picture_url": None, # Updated value
            "custom_fields": {}          # Updated value
        }
        self.mock_update_person_db.return_value = mock_service_response

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            
            with self.app.test_request_context(f'/api/people/{self.test_person_id}', method='PUT'):
                if hasattr(g, 'db'): g.db = MagicMock()
                if hasattr(g, 'active_tree_id'): g.active_tree_id = self.test_tree_id

                response = client.put(f'/api/people/{self.test_person_id}', json=update_data_to_send)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_service_response)

    # Example of testing validation (if blueprint were to do it, but service handles it)
    # For this setup, we assume the service layer (mocked here) would raise HTTPException for bad data
    def test_update_person_endpoint_invalid_custom_fields_type(self):
        update_data_to_send = {"custom_fields": "not_a_dictionary"}
        
        # Simulate the service layer raising an HTTPException (e.g., BadRequest 400)
        # This is what the actual service would do, and the blueprint would propagate it.
        self.mock_update_person_db.side_effect = BadRequest(description="Custom fields must be a dictionary or null.")

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id

            with self.app.test_request_context(f'/api/people/{self.test_person_id}', method='PUT'):
                if hasattr(g, 'db'): g.db = MagicMock()
                if hasattr(g, 'active_tree_id'): g.active_tree_id = self.test_tree_id
            
                response = client.put(f'/api/people/{self.test_person_id}', json=update_data_to_send)

        self.assertEqual(response.status_code, 400) # Werkzeug's BadRequest maps to 400
        self.assertIn("Custom fields must be a dictionary or null", response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
