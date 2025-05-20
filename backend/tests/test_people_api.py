import unittest
import json
import uuid
import io # For file uploads
from unittest.mock import patch, MagicMock, ANY

from flask import Flask, jsonify, g, session
from werkzeug.exceptions import BadRequest, InternalServerError, Forbidden, NotFound # For simulating service errors

# Assuming your blueprint and service are importable
# Adjust paths as necessary
from blueprints.people import people_bp 
# Import the actual services that will be mocked
# import services.person_service as person_service_module # Not needed if patching via string path

class TestPeopleAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'super_secret_key_for_testing_session' # Required for session
        self.app.register_blueprint(people_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        self.test_user_id = str(uuid.uuid4())
        self.test_tree_id = str(uuid.uuid4())
        self.test_person_id = str(uuid.uuid4())

        # Patch the actual service functions used by the blueprint endpoints
        self.patcher_create_person_db = patch('blueprints.people.create_person_db')
        self.patcher_update_person_db = patch('blueprints.people.update_person_db')
        self.patcher_get_person_db = patch('blueprints.people.get_person_db')
        self.patcher_delete_person_db = patch('blueprints.people.delete_person_db')
        self.patcher_upload_profile_picture_db = patch('blueprints.people.upload_profile_picture_db')
        self.patcher_get_media_for_entity_db = patch('blueprints.people.get_media_for_entity_db')
        self.patcher_get_events_for_person_db = patch('blueprints.people.get_events_for_person_db') # New patch for person events


        self.patcher_require_tree_access = patch('blueprints.people.require_tree_access')
        self.patcher_require_auth = patch('blueprints.people.require_auth') 

        self.mock_create_person_db = self.patcher_create_person_db.start()
        self.mock_update_person_db = self.patcher_update_person_db.start()
        self.mock_get_person_db = self.patcher_get_person_db.start()
        self.mock_delete_person_db = self.patcher_delete_person_db.start()
        self.mock_upload_profile_picture_db = self.patcher_upload_profile_picture_db.start()
        self.mock_get_media_for_entity_db = self.patcher_get_media_for_entity_db.start()
        self.mock_get_events_for_person_db = self.patcher_get_events_for_person_db.start() # Start the new patch
        
        self.mock_require_tree_access_decorator = self.patcher_require_tree_access.start()
        self.mock_require_auth_decorator = self.patcher_require_auth.start()
        
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)
        self.mock_require_auth_decorator.side_effect = lambda func: func


    def tearDown(self):
        self.patcher_create_person_db.stop()
        self.patcher_update_person_db.stop()
        self.patcher_get_person_db.stop()
        self.patcher_delete_person_db.stop()
        self.patcher_upload_profile_picture_db.stop()
        self.patcher_get_media_for_entity_db.stop()
        self.patcher_get_events_for_person_db.stop() # Stop the new patch
        self.patcher_require_tree_access.stop()
        self.patcher_require_auth.stop()

    # ... (other existing tests like _make_request_context, create_person, update_person, profile_picture, get_media) ...
    def test_create_person_endpoint_with_new_fields(self):
        person_data_to_send = {
            "first_name": "ApiTest", "last_name": "User",
            "profile_picture_url": "http://api.example.com/profile.jpg",
            "custom_fields": {"department": "api_dev", "employee_id": "A123"}
        }
        mock_service_response = {"id": self.test_person_id, **person_data_to_send}
        self.mock_create_person_db.return_value = mock_service_response

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post('/api/people', json=person_data_to_send)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, mock_service_response)
        self.mock_create_person_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_user_id), uuid.UUID(self.test_tree_id), person_data_to_send
        )
    
    def test_update_person_endpoint_with_new_fields(self):
        update_data_to_send = {
            "profile_picture_url": "http://updated.com/new_profile.png",
            "custom_fields": {"status": "promoted", "office": "corner"}
        }
        mock_service_response = {"id": self.test_person_id, "first_name": "OriginalName", **update_data_to_send}
        self.mock_update_person_db.return_value = mock_service_response

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.put(f'/api/people/{self.test_person_id}', json=update_data_to_send)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_service_response)
        self.mock_update_person_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_person_id), uuid.UUID(self.test_tree_id), update_data_to_send
        )
    
    def test_upload_person_profile_picture_success(self):
        mock_response_data = {"id": self.test_person_id, "profile_picture_url": "some/s3/key.jpg"}
        self.mock_upload_profile_picture_db.return_value = mock_response_data
        
        data = {'file': (io.BytesIO(b"fake image data"), 'test.jpg')}

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context(): 
                g.db = MagicMock() 
                g.active_tree_id = self.test_tree_id 
                response = client.post(
                    f'/api/people/{self.test_person_id}/profile_picture',
                    data=data,
                    content_type='multipart/form-data'
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)
        self.mock_upload_profile_picture_db.assert_called_once_with(
            db=g.db,
            person_id=uuid.UUID(self.test_person_id),
            tree_id=uuid.UUID(self.test_tree_id), # Changed from g.active_tree_id to self.test_tree_id
            user_id=uuid.UUID(self.test_user_id),
            file_stream=ANY, 
            filename='test.jpg',
            content_type=ANY 
        )

    def test_get_person_media_endpoint_success(self):
        mock_media_list = {"items": [{"id": str(uuid.uuid4()), "file_name": "media1.jpg"}]}
        self.mock_get_media_for_entity_db.return_value = mock_media_list

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id 
                response = client.get(f'/api/people/{self.test_person_id}/media?page=1&per_page=10')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_media_list)
        self.mock_get_media_for_entity_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_tree_id), "Person", uuid.UUID(self.test_person_id),
            1, 10, "created_at", "desc" 
        )

    # --- Tests for Get Person Events Endpoint ---
    def test_get_person_events_endpoint_success(self):
        mock_events_list = {"items": [{"id": str(uuid.uuid4()), "event_type": "BIRTH"}]}
        self.mock_get_events_for_person_db.return_value = mock_events_list

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id 
                response = client.get(f'/api/people/{self.test_person_id}/events?page=2&per_page=5&sort_by=event_type&sort_order=desc')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_events_list)
        self.mock_get_events_for_person_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_tree_id), uuid.UUID(self.test_person_id),
            2, 5, "event_type", "desc"
        )

    def test_get_person_events_endpoint_default_pagination_and_sort(self):
        mock_events_list = {"items": []}
        self.mock_get_events_for_person_db.return_value = mock_events_list

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/people/{self.test_person_id}/events')
        
        self.assertEqual(response.status_code, 200)
        self.mock_get_events_for_person_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_tree_id), uuid.UUID(self.test_person_id),
            ANY, ANY, "date", "asc" # Default sort for events
        )

    def test_get_person_events_endpoint_service_failure(self):
        self.mock_get_events_for_person_db.side_effect = InternalServerError(description="Events DB error")
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/people/{self.test_person_id}/events')

        self.assertEqual(response.status_code, 500)
        self.assertIn("Events DB error", response.json['message'])


if __name__ == '__main__':
    unittest.main()
