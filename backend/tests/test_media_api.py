import unittest
import uuid
import io
from unittest.mock import patch, MagicMock, ANY

from flask import Flask, g, session
from werkzeug.exceptions import BadRequest, InternalServerError, Forbidden, NotFound

# Adjust imports based on your project structure
from blueprints.media import media_bp # The blueprint to test

class TestMediaAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'super_secret_key_for_testing_session_media'
        self.app.register_blueprint(media_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.test_user_id = str(uuid.uuid4())
        self.test_tree_id = str(uuid.uuid4())
        self.test_media_id = str(uuid.uuid4())
        self.test_entity_id = str(uuid.uuid4()) # For linked_entity_id

        # Patch service functions used by the media blueprint
        self.patcher_upload_media_item_db = patch('blueprints.media.upload_media_item_db')
        self.patcher_delete_media_item_db = patch('blueprints.media.delete_media_item_db')
        self.patcher_get_media_item_db = patch('blueprints.media.get_media_item_db')
        self.patcher_get_media_for_entity_db = patch('blueprints.media.get_media_for_entity_db')

        self.mock_upload_media_item_db = self.patcher_upload_media_item_db.start()
        self.mock_delete_media_item_db = self.patcher_delete_media_item_db.start()
        self.mock_get_media_item_db = self.patcher_get_media_item_db.start()
        self.mock_get_media_for_entity_db = self.patcher_get_media_for_entity_db.start()

        # Patch decorators
        self.patcher_require_auth = patch('blueprints.media.require_auth')
        self.patcher_require_tree_access = patch('blueprints.media.require_tree_access')
        
        self.mock_require_auth_decorator = self.patcher_require_auth.start()
        self.mock_require_tree_access_decorator = self.patcher_require_tree_access.start()

        self.mock_require_auth_decorator.side_effect = lambda func: func
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)

    def tearDown(self):
        self.patcher_upload_media_item_db.stop()
        self.patcher_delete_media_item_db.stop()
        self.patcher_get_media_item_db.stop()
        self.patcher_get_media_for_entity_db.stop()
        self.patcher_require_auth.stop()
        self.patcher_require_tree_access.stop()

    # --- Test Upload Media Item Endpoint ---
    def test_upload_media_item_success(self):
        mock_response_data = {"id": self.test_media_id, "file_name": "test_upload.jpg"}
        self.mock_upload_media_item_db.return_value = mock_response_data
        
        data = {
            'file': (io.BytesIO(b"fake file data for upload"), 'test_upload.jpg'),
            'linked_entity_type': 'Person',
            'linked_entity_id': self.test_entity_id,
            'caption': 'A test caption for upload'
        }

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id # Ensure g.active_tree_id is string for blueprint
                response = client.post('/api/media', data=data, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, mock_response_data)
        self.mock_upload_media_item_db.assert_called_once_with(
            db=g.db,
            user_id=uuid.UUID(self.test_user_id),
            tree_id=uuid.UUID(self.test_tree_id),
            linked_entity_type='Person',
            linked_entity_id=uuid.UUID(self.test_entity_id),
            file_stream=ANY,
            filename='test_upload.jpg',
            content_type=ANY,
            caption='A test caption for upload',
            file_type_enum_provided=None 
        )

    def test_upload_media_item_missing_file(self):
        data = { # No 'file' part
            'linked_entity_type': 'Person', 'linked_entity_id': self.test_entity_id
        }
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post('/api/media', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        self.assertIn("No file part", response.json['message'])

    def test_upload_media_item_missing_form_fields(self):
        # Missing linked_entity_type
        data = {'file': (io.BytesIO(b"data"), 'test.jpg'), 'linked_entity_id': self.test_entity_id}
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post('/api/media', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required form field: linked_entity_type", response.json['message'])

    # --- Test Delete Media Item Endpoint ---
    def test_delete_media_item_success(self):
        self.mock_delete_media_item_db.return_value = True
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.delete(f'/api/media/{self.test_media_id}')
        
        self.assertEqual(response.status_code, 204)
        self.mock_delete_media_item_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_media_id), uuid.UUID(self.test_user_id), uuid.UUID(self.test_tree_id)
        )

    def test_delete_media_item_service_failure_forbidden(self):
        self.mock_delete_media_item_db.side_effect = Forbidden(description="Not authorized to delete")
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.delete(f'/api/media/{self.test_media_id}')
        self.assertEqual(response.status_code, 403)
        self.assertIn("Not authorized to delete", response.json['message'])

    # --- Test Get Media Item Endpoint ---
    def test_get_media_item_success(self):
        mock_response_data = {"id": self.test_media_id, "file_name": "detail.png"}
        self.mock_get_media_item_db.return_value = mock_response_data
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/media/{self.test_media_id}')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)
        self.mock_get_media_item_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_media_id), uuid.UUID(self.test_tree_id)
        )

    def test_get_media_item_not_found(self):
        self.mock_get_media_item_db.side_effect = NotFound(description="Media not found here")
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/media/{self.test_media_id}')
        self.assertEqual(response.status_code, 404)
        self.assertIn("Media not found here", response.json['message'])

    # --- Test Get Media For Entity Endpoint ---
    def test_get_media_for_entity_success(self):
        entity_type = "Person"
        mock_response_data = {"items": [{"file_name": "person_pic.jpg"}], "total_items": 1}
        self.mock_get_media_for_entity_db.return_value = mock_response_data
        
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/media/entity/{entity_type}/{self.test_entity_id}?page=1&per_page=10')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)
        self.mock_get_media_for_entity_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_tree_id), entity_type, uuid.UUID(self.test_entity_id),
            1, 10, "created_at", "desc"
        )

if __name__ == '__main__':
    unittest.main()
