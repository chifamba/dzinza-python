import unittest
from unittest.mock import MagicMock, patch, ANY
import uuid
import io

from sqlalchemy.orm import Session as DBSession
from werkzeug.exceptions import HTTPException, Forbidden
from botocore.exceptions import S3UploadFailedError, ClientError

from models import Tree # Assuming Tree model exists
from services.tree_service import upload_tree_cover_image_db
from config import config # For S3 bucket name etc.

class TestTreeService(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock(spec=DBSession)
        self.test_user_id = uuid.uuid4()
        self.test_tree_id = uuid.uuid4()
        
        self.mock_s3_client = MagicMock()
        self.patcher_get_storage_client = patch('services.tree_service.get_storage_client', return_value=self.mock_s3_client)
        self.patcher_create_bucket = patch('services.tree_service.create_bucket_if_not_exists', return_value=True)
        self.patcher_get_or_404 = patch('services.tree_service._get_or_404')

        self.mock_get_storage_client = self.patcher_get_storage_client.start()
        self.mock_create_bucket = self.patcher_create_bucket.start()
        self.mock_get_or_404 = self.patcher_get_or_404.start()

    def tearDown(self):
        self.patcher_get_storage_client.stop()
        self.patcher_create_bucket.stop()
        self.patcher_get_or_404.stop()

    @patch('services.tree_service.secure_filename', side_effect=lambda x: x) # Mock secure_filename
    def test_upload_tree_cover_image_db_success_new_image(self, mock_secure_filename):
        mock_tree = MagicMock(spec=Tree)
        mock_tree.id = self.test_tree_id
        mock_tree.created_by = self.test_user_id # User is owner
        mock_tree.cover_image_url = None # No existing image
        mock_tree.to_dict.return_value = {"id": str(self.test_tree_id), "cover_image_url": "new_cover.jpg"}
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
        mock_tree.created_by = uuid.uuid4() # Different user
        self.mock_get_or_404.return_value = mock_tree

        with self.assertRaises(HTTPException) as context:
            upload_tree_cover_image_db(
                self.mock_db_session, self.test_tree_id, self.test_user_id,
                io.BytesIO(b"data"), "cover.jpg", "image/jpeg"
            )
        self.assertEqual(context.exception.code, 403) # Forbidden

    def test_upload_tree_cover_image_db_s3_upload_failure(self):
        mock_tree = MagicMock(spec=Tree, created_by=self.test_user_id, cover_image_url=None)
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
    @patch('services.tree_service.logger') # Patch logger in the tree_service module
    def test_upload_tree_cover_image_db_s3_old_delete_fails_logs_and_continues(self, mock_logger, mock_secure_filename):
        old_key = "tree_cover_images/some_old_key.jpg"
        mock_tree = MagicMock(spec=Tree, id=self.test_tree_id, created_by=self.test_user_id, cover_image_url=old_key)
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
        self.mock_s3_client.upload_fileobj.assert_called_once() # New upload should still happen
        self.assertNotEqual(mock_tree.cover_image_url, old_key) # URL should be updated
        self.mock_db_session.commit.assert_called_once() # Commit should still happen

if __name__ == '__main__':
    unittest.main()
