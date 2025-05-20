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
from services.person_service import get_all_people_db # Import the actual service for one test

class TestPeopleAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'super_secret_key_for_testing_session' # Required for session
        self.app.register_blueprint(people_bp)
        self.app.config['TESTING'] = True
        # self.app.config['SERVER_NAME'] = 'localhost.localdomain' # Sometimes needed for url_for
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
        self.patcher_get_events_for_person_db = patch('blueprints.people.get_events_for_person_db')
        self.patcher_get_all_people_db = patch('blueprints.people.get_all_people_db') # Patch for most filter tests


        self.patcher_require_tree_access = patch('blueprints.people.require_tree_access')
        self.patcher_require_auth = patch('blueprints.people.require_auth') 

        self.mock_create_person_db = self.patcher_create_person_db.start()
        self.mock_update_person_db = self.patcher_update_person_db.start()
        self.mock_get_person_db = self.patcher_get_person_db.start()
        self.mock_delete_person_db = self.patcher_delete_person_db.start()
        self.mock_upload_profile_picture_db = self.patcher_upload_profile_picture_db.start()
        self.mock_get_media_for_entity_db = self.patcher_get_media_for_entity_db.start()
        self.mock_get_events_for_person_db = self.patcher_get_events_for_person_db.start()
        self.mock_get_all_people_db = self.patcher_get_all_people_db.start() # Start patch
        
        self.mock_require_tree_access_decorator = self.patcher_require_tree_access.start()
        self.mock_require_auth_decorator = self.patcher_require_auth.start()
        
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)
        self.mock_require_auth_decorator.side_effect = lambda func: func

        # Default return for get_all_people_db
        self.mock_get_all_people_db.return_value = {"items": [], "total_items": 0, "page": 1, "per_page": 10, "total_pages": 0}


    def tearDown(self):
        self.patcher_create_person_db.stop()
        self.patcher_update_person_db.stop()
        self.patcher_get_person_db.stop()
        self.patcher_delete_person_db.stop()
        self.patcher_upload_profile_picture_db.stop()
        self.patcher_get_media_for_entity_db.stop()
        self.patcher_get_events_for_person_db.stop() 
        self.patcher_get_all_people_db.stop() # Stop patch
        self.patcher_require_tree_access.stop()
        self.patcher_require_auth.stop()
        patch.stopall() # Stop any other patches started in tests

    # --- Tests for GET /api/people with new filters ---
    def test_get_all_people_with_search_term_filter(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                client.get('/api/people?search_term=John')
        
        self.mock_get_all_people_db.assert_called_once()
        args, kwargs = self.mock_get_all_people_db.call_args
        expected_filters = {'search_term': 'John'}
        # Check if expected_filters is a subset of the actual filters passed
        self.assertTrue(expected_filters.items() <= kwargs['filters'].items())


    def test_get_all_people_with_date_range_filters(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                client.get('/api/people?birth_start_date=1990-01-01&death_end_date=2020-12-31')

        self.mock_get_all_people_db.assert_called_once()
        args, kwargs = self.mock_get_all_people_db.call_args
        expected_filters = {
            'birth_date_range_start': '1990-01-01',
            'death_date_range_end': '2020-12-31'
        }
        self.assertTrue(expected_filters.items() <= kwargs['filters'].items())

    def test_get_all_people_with_custom_fields_filter(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                client.get('/api/people?custom_fields_key=occupation&custom_fields_value=engineer')
        
        self.mock_get_all_people_db.assert_called_once()
        args, kwargs = self.mock_get_all_people_db.call_args
        expected_filters = {
            'custom_fields_key': 'occupation',
            'custom_fields_value': 'engineer'
        }
        self.assertTrue(expected_filters.items() <= kwargs['filters'].items())

    def test_get_all_people_with_custom_fields_partial_filter_ignored(self):
        # Test that if only custom_fields_key is provided, the filter is not applied (as per blueprint logic)
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                client.get('/api/people?custom_fields_key=occupation')
        
        self.mock_get_all_people_db.assert_called_once()
        args, kwargs = self.mock_get_all_people_db.call_args
        # Ensure custom_fields_key and _value are NOT in filters if only one is provided
        self.assertNotIn('custom_fields_key', kwargs['filters'])
        self.assertNotIn('custom_fields_value', kwargs['filters'])


    @patch('blueprints.people.get_all_people_db', side_effect=get_all_people_db) # Use actual service for this test
    def test_get_all_people_invalid_date_format_raises_400(self, mock_actual_service_call):
        # This test expects the service layer to raise an HTTPException (abort 400)
        # So, we don't fully mock get_all_people_db, or make its mock raise the error.
        # Here, we let the actual service be called but mock the DB session it uses.
        
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock() # Service will use g.db
                g.active_tree_id = self.test_tree_id
                
                # Mock the query and paginate_query within the actual service for this specific test
                with patch('services.person_service.db.query') as mock_query, \
                     patch('services.person_service.paginate_query') as mock_paginate:
                    mock_query.return_value.filter.return_value = MagicMock() # Mock the chain
                    mock_paginate.return_value = {"items": []} # Return valid pagination
                    
                    response = client.get('/api/people?birth_start_date=invalid-date-format')

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid date format", response.json['message']['details']['birth_date_range_start'])


    def test_get_all_people_combined_filters(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                client.get('/api/people?search_term=Doe&is_living=true&birth_start_date=1980-01-01&gender=female')

        self.mock_get_all_people_db.assert_called_once()
        args, kwargs = self.mock_get_all_people_db.call_args
        expected_filters = {
            'search_term': 'Doe',
            'is_living': True,
            'birth_date_range_start': '1980-01-01',
            'gender': 'female'
        }
        self.assertTrue(expected_filters.items() <= kwargs['filters'].items())


    # --- Keep existing tests below, ensure they still pass with setup changes ---
    def test_create_person_endpoint_with_new_fields(self):
        person_data_to_send = { "first_name": "ApiTest", "last_name": "User", "profile_picture_url": "http://api.example.com/profile.jpg", "custom_fields": {"department": "api_dev"}}
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
    
    def test_update_person_endpoint_with_new_fields(self):
        update_data_to_send = {"profile_picture_url": "http://updated.com/new_profile.png", "custom_fields": {"status": "promoted"}}
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
                response = client.post( f'/api/people/{self.test_person_id}/profile_picture', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)

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

if __name__ == '__main__':
    unittest.main()
