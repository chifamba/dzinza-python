import unittest
import uuid
import io
import json # For JSON payloads
from unittest.mock import patch, MagicMock, ANY

from flask import Flask, g, session, jsonify
from werkzeug.exceptions import BadRequest, InternalServerError, Forbidden, NotFound

# Adjust imports based on your project structure
from blueprints.trees import trees_bp 
from models import TreePrivacySettingEnum # For testing privacy_setting

class TestTreesAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'super_secret_key_for_testing_session_trees'
        self.app.register_blueprint(trees_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.test_user_id = str(uuid.uuid4())
        self.test_owner_id = str(uuid.uuid4()) # For testing access by non-owner
        self.test_tree_id = str(uuid.uuid4())

        # Patch service functions used by the trees blueprint
        self.patcher_create_tree_db = patch('blueprints.trees.create_tree_db')
        self.patcher_get_user_trees_db = patch('blueprints.trees.get_user_trees_db')
        
        self.patcher_get_tree_data_for_viz_db = patch('blueprints.trees.get_tree_data_for_visualization_db')
        self.patcher_upload_tree_cover_image_db = patch('blueprints.trees.upload_tree_cover_image_db')
        self.patcher_get_media_for_entity_db = patch('blueprints.trees.get_media_for_entity_db')
        self.patcher_get_events_for_tree_db = patch('blueprints.trees.get_events_for_tree_db') 

        self.mock_create_tree_db = self.patcher_create_tree_db.start()
        self.mock_get_user_trees_db = self.patcher_get_user_trees_db.start()
        self.mock_get_tree_data_for_viz_db = self.patcher_get_tree_data_for_viz_db.start()
        self.mock_upload_tree_cover_image_db = self.patcher_upload_tree_cover_image_db.start()
        self.mock_get_media_for_entity_db = self.patcher_get_media_for_entity_db.start()
        self.mock_get_events_for_tree_db = self.patcher_get_events_for_tree_db.start()

        # Patch decorators
        self.patcher_require_auth = patch('blueprints.trees.require_auth')
        self.patcher_require_tree_access = patch('blueprints.trees.require_tree_access') 
        
        self.mock_require_auth_decorator = self.patcher_require_auth.start()
        self.mock_require_tree_access_decorator = self.patcher_require_tree_access.start()

        self.mock_require_auth_decorator.side_effect = lambda func: func 
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func) 
        
        self.patcher_limiter_limit = patch('blueprints.trees.limiter.limit', return_value=lambda func: func)
        self.mock_limiter_limit = self.patcher_limiter_limit.start()

    def tearDown(self):
        self.patcher_create_tree_db.stop()
        self.patcher_get_user_trees_db.stop()
        self.patcher_get_tree_data_for_viz_db.stop()
        self.patcher_upload_tree_cover_image_db.stop()
        self.patcher_get_media_for_entity_db.stop()
        self.patcher_get_events_for_tree_db.stop()
        self.patcher_require_auth.stop()
        self.patcher_require_tree_access.stop()
        self.patcher_limiter_limit.stop()
        patch.stopall() 

    # --- Tests for POST /api/trees (privacy_setting) ---
    def test_create_tree_with_default_privacy_setting(self):
        tree_payload = {"name": "My Default Private Tree"}
        mock_response_data = {"id": self.test_tree_id, "name": "My Default Private Tree", "privacy_setting": "PRIVATE"}
        self.mock_create_tree_db.return_value = mock_response_data

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
            with self.app.app_context():
                g.db = MagicMock()
                response = client.post('/api/trees', json=tree_payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['privacy_setting'], "PRIVATE")
        self.mock_create_tree_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_user_id), tree_payload
        )

    def test_create_tree_with_explicit_public_privacy_setting(self):
        tree_payload = {"name": "My Public Tree", "privacy_setting": TreePrivacySettingEnum.PUBLIC.value}
        mock_response_data = {"id": self.test_tree_id, **tree_payload}
        self.mock_create_tree_db.return_value = mock_response_data

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
            with self.app.app_context():
                g.db = MagicMock()
                response = client.post('/api/trees', json=tree_payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['privacy_setting'], TreePrivacySettingEnum.PUBLIC.value)
        self.mock_create_tree_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_user_id), tree_payload
        )

    def test_create_tree_with_invalid_privacy_setting(self):
        tree_payload = {"name": "Invalid Privacy Tree", "privacy_setting": "SOMETHING_ELSE"}
        self.mock_create_tree_db.side_effect = BadRequest(description="Invalid privacy_setting")

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
            with self.app.app_context():
                g.db = MagicMock()
                response = client.post('/api/trees', json=tree_payload)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid privacy_setting", response.json['message'])

    # --- Tests for require_tree_access with privacy_setting ---
    @patch('blueprints.trees.require_tree_access', wraps=require_tree_access) 
    @patch('decorators.models.Tree') 
    @patch('decorators.models.TreeAccess') 
    def test_get_tree_data_public_tree_non_owner_viewer(self, MockTreeAccessModel, MockTreeModel, mock_actual_decorator):
        self.mock_get_tree_data_for_viz_db.return_value = {"nodes": [], "links": []} 
        
        mock_tree_instance = MockTreeModel()
        mock_tree_instance.id = uuid.UUID(self.test_tree_id)
        mock_tree_instance.created_by = self.test_owner_id 
        mock_tree_instance.privacy_setting = TreePrivacySettingEnum.PUBLIC

        with self.app.test_request_context(f'/api/tree_data'): 
            with self.client as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = self.test_user_id 
                    sess['active_tree_id'] = self.test_tree_id 
                
                g.db = MagicMock()
                g.db.query(MockTreeModel).filter(MockTreeModel.id == uuid.UUID(self.test_tree_id)).one_or_none.return_value = mock_tree_instance
                g.db.query(MockTreeAccessModel).filter(ANY).one_or_none.return_value = None 

                response = client.get(f'/api/tree_data') 
        
        self.assertEqual(response.status_code, 200)
        self.mock_get_tree_data_for_viz_db.assert_called_once()

    @patch('blueprints.trees.require_tree_access', wraps=require_tree_access)
    @patch('decorators.models.Tree') 
    @patch('decorators.models.TreeAccess')
    def test_get_tree_data_private_tree_non_owner_no_access_fails(self, MockTreeAccessModel, MockTreeModel, mock_actual_decorator):
        mock_tree_instance = MockTreeModel()
        mock_tree_instance.id = uuid.UUID(self.test_tree_id)
        mock_tree_instance.created_by = self.test_owner_id
        mock_tree_instance.privacy_setting = TreePrivacySettingEnum.PRIVATE

        with self.app.test_request_context(f'/api/tree_data'):
            with self.client as client:
                with client.session_transaction() as sess:
                    sess['user_id'] = self.test_user_id
                    sess['active_tree_id'] = self.test_tree_id
                
                g.db = MagicMock()
                g.db.query(MockTreeModel).filter(MockTreeModel.id == uuid.UUID(self.test_tree_id)).one_or_none.return_value = mock_tree_instance
                g.db.query(MockTreeAccessModel).filter(ANY).one_or_none.return_value = None

                response = client.get(f'/api/tree_data')
        
        self.assertEqual(response.status_code, 403) 

    def test_upload_tree_cover_image_success(self):
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func) 

        mock_response_data = {"id": self.test_tree_id, "cover_image_url": "s3_key_for_cover.png"}
        self.mock_upload_tree_cover_image_db.return_value = mock_response_data
        data = {'file': (io.BytesIO(b"fake cover image data"), 'cover.png')}

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id 
            with self.app.app_context():
                g.db = MagicMock()
                response = client.post(
                    f'/api/trees/{self.test_tree_id}/cover_image',
                    data=data, content_type='multipart/form-data'
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)

    def test_get_tree_media_endpoint_success(self):
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func) 

        mock_media_list = {"items": [{"id": str(uuid.uuid4()), "file_name": "tree_media.jpg"}]}
        self.mock_get_media_for_entity_db.return_value = mock_media_list

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id 
                response = client.get(f'/api/trees/{self.test_tree_id}/media?page=1&per_page=5')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_media_list)

    # --- Tests for /api/trees/{tree_id}/events endpoint ---
    def test_get_tree_events_endpoint_success(self):
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func) 

        mock_events_list = {"items": [{"id": str(uuid.uuid4()), "event_type": "FOUNDING"}]}
        self.mock_get_events_for_tree_db.return_value = mock_events_list

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id # Ensure g.active_tree_id is set as string
                response = client.get(f'/api/trees/{self.test_tree_id}/events?page=1&event_type=FOUNDING')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_events_list)
        self.mock_get_events_for_tree_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_tree_id), 1, ANY, "date", "asc", filters={"event_type": "FOUNDING"}
        )

    def test_get_tree_events_endpoint_service_failure(self):
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)
        self.mock_get_events_for_tree_db.side_effect = InternalServerError(description="Tree Events DB error")
        
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/trees/{self.test_tree_id}/events')

        self.assertEqual(response.status_code, 500)
        self.assertIn("Tree Events DB error", response.json['message'])


if __name__ == '__main__':
    unittest.main()
