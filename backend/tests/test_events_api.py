import unittest
import uuid
import json
from unittest.mock import patch, MagicMock, ANY

from flask import Flask, g, session
from werkzeug.exceptions import BadRequest, NotFound, Forbidden, InternalServerError

# Adjust imports based on your project structure
from blueprints.events import events_bp 

class TestEventsAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'super_secret_key_for_testing_session_events'
        self.app.register_blueprint(events_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.test_user_id = str(uuid.uuid4())
        self.test_tree_id = str(uuid.uuid4())
        self.test_event_id = str(uuid.uuid4())
        self.test_person_id = str(uuid.uuid4()) # For person_id in event

        # Patch service functions
        self.patcher_create_event_db = patch('blueprints.events.create_event_db')
        self.patcher_get_event_db = patch('blueprints.events.get_event_db')
        self.patcher_update_event_db = patch('blueprints.events.update_event_db')
        self.patcher_delete_event_db = patch('blueprints.events.delete_event_db')

        self.mock_create_event_db = self.patcher_create_event_db.start()
        self.mock_get_event_db = self.patcher_get_event_db.start()
        self.mock_update_event_db = self.patcher_update_event_db.start()
        self.mock_delete_event_db = self.patcher_delete_event_db.start()

        # Patch decorators
        self.patcher_require_auth = patch('blueprints.events.require_auth')
        self.patcher_require_tree_access = patch('blueprints.events.require_tree_access')
        
        self.mock_require_auth_decorator = self.patcher_require_auth.start()
        self.mock_require_tree_access_decorator = self.patcher_require_tree_access.start()

        self.mock_require_auth_decorator.side_effect = lambda func: func
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)

    def tearDown(self):
        self.patcher_create_event_db.stop()
        self.patcher_get_event_db.stop()
        self.patcher_update_event_db.stop()
        self.patcher_delete_event_db.stop()
        self.patcher_require_auth.stop()
        self.patcher_require_tree_access.stop()

    # --- Test POST /api/events ---
    def test_create_event_success(self):
        event_payload = {
            "event_type": "BIRTH", "date": "2000-01-01", 
            "person_id": self.test_person_id,
            "description": "Born at home."
        }
        mock_response_data = {"id": self.test_event_id, **event_payload}
        self.mock_create_event_db.return_value = mock_response_data

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id # Ensure g.active_tree_id is string for blueprint
                response = client.post('/api/events', json=event_payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, mock_response_data)
        self.mock_create_event_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_user_id), uuid.UUID(self.test_tree_id), event_payload
        )

    def test_create_event_missing_data(self):
        self.mock_create_event_db.side_effect = BadRequest(description="Request body cannot be empty.")
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post('/api/events', json={}) # Empty payload
        self.assertEqual(response.status_code, 400) # Or as per actual abort in blueprint
        # self.assertIn("Request body cannot be empty", response.json['message'])

    def test_create_event_service_validation_error(self):
        event_payload = {"event_type": "INVALID_TYPE"} # Missing required field or invalid value
        self.mock_create_event_db.side_effect = BadRequest(description={"message": "Validation failed", "details": {"event_type": "Invalid type"}})
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post('/api/events', json=event_payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Validation failed", response.json['message']['message'])


    # --- Test GET /api/events/<uuid:event_id_param> ---
    def test_get_event_success(self):
        mock_response_data = {"id": self.test_event_id, "event_type": "BIRTH"}
        self.mock_get_event_db.return_value = mock_response_data
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/events/{self.test_event_id}')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)
        self.mock_get_event_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_event_id), uuid.UUID(self.test_tree_id)
        )

    def test_get_event_not_found(self):
        self.mock_get_event_db.side_effect = NotFound(description="Event not found")
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/events/{self.test_event_id}')
        self.assertEqual(response.status_code, 404)
        self.assertIn("Event not found", response.json['message'])

    # --- Test PUT /api/events/<uuid:event_id_param> ---
    def test_update_event_success(self):
        update_payload = {"description": "Updated description"}
        mock_response_data = {"id": self.test_event_id, **update_payload}
        self.mock_update_event_db.return_value = mock_response_data
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.put(f'/api/events/{self.test_event_id}', json=update_payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)
        self.mock_update_event_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_event_id), uuid.UUID(self.test_tree_id), update_payload
        )

    # --- Test DELETE /api/events/<uuid:event_id_param> ---
    def test_delete_event_success(self):
        self.mock_delete_event_db.return_value = True
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.delete(f'/api/events/{self.test_event_id}')
        
        self.assertEqual(response.status_code, 204)
        self.mock_delete_event_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_event_id), uuid.UUID(self.test_tree_id)
        )

    def test_delete_event_service_failure(self):
        self.mock_delete_event_db.side_effect = InternalServerError(description="DB constraint error")
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.delete(f'/api/events/{self.test_event_id}')
        self.assertEqual(response.status_code, 500)
        self.assertIn("DB constraint error", response.json['message'])


if __name__ == '__main__':
    unittest.main()
