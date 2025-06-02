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
from services.person_service import get_all_people_db, update_person_order_db # Import for actual service call test and new service

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
        self.patcher_update_person_order_db = patch('blueprints.people.update_person_order_db') # Patch for new endpoint


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
        self.mock_update_person_order_db = self.patcher_update_person_order_db.start() # Start patch for new service
        
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
        self.patcher_update_person_order_db.stop() # Stop patch for new service
        self.patcher_require_tree_access.stop()
        self.patcher_require_auth.stop()
        patch.stopall() # Stop any other patches started in tests

    # --- Tests for PUT /api/people/order ---
    def test_update_people_order_success(self):
        self.mock_update_person_order_db.return_value = True
        order_payload = [
            {"id": str(uuid.uuid4()), "display_order": 1},
            {"id": str(uuid.uuid4()), "display_order": 0},
        ]
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.put('/api/people/order', json=order_payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Person order updated successfully."})
        self.mock_update_person_order_db.assert_called_once_with(
            db=g.db,
            tree_id=self.test_tree_id,
            persons_data=order_payload,
            actor_user_id=uuid.UUID(self.test_user_id)
        )

    def test_update_people_order_invalid_payload_not_a_list(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.put('/api/people/order', json={"not": "a list"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Request body must be a list", response.json['description'])

    def test_update_people_order_service_returns_false(self):
        self.mock_update_person_order_db.return_value = False # Simulate service failure
        order_payload = [{"id": str(uuid.uuid4()), "display_order": 0}]
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.put('/api/people/order', json=order_payload)
        self.assertEqual(response.status_code, 500) # As per blueprint's current error handling
        self.assertIn("Failed to update person order", response.json['description'])

    def test_update_people_order_service_raises_httpexception(self):
        # Simulate service raising BadRequest (e.g., person not found)
        self.mock_update_person_order_db.side_effect = BadRequest("Person not found in tree.")
        order_payload = [{"id": str(uuid.uuid4()), "display_order": 0}]
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.put('/api/people/order', json=order_payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Person not found in tree.", response.json['description'])

    def test_update_people_order_no_edit_permission(self):
        # Simulate require_tree_access decorator raising Forbidden
        self.mock_require_tree_access_decorator.side_effect = lambda level: (_ for _ in ()).throw(Forbidden("User does not have edit access.")) if level == 'edit' else (lambda func: func)

        order_payload = [{"id": str(uuid.uuid4()), "display_order": 0}]
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.put('/api/people/order', json=order_payload)

        self.assertEqual(response.status_code, 403)
        self.assertIn("User does not have edit access.", response.json['description'])
        # Restore default side_effect for other tests
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)


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
    @patch('services.person_service.paginate_query') # Mock paginate_query at service level
    @patch('services.person_service.db') # Mock db at service level
    def test_get_all_people_invalid_date_format_raises_400(self, mock_db_in_service, mock_paginate_query_in_service):
        # This test needs to ensure that the actual get_all_people_db service function is called,
        # but its internal DB interactions are controlled.
        # We patch get_all_people_db at the blueprint level to use the *actual* service function.
        
        # Temporarily stop the general mock of get_all_people_db for this specific test
        self.patcher_get_all_people_db.stop()

        # Configure mocks for the *actual* service's dependencies
        # The actual service will attempt db.query(...).join(...).filter(...)
        # We need to mock this chain.
        mock_query_obj = MagicMock()
        mock_join_obj = MagicMock()
        mock_filter_obj = MagicMock()

        mock_db_in_service.query.return_value = mock_query_obj
        mock_query_obj.join.return_value = mock_join_obj
        mock_join_obj.filter.return_value = mock_filter_obj # This is what paginate_query will receive

        # paginate_query should return a valid structure even if no items match
        mock_paginate_query_in_service.return_value = {
            "items": [], "total_items": 0, "page": 1,
            "per_page": 10, "total_pages": 0
        }

        response = None
        try:
            with self.client as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = self.test_user_id
                    sess['active_tree_id'] = self.test_tree_id
                with self.app.app_context():
                    g.db = mock_db_in_service # Ensure g.db is the service-level mock for the endpoint context
                    g.active_tree_id = self.test_tree_id
                    
                    # Call the endpoint which should now use the actual service due to stopped patcher
                    # The blueprint decorator will still pass g.db (which is mock_db_in_service)
                    # to the actual get_all_people_db service function.
                    with patch('blueprints.people.get_all_people_db', side_effect=get_all_people_db) as temp_patch:
                         response = client.get('/api/people?birth_start_date=invalid-date-format')

            self.assertIsNotNone(response, "Response was not captured.")
            self.assertEqual(response.status_code, 400)
            # The service aborts with a specific structure
            self.assertIn("Validation failed", response.json['description']['message'])
            self.assertIn("Invalid date format", response.json['description']['details']['birth_date_range_start'])
        finally:
            # Restart the general mock for other tests
            self.mock_get_all_people_db = self.patcher_get_all_people_db.start()
            self.mock_get_all_people_db.return_value = {"items": [], "total_items": 0, "page": 1, "per_page": 10, "total_pages": 0} # Restore default mock behavior


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
