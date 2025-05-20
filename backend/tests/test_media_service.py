import unittest
from unittest.mock import MagicMock, patch, ANY, call
import uuid
import io
from datetime import datetime

from sqlalchemy.orm import Session as DBSession
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, Forbidden
from botocore.exceptions import S3UploadFailedError, ClientError

# Adjust imports based on your project structure
from models import MediaItem, MediaTypeEnum, Person, Tree # Assuming these models exist
from services.media_service import (
    upload_media_item_db,
    delete_media_item_db,
    get_media_item_db,
    get_media_for_entity_db,
    _infer_file_type # Also test this helper if it's complex
)
from config import config # For accessing config.OBJECT_STORAGE_BUCKET_NAME etc.

class TestMediaService(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock(spec=DBSession)
        self.test_user_id = uuid.uuid4()
        self.test_tree_id = uuid.uuid4()
        self.test_person_id = uuid.uuid4()
        self.test_media_id = uuid.uuid4()
        self.mock_s3_client = MagicMock()

        # Patch external dependencies commonly used
        self.patcher_get_storage_client = patch('services.media_service.get_storage_client', return_value=self.mock_s3_client)
        self.patcher_create_bucket = patch('services.media_service.create_bucket_if_not_exists', return_value=True)
        self.patcher_get_or_404 = patch('services.media_service._get_or_404')
        self.patcher_paginate_query = patch('services.media_service.paginate_query')

        self.mock_get_storage_client = self.patcher_get_storage_client.start()
        self.mock_create_bucket = self.patcher_create_bucket.start()
        self.mock_get_or_404 = self.patcher_get_or_404.start()
        self.mock_paginate_query = self.patcher_paginate_query.start()


    def tearDown(self):
        self.patcher_get_storage_client.stop()
        self.patcher_create_bucket.stop()
        self.patcher_get_or_404.stop()
        self.patcher_paginate_query.stop()

    # --- Tests for _infer_file_type ---
    def test_infer_file_type(self):
        self.assertEqual(_infer_file_type('image/jpeg', 'test.jpg'), MediaTypeEnum.photo)
        self.assertEqual(_infer_file_type('application/pdf', 'doc.pdf'), MediaTypeEnum.document)
        self.assertEqual(_infer_file_type('video/mp4', 'vid.mp4'), MediaTypeEnum.video)
        self.assertEqual(_infer_file_type('audio/mpeg', 'aud.mp3'), MediaTypeEnum.audio)
        self.assertEqual(_infer_file_type('application/octet-stream', 'unknown.bin'), MediaTypeEnum.other)
        self.assertEqual(_infer_file_type(None, 'image.png'), MediaTypeEnum.photo) # Test filename inference
        self.assertEqual(_infer_file_type(None, None), MediaTypeEnum.other)


    # --- Tests for upload_media_item_db ---
    @patch('services.media_service.MediaItem') # Mock the MediaItem model class
    @patch('services.media_service.Person') # Mock Person for entity check
    def test_upload_media_item_db_success_person_entity(self, MockPersonModel, MockMediaItemModel):
        mock_person_entity = MockPersonModel() # Instance returned by _get_or_404
        mock_person_entity.tree_id = self.test_tree_id # Ensure tree_id matches
        self.mock_get_or_404.return_value = mock_person_entity
        
        mock_media_item_instance = MockMediaItemModel.return_value
        mock_media_item_instance.to_dict.return_value = {"id": str(self.test_media_id), "file_name": "test.jpg"}

        file_stream = io.BytesIO(b"fake image data")
        filename = "test.jpg"
        content_type = "image/jpeg"
        
        result = upload_media_item_db(
            self.mock_db_session, self.test_user_id, self.test_tree_id,
            "Person", self.test_person_id, file_stream, filename, content_type, "A test caption"
        )

        self.mock_get_or_404.assert_called_once_with(self.mock_db_session, Person, self.test_person_id, tree_id=self.test_tree_id)
        self.mock_s3_client.upload_fileobj.assert_called_once_with(
            file_stream, config.OBJECT_STORAGE_BUCKET_NAME, ANY, ExtraArgs={'ContentType': content_type}
        )
        MockMediaItemModel.assert_called_once() # Check MediaItem was instantiated
        # More detailed check of args passed to MediaItem constructor
        _, kwargs = MockMediaItemModel.call_args
        self.assertEqual(kwargs['uploader_user_id'], self.test_user_id)
        self.assertEqual(kwargs['tree_id'], self.test_tree_id)
        self.assertEqual(kwargs['file_name'], "test.jpg") # secure_filename result
        self.assertEqual(kwargs['file_type'], MediaTypeEnum.photo) # Inferred
        self.assertEqual(kwargs['storage_path'], self.mock_s3_client.upload_fileobj.call_args[0][2]) # Check object_key matches
        self.assertEqual(kwargs['file_size'], len(b"fake image data"))

        self.mock_db_session.add.assert_called_once_with(mock_media_item_instance)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(mock_media_item_instance)
        self.assertEqual(result, mock_media_item_instance.to_dict.return_value)

    @patch('services.media_service.Tree') # Mock Tree for entity check
    def test_upload_media_item_db_entity_tree_id_mismatch(self, MockTreeModel):
        mock_tree_entity = MockTreeModel()
        mock_tree_entity.id = uuid.uuid4() # Different from self.test_tree_id
        self.mock_get_or_404.return_value = mock_tree_entity

        with self.assertRaises(HTTPException) as context:
            upload_media_item_db(
                self.mock_db_session, self.test_user_id, self.test_tree_id,
                "Tree", mock_tree_entity.id, io.BytesIO(b"data"), "test.txt", "text/plain"
            )
        self.assertEqual(context.exception.code, 400) # Bad Request due to tree ID mismatch

    def test_upload_media_item_db_s3_failure(self):
        self.mock_get_or_404.return_value = MagicMock(spec=Person, tree_id=self.test_tree_id) # Mock entity
        self.mock_s3_client.upload_fileobj.side_effect = S3UploadFailedError("S3 is sad")
        
        with self.assertRaises(HTTPException) as context:
            upload_media_item_db(
                self.mock_db_session, self.test_user_id, self.test_tree_id,
                "Person", self.test_person_id, io.BytesIO(b"data"), "fail.jpg", "image/jpeg"
            )
        self.assertEqual(context.exception.code, 500)
        self.mock_db_session.rollback.assert_called_once()

    # --- Tests for delete_media_item_db ---
    def test_delete_media_item_db_success(self):
        mock_media_item = MagicMock(spec=MediaItem)
        mock_media_item.id = self.test_media_id
        mock_media_item.tree_id = self.test_tree_id
        mock_media_item.uploader_user_id = self.test_user_id # User is uploader
        mock_media_item.storage_path = "some/s3/key.jpg"
        self.mock_get_or_404.return_value = mock_media_item

        result = delete_media_item_db(self.mock_db_session, self.test_media_id, self.test_user_id, self.test_tree_id)

        self.mock_get_or_404.assert_called_once_with(self.mock_db_session, MediaItem, self.test_media_id, tree_id=self.test_tree_id)
        self.mock_s3_client.delete_object.assert_called_once_with(
            Bucket=config.OBJECT_STORAGE_BUCKET_NAME, Key=mock_media_item.storage_path
        )
        self.mock_db_session.delete.assert_called_once_with(mock_media_item)
        self.mock_db_session.commit.assert_called_once()
        self.assertTrue(result)

    def test_delete_media_item_db_unauthorized(self):
        mock_media_item = MagicMock(spec=MediaItem)
        mock_media_item.uploader_user_id = uuid.uuid4() # Different user
        self.mock_get_or_404.return_value = mock_media_item

        with self.assertRaises(HTTPException) as context:
            delete_media_item_db(self.mock_db_session, self.test_media_id, self.test_user_id, self.test_tree_id)
        self.assertEqual(context.exception.code, 403) # Forbidden

    def test_delete_media_item_db_s3_failure_proceeds(self):
        mock_media_item = MagicMock(spec=MediaItem, uploader_user_id=self.test_user_id, storage_path="key")
        self.mock_get_or_404.return_value = mock_media_item
        self.mock_s3_client.delete_object.side_effect = ClientError({"Error": {"Code": "500", "Message": "S3 error"}}, "delete_object")

        result = delete_media_item_db(self.mock_db_session, self.test_media_id, self.test_user_id, self.test_tree_id)
        
        self.mock_db_session.delete.assert_called_once_with(mock_media_item) # Still deletes DB record
        self.mock_db_session.commit.assert_called_once()
        self.assertTrue(result) # Service returns True as DB deletion was successful

    # --- Tests for get_media_item_db ---
    def test_get_media_item_db_success(self):
        mock_media_item = MagicMock(spec=MediaItem)
        mock_media_item.to_dict.return_value = {"id": str(self.test_media_id)}
        self.mock_get_or_404.return_value = mock_media_item

        result = get_media_item_db(self.mock_db_session, self.test_media_id, self.test_tree_id)
        
        self.mock_get_or_404.assert_called_once_with(self.mock_db_session, MediaItem, self.test_media_id, tree_id=self.test_tree_id)
        self.assertEqual(result, mock_media_item.to_dict.return_value)

    # --- Tests for get_media_for_entity_db ---
    def test_get_media_for_entity_db_success(self):
        mock_paginated_result = {"items": [], "total_items": 0, "page": 1, "per_page": 10, "total_pages": 0}
        self.mock_paginate_query.return_value = mock_paginated_result
        
        entity_type = "Person"
        entity_id = self.test_person_id
        
        result = get_media_for_entity_db(self.mock_db_session, self.test_tree_id, entity_type, entity_id, page=1, per_page=10)

        self.mock_paginate_query.assert_called_once()
        args, kwargs = self.mock_paginate_query.call_args
        # query_arg = args[0] # This is the SQLAlchemy query object, hard to assert details without more complex setup
        self.assertEqual(args[1], MediaItem) # Model being paginated
        self.assertEqual(args[2], 1) # page
        self.assertEqual(args[3], 10) # per_page
        # Check filters on the query (more advanced)
        # query_arg.statement.whereclause ... this requires deeper SQLAlchemy knowledge to inspect correctly
        self.assertEqual(result, mock_paginated_result)

if __name__ == '__main__':
    unittest.main()
