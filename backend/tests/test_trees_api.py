import unittest
import uuid
import io
from unittest.mock import patch, MagicMock, ANY

from flask import Flask, g, session
from werkzeug.exceptions import BadRequest, InternalServerError, Forbidden, NotFound

# Adjust imports based on your project structure
from blueprints.trees import trees_bp 

class TestTreesAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'super_secret_key_for_testing_session_trees'
        self.app.register_blueprint(trees_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.test_user_id = str(uuid.uuid4())
        self.test_tree_id = str(uuid.uuid4())

        # Patch service functions used by the trees blueprint
        self.patcher_create_tree_db = patch('blueprints.trees.create_tree_db')
        self.patcher_get_user_trees_db = patch('blueprints.trees.get_user_trees_db')
        self.patcher_set_active_tree_in_session = patch('blueprints.trees.Tree') # Assuming direct model usage for set_active_tree
        self.patcher_get_tree_data_for_viz_db = patch('blueprints.trees.get_tree_data_for_visualization_db')
        self.patcher_upload_tree_cover_image_db = patch('blueprints.trees.upload_tree_cover_image_db')
        self.patcher_get_media_for_entity_db = patch('blueprints.trees.get_media_for_entity_db')


        self.mock_create_tree_db = self.patcher_create_tree_db.start()
        self.mock_get_user_trees_db = self.patcher_get_user_trees_db.start()
        self.mock_tree_model_for_set_active = self.patcher_set_active_tree_in_session.start()
        self.mock_get_tree_data_for_viz_db = self.patcher_get_tree_data_for_viz_db.start()
        self.mock_upload_tree_cover_image_db = self.patcher_upload_tree_cover_image_db.start()
        self.mock_get_media_for_entity_db = self.patcher_get_media_for_entity_db.start()


        # Patch decorators
        self.patcher_require_auth = patch('blueprints.trees.require_auth')
        self.patcher_require_tree_access = patch('blueprints.trees.require_tree_access')
        
        self.mock_require_auth_decorator = self.patcher_require_auth.start()
        self.mock_require_tree_access_decorator = self.patcher_require_tree_access.start()

        self.mock_require_auth_decorator.side_effect = lambda func: func
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)
        
        # Mock for limiter if it's actively applied to tested endpoints
        self.patcher_limiter_limit = patch('blueprints.trees.limiter.limit', return_value=lambda func: func)
        self.mock_limiter_limit = self.patcher_limiter_limit.start()


    def tearDown(self):
        self.patcher_create_tree_db.stop()
        self.patcher_get_user_trees_db.stop()
        self.patcher_set_active_tree_in_session.stop()
        self.patcher_get_tree_data_for_viz_db.stop()
        self.patcher_upload_tree_cover_image_db.stop()
        self.patcher_get_media_for_entity_db.stop()
        self.patcher_require_auth.stop()
        self.patcher_require_tree_access.stop()
        self.patcher_limiter_limit.stop()


    # --- Tests for Tree Cover Image Upload Endpoint ---
    def test_upload_tree_cover_image_success(self):
        mock_response_data = {"id": self.test_tree_id, "cover_image_url": "s3_key_for_cover.png"}
        self.mock_upload_tree_cover_image_db.return_value = mock_response_data
        
        data = {'file': (io.BytesIO(b"fake cover image data"), 'cover.png')}

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                # active_tree_id might be needed by @require_tree_access if it's used on this endpoint
                # For now, the endpoint itself doesn't use g.active_tree_id directly for this operation.
                sess['active_tree_id'] = self.test_tree_id 
            
            with self.app.app_context():
                g.db = MagicMock() # Mock db on g
                # g.active_tree_id = self.test_tree_id # If @require_tree_access decorator needs it
                response = client.post(
                    f'/api/trees/{self.test_tree_id}/cover_image', # Adjusted URL prefix
                    data=data,
                    content_type='multipart/form-data'
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)
        self.mock_upload_tree_cover_image_db.assert_called_once_with(
            db=g.db,
            tree_id=uuid.UUID(self.test_tree_id),
            user_id=uuid.UUID(self.test_user_id),
            file_stream=ANY,
            filename='cover.png',
            content_type=ANY 
        )

    def test_upload_tree_cover_image_no_file_part(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                response = client.post(f'/api/trees/{self.test_tree_id}/cover_image', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("No file part", response.json['message'])

    def test_upload_tree_cover_image_no_selected_file(self):
        data = {'file': (io.BytesIO(b""), '')}
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
        self.assertEqual(response.status_code, 400)
        self.assertIn("No selected file", response.json['message'])

    def test_upload_tree_cover_image_service_failure(self):
        self.mock_upload_tree_cover_image_db.side_effect = InternalServerError(description="S3 is having a nap")
        data = {'file': (io.BytesIO(b"fake cover data"), 'cover.png')}
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
        self.assertEqual(response.status_code, 500)
        self.assertIn("S3 is having a nap", response.json['message'])

    def test_upload_tree_cover_image_service_auth_failure(self):
        self.mock_upload_tree_cover_image_db.side_effect = Forbidden(description="User not tree owner")
        data = {'file': (io.BytesIO(b"fake cover data"), 'cover.png')}
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id # User is not owner (mocked service will raise)
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                response = client.post(
                    f'/api/trees/{self.test_tree_id}/cover_image',
                    data=data, content_type='multipart/form-data'
                )
        self.assertEqual(response.status_code, 403)
        self.assertIn("User not tree owner", response.json['message'])

    # --- Tests for Get Tree Media Endpoint ---
    def test_get_tree_media_endpoint_success(self):
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
        self.mock_get_media_for_entity_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_tree_id), "Tree", uuid.UUID(self.test_tree_id),
            1, 5, "created_at", "desc" 
        )

    def test_get_tree_media_endpoint_service_failure(self):
        self.mock_get_media_for_entity_db.side_effect = InternalServerError(description="Database hiccup")
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.get(f'/api/trees/{self.test_tree_id}/media')

        self.assertEqual(response.status_code, 500)
        self.assertIn("Database hiccup", response.json['message'])


if __name__ == '__main__':
    unittest.main()
