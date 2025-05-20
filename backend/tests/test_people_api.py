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
        self.patcher_upload_profile_picture_db = patch('blueprints.people.upload_profile_picture_db') # New patch
        self.patcher_get_media_for_entity_db = patch('blueprints.people.get_media_for_entity_db')


        self.patcher_require_tree_access = patch('blueprints.people.require_tree_access')
        self.patcher_require_auth = patch('blueprints.people.require_auth') # If it's a separate decorator

        self.mock_create_person_db = self.patcher_create_person_db.start()
        self.mock_update_person_db = self.patcher_update_person_db.start()
        self.mock_get_person_db = self.patcher_get_person_db.start()
        self.mock_delete_person_db = self.patcher_delete_person_db.start()
        self.mock_upload_profile_picture_db = self.patcher_upload_profile_picture_db.start()
        self.mock_get_media_for_entity_db = self.patcher_get_media_for_entity_db.start()
        
        self.mock_require_tree_access_decorator = self.patcher_require_tree_access.start()
        self.mock_require_auth_decorator = self.patcher_require_auth.start()
        
        # Configure decorator mocks to just run the decorated function
        # This bypasses actual auth/permission logic for these tests
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)
        self.mock_require_auth_decorator.side_effect = lambda func: func


    def tearDown(self):
        self.patcher_create_person_db.stop()
        self.patcher_update_person_db.stop()
        self.patcher_get_person_db.stop()
        self.patcher_delete_person_db.stop()
        self.patcher_upload_profile_picture_db.stop()
        self.patcher_get_media_for_entity_db.stop()
        self.patcher_require_tree_access.stop()
        self.patcher_require_auth.stop()

    # --- Helper for setting up flask context ---
    def _make_request_context(self, path, method='GET'):
        # This helper ensures g.db and g.active_tree_id are set as expected by endpoints
        # after decorators might have run or if decorators are fully bypassed.
        # It also sets up the session.
        context = self.app.test_request_context(path, method=method)
        
        # Simulate what decorators or before_request hooks would do
        # If your actual decorators modify g or session, mimic that here.
        # For these tests, we are mocking the decorators themselves to bypass their logic,
        # but the endpoint handlers might still expect g.db and g.active_tree_id.
        
        # To set g attributes, we need to be within the app context
        # context.push() would typically do this, but for test_client requests,
        # Flask handles context. Here, we ensure session and g are populated
        # before the client makes the request if the endpoint relies on them directly
        # (which it does for g.db, g.active_tree_id, and session['user_id']).

        # The session is best managed using `with client.session_transaction() as sess:`
        # For g attributes, if decorators are perfectly mocked to set them, this might not be needed.
        # However, if endpoints access g directly and decorators are fully bypassed,
        # we might need a way to inject into g. For now, assuming decorators set them or
        # the endpoint logic is simple enough not to rely on complex g setup beyond session.
        
        # A common pattern is to have a @app.before_request that sets g.db and g.active_tree_id
        # If that's the case, and it's not running in tests, we'd mock it or replicate its effect.
        # For this test setup, the decorators are mocked, and we manually set session.
        # The endpoint itself uses g.db and g.active_tree_id, which are assumed to be populated
        # by a real before_request hook or the mocked decorators.
        # Let's ensure they are available if the endpoint directly uses them.
        
        # The test_client runs within an app context, so g should be available.
        # We'll set g.db and g.active_tree_id inside the test methods using `with self.app.app_context():`
        # or rely on the session context provided by `with self.client:`

        return context


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
            
            # Simulate g values if decorators don't set them due to mocking
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post('/api/people', json=person_data_to_send)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, mock_service_response)
        self.mock_create_person_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_user_id), uuid.UUID(self.test_tree_id), person_data_to_send
        )
    
    # ... (other existing tests for create, update, delete, get_person, get_all_people) ...
    # Assuming they are updated similarly to use the app_context for g
    # For brevity, I'll skip re-listing them if they follow the pattern above.
    # Ensure all existing tests are passing with the new setup if g is used.

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
    
    # --- Tests for Profile Picture Upload Endpoint ---
    def test_upload_person_profile_picture_success(self):
        mock_response_data = {"id": self.test_person_id, "profile_picture_url": "some/s3/key.jpg"}
        self.mock_upload_profile_picture_db.return_value = mock_response_data
        
        data = {'file': (io.BytesIO(b"fake image data"), 'test.jpg')}

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context(): # Ensure g is available
                g.db = MagicMock() # Mock db on g
                g.active_tree_id = self.test_tree_id # Mock active_tree_id on g
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
            tree_id=uuid.UUID(self.test_tree_id),
            user_id=uuid.UUID(self.test_user_id),
            file_stream=ANY, # io.BytesIO object
            filename='test.jpg',
            content_type=ANY # Actual content type from request
        )

    def test_upload_person_profile_picture_no_file_part(self):
        with self.client as client:
            with client.session_transaction() as sess: # Ensure session for decorators
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post(f'/api/people/{self.test_person_id}/profile_picture', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("No file part", response.json['message'])

    def test_upload_person_profile_picture_no_selected_file(self):
        data = {'file': (io.BytesIO(b""), '')} # Empty filename
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post(
                    f'/api/people/{self.test_person_id}/profile_picture',
                    data=data, content_type='multipart/form-data'
                )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No selected file", response.json['message'])

    def test_upload_person_profile_picture_service_failure(self):
        self.mock_upload_profile_picture_db.side_effect = InternalServerError(description="S3 is down")
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
                    data=data, content_type='multipart/form-data'
                )
        self.assertEqual(response.status_code, 500)
        self.assertIn("S3 is down", response.json['message'])

    # --- Tests for Get Person Media Endpoint ---
    def test_get_person_media_endpoint_success(self):
        mock_media_list = {"items": [{"id": str(uuid.uuid4()), "file_name": "media1.jpg"}]}
        self.mock_get_media_for_entity_db.return_value = mock_media_list

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id # Ensure this is set as UUID in service call
                response = client.get(f'/api/people/{self.test_person_id}/media?page=1&per_page=10')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_media_list)
        self.mock_get_media_for_entity_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_tree_id), "Person", uuid.UUID(self.test_person_id),
            1, 10, "created_at", "desc" # Default sort order
        )

    def test_get_person_media_endpoint_service_failure(self):
        self.mock_get_media_for_entity_db.side_effect = InternalServerError(description="DB error")
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/people/{self.test_person_id}/media')

        self.assertEqual(response.status_code, 500)
        self.assertIn("DB error", response.json['message'])


if __name__ == '__main__':
    unittest.main()
