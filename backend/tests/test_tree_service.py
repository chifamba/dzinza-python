import unittest
from unittest.mock import MagicMock, patch, ANY
import uuid
import io

from sqlalchemy.orm import Session as DBSession
from werkzeug.exceptions import HTTPException, Forbidden, BadRequest

from models import Tree, TreePrivacySettingEnum, PrivacyLevelEnum, TreeAccess # Added TreePrivacySettingEnum, PrivacyLevelEnum, TreeAccess
from services.tree_service import (
    upload_tree_cover_image_db, 
    create_tree_db, # Added for testing
    update_tree_db  # Added for testing
)
from config import config # For S3 bucket name etc.

class TestTreeService(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock(spec=DBSession)
        self.test_user_id = uuid.uuid4()
        self.test_tree_id = uuid.uuid4()
        
        self.mock_s3_client = MagicMock()
        # Patch S3 related for cover image, might not be needed for all tree tests
        self.patcher_get_storage_client = patch('services.tree_service.get_storage_client', return_value=self.mock_s3_client)
        self.patcher_create_bucket = patch('services.tree_service.create_bucket_if_not_exists', return_value=True)
        
        self.patcher_get_or_404 = patch('services.tree_service._get_or_404') # Used by update_tree_db

        self.mock_get_storage_client = self.patcher_get_storage_client.start()
        self.mock_create_bucket = self.patcher_create_bucket.start()
        self.mock_get_or_404 = self.patcher_get_or_404.start()

    def tearDown(self):
        self.patcher_get_storage_client.stop()
        self.patcher_create_bucket.stop()
        self.patcher_get_or_404.stop()
        patch.stopall() # Stop any other patches started in tests

    # --- Tests for create_tree_db ---
    @patch('services.tree_service.Tree') # Mock the Tree model
    @patch('services.tree_service.TreeAccess') # Mock TreeAccess
    def test_create_tree_db_default_privacy(self, MockTreeAccess, MockTree):
        mock_tree_instance = MockTree.return_value
        mock_tree_instance.id = self.test_tree_id # Ensure the instance has an ID for TreeAccess
        mock_tree_instance.to_dict.return_value = {"id": str(self.test_tree_id), "name": "Test Tree"}

        tree_data = {"name": "Test Tree"} # No privacy_setting provided
        
        created_tree = create_tree_db(self.mock_db_session, self.test_user_id, tree_data)

        MockTree.assert_called_once()
        args, kwargs = MockTree.call_args
        self.assertEqual(kwargs.get('name'), "Test Tree")
        self.assertEqual(kwargs.get('privacy_setting'), TreePrivacySettingEnum.PRIVATE) # Check default

        MockTreeAccess.assert_called_once_with(
            tree_id=self.test_tree_id, user_id=self.test_user_id, 
            access_level='admin', granted_by=self.test_user_id
        )
        self.mock_db_session.add.assert_any_call(mock_tree_instance)
        self.mock_db_session.add.assert_any_call(MockTreeAccess.return_value)
        self.mock_db_session.commit.assert_called_once()
        self.assertEqual(created_tree, mock_tree_instance.to_dict.return_value)

    @patch('services.tree_service.Tree')
    @patch('services.tree_service.TreeAccess')
    def test_create_tree_db_with_public_privacy(self, MockTreeAccess, MockTree):
        MockTree.return_value.id = self.test_tree_id
        tree_data = {"name": "Public Tree", "privacy_setting": TreePrivacySettingEnum.PUBLIC.value}
        
        create_tree_db(self.mock_db_session, self.test_user_id, tree_data)

        MockTree.assert_called_once()
        args, kwargs = MockTree.call_args
        self.assertEqual(kwargs.get('privacy_setting'), TreePrivacySettingEnum.PUBLIC)

    def test_create_tree_db_invalid_privacy_setting(self):
        tree_data = {"name": "Invalid Tree", "privacy_setting": "INVALID_VALUE"}
        with self.assertRaises(HTTPException) as context:
            create_tree_db(self.mock_db_session, self.test_user_id, tree_data)
        self.assertEqual(context.exception.code, 400)
        self.assertIn("Invalid privacy_setting", context.exception.description)

    # --- Tests for update_tree_db ---
    def test_update_tree_db_privacy_setting(self):
        mock_tree = MagicMock(spec=Tree)
        self.mock_get_or_404.return_value = mock_tree
        mock_tree.to_dict.return_value = {"id": str(self.test_tree_id), "privacy_setting": "PUBLIC"}

        update_data = {"privacy_setting": TreePrivacySettingEnum.PUBLIC.value}
        updated_tree = update_tree_db(self.mock_db_session, self.test_tree_id, update_data)

        self.mock_get_or_404.assert_called_once_with(self.mock_db_session, Tree, self.test_tree_id)
        self.assertEqual(mock_tree.privacy_setting, TreePrivacySettingEnum.PUBLIC)
        self.mock_db_session.commit.assert_called_once()
        self.assertEqual(updated_tree, mock_tree.to_dict.return_value)

    def test_update_tree_db_invalid_privacy_setting(self):
        mock_tree = MagicMock(spec=Tree)
        self.mock_get_or_404.return_value = mock_tree
        update_data = {"privacy_setting": "NOT_VALID"}
        
        with self.assertRaises(HTTPException) as context:
            update_tree_db(self.mock_db_session, self.test_tree_id, update_data)
        self.assertEqual(context.exception.code, 400)
        self.assertIn("Invalid value: NOT_VALID", context.exception.description['details']['privacy_setting'])


    # --- Existing tests for upload_tree_cover_image_db ---
    @patch('services.tree_service.secure_filename', side_effect=lambda x: x) 
    def test_upload_tree_cover_image_db_success_new_image(self, mock_secure_filename):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_user_id 
        mock_tree.cover_image_url = None 
        mock_tree.to_dict.return_value = {"id": str(self.test_tree_id), "cover_image_url": "new_cover.jpg"}
        # self.mock_get_or_404 was already started in setUp, ensure it's configured for this specific call
        self.mock_get_or_404.reset_mock() # Reset from potential previous calls in other tests
        self.mock_get_or_404.return_value = mock_tree


        file_stream = io.BytesIO(b"fake cover data")
        filename = "cover.jpg"
        content_type = "image/jpeg"

        result = upload_tree_cover_image_db(
            self.mock_db_session, self.test_tree_id, self.test_user_id,
            file_stream, filename, content_type
        )

        self.mock_get_or_404.assert_called_once_with(self.mock_db_session, Tree, self.test_tree_id)
        self.mock_s3_client.upload_fileobj.assert_called_once_with(
            file_stream, config.OBJECT_STORAGE_BUCKET_NAME, ANY, ExtraArgs={'ContentType': content_type}
        )
        new_object_key = self.mock_s3_client.upload_fileobj.call_args[0][2]
        self.assertTrue(filename in new_object_key)
        self.assertEqual(mock_tree.cover_image_url, new_object_key)
        
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(mock_tree)
        self.assertEqual(result, mock_tree.to_dict.return_value)
        self.mock_s3_client.delete_object.assert_not_called()

    @patch('services.tree_service.secure_filename', side_effect=lambda x: x)
    def test_upload_tree_cover_image_db_replace_existing(self, mock_secure_filename):
        old_key = f"tree_cover_images/{self.test_tree_id}/old_cover.png"
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_user_id
        mock_tree.cover_image_url = old_key
        self.mock_get_or_404.reset_mock()
        self.mock_get_or_404.return_value = mock_tree

        file_stream = io.BytesIO(b"new fake cover data")
        new_filename = "new_cover.png"

        upload_tree_cover_image_db(
            self.mock_db_session, self.test_tree_id, self.test_user_id,
            file_stream, new_filename, "image/png"
        )

        self.mock_s3_client.upload_fileobj.assert_called_once()
        self.mock_s3_client.delete_object.assert_called_once_with(
            Bucket=config.OBJECT_STORAGE_BUCKET_NAME, Key=old_key
        )
        self.assertNotEqual(mock_tree.cover_image_url, old_key)
        self.assertTrue(new_filename in mock_tree.cover_image_url)
        self.mock_db_session.commit.assert_called_once()

    def test_upload_tree_cover_image_db_unauthorized_user(self):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.created_by = uuid.uuid4() 
        self.mock_get_or_404.reset_mock()
        self.mock_get_or_404.return_value = mock_tree

        with self.assertRaises(HTTPException) as context:
            upload_tree_cover_image_db(
                self.mock_db_session, self.test_tree_id, self.test_user_id,
                io.BytesIO(b"data"), "cover.jpg", "image/jpeg"
            )
        self.assertEqual(context.exception.code, 403)

    def test_upload_tree_cover_image_db_s3_upload_failure(self):
        mock_tree = MagicMock(spec=Tree, created_by=self.test_user_id, cover_image_url=None)
        self.mock_get_or_404.reset_mock()
        self.mock_get_or_404.return_value = mock_tree
        self.mock_s3_client.upload_fileobj.side_effect = S3UploadFailedError("S3 upload epic fail")

        with self.assertRaises(HTTPException) as context:
            upload_tree_cover_image_db(
                self.mock_db_session, self.test_tree_id, self.test_user_id,
                io.BytesIO(b"data"), "fail.jpg", "image/jpeg"
            )
        self.assertEqual(context.exception.code, 500)
        self.mock_db_session.rollback.assert_called_once()

    @patch('services.tree_service.secure_filename', side_effect=lambda x: x)
    @patch('services.tree_service.logger') 
    def test_upload_tree_cover_image_db_s3_old_delete_fails_logs_and_continues(self, mock_logger, mock_secure_filename):
        old_key = "tree_cover_images/some_old_key.jpg"
        mock_tree = MagicMock(spec=Tree, id=self.test_tree_id, created_by=self.test_user_id, cover_image_url=old_key)
        self.mock_get_or_404.reset_mock()
        self.mock_get_or_404.return_value = mock_tree
        
        self.mock_s3_client.delete_object.side_effect = ClientError({"Error": {"Code": "500", "Message": "Delete failed"}}, "delete_object")

        file_stream = io.BytesIO(b"new data for tree")
        new_filename = "new_tree_cover.jpg"
        
        upload_tree_cover_image_db(
            self.mock_db_session, self.test_tree_id, self.test_user_id,
            file_stream, new_filename, "image/jpeg"
        )
        
        mock_logger.error.assert_any_call(
            f"Failed to delete old tree cover image {old_key} from S3.",
            error=ANY, tree_id=self.test_tree_id
        )
        self.mock_s3_client.upload_fileobj.assert_called_once() 
        self.assertNotEqual(mock_tree.cover_image_url, old_key) 
        self.mock_db_session.commit.assert_called_once() 

if __name__ == '__main__':
    unittest.main()
