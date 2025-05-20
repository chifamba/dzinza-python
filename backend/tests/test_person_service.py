import unittest
from unittest.mock import MagicMock, patch, call, ANY
import uuid
from datetime import date
import io # For mocking file streams

from sqlalchemy.orm import Session as DBSession
from werkzeug.exceptions import HTTPException, NotFound, BadRequest
from botocore.exceptions import S3UploadFailedError, ClientError # For S3 error simulation

# Assuming your project structure allows this import path
# Adjust if your models/services are in a different relative path
from models import Person, PrivacyLevelEnum, User 
from services.person_service import (
    create_person_db,
    update_person_db,
    upload_profile_picture_db # Added function to test
)
from config import config # For S3 bucket name etc.
# utils._get_or_404 is mocked directly where used by specific service functions

class TestPersonService(unittest.TestCase):

    def setUp(self):
        # Common setup for tests, e.g., mock DB session
        self.mock_db_session = MagicMock(spec=DBSession)
        self.test_user_id = uuid.uuid4()
        self.test_tree_id = uuid.uuid4()
        self.test_person_id = uuid.uuid4()

        # Mock user for created_by
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = self.test_user_id
        
        # Mocks for S3 related operations, common for upload tests
        self.mock_s3_client = MagicMock()
        self.patcher_get_storage_client = patch('services.person_service.get_storage_client', return_value=self.mock_s3_client)
        self.patcher_create_bucket = patch('services.person_service.create_bucket_if_not_exists', return_value=True)
        
        self.mock_get_storage_client = self.patcher_get_storage_client.start()
        self.mock_create_bucket = self.patcher_create_bucket.start()

    def tearDown(self):
        self.patcher_get_storage_client.stop()
        self.patcher_create_bucket.stop()
        # Ensure any other patchers started in specific tests are stopped if not managed by with statement

    @patch('services.person_service.Person') 
    def test_create_person_db_with_all_new_fields(self, MockPerson):
        mock_person_instance = MockPerson.return_value
        mock_person_instance.to_dict.return_value = {"id": str(self.test_person_id), "first_name": "Test"} 

        person_data = {
            "first_name": "Test", "last_name": "User",
            "profile_picture_url": "http://example.com/profile.jpg",
            "custom_fields": {"hobby": "testing", "skill": "mocking"}
        }
        
        created_person = create_person_db(self.mock_db_session, self.test_user_id, self.test_tree_id, person_data)

        MockPerson.assert_called_once_with(
            tree_id=self.test_tree_id, created_by=self.test_user_id,
            first_name="Test", last_name="User",
            middle_names=None, maiden_name=None, nickname=None, gender=None,
            birth_date=None, birth_date_approx=False, birth_place=None, place_of_birth=None,
            death_date=None, death_date_approx=False, death_place=None, place_of_death=None,
            burial_place=None, privacy_level=PrivacyLevelEnum.inherit,
            is_living=True, 
            notes=None, biography=None, custom_attributes={},
            profile_picture_url="http://example.com/profile.jpg",
            custom_fields={"hobby": "testing", "skill": "mocking"}
        )
        self.mock_db_session.add.assert_called_once_with(mock_person_instance)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(mock_person_instance)
        self.assertEqual(created_person, mock_person_instance.to_dict.return_value)

    @patch('services.person_service.Person')
    def test_create_person_db_with_profile_url_only(self, MockPerson):
        MockPerson.return_value # Ensure it's a mock
        person_data = {
            "first_name": "Test",
            "profile_picture_url": "http://example.com/pic.png"
        }
        create_person_db(self.mock_db_session, self.test_user_id, self.test_tree_id, person_data)
        args, kwargs = MockPerson.call_args
        self.assertEqual(kwargs.get('profile_picture_url'), "http://example.com/pic.png")
        self.assertEqual(kwargs.get('custom_fields'), {})

    @patch('services.person_service.Person')
    def test_create_person_db_with_custom_fields_only(self, MockPerson):
        MockPerson.return_value
        person_data = {
            "first_name": "Test",
            "custom_fields": {"department": "dev"}
        }
        create_person_db(self.mock_db_session, self.test_user_id, self.test_tree_id, person_data)
        args, kwargs = MockPerson.call_args
        self.assertIsNone(kwargs.get('profile_picture_url'))
        self.assertEqual(kwargs.get('custom_fields'), {"department": "dev"})

    @patch('services.person_service.Person')
    def test_create_person_db_with_neither_new_field(self, MockPerson):
        MockPerson.return_value
        person_data = {"first_name": "Test"}
        create_person_db(self.mock_db_session, self.test_user_id, self.test_tree_id, person_data)
        args, kwargs = MockPerson.call_args
        self.assertIsNone(kwargs.get('profile_picture_url'))
        self.assertEqual(kwargs.get('custom_fields'), {})

    @patch('services.person_service._get_or_404') 
    def test_update_person_db_profile_url_and_custom_fields(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person)
        mock_person.id = self.test_person_id
        mock_person.tree_id = self.test_tree_id
        mock_person.birth_date = date(1990, 1, 1)
        mock_person.death_date = None
        mock_person.is_living = True
        mock_person.privacy_level = PrivacyLevelEnum.inherit
        mock_person.custom_attributes = {}
        mock_person.profile_picture_url = None
        mock_person.custom_fields = {}
        mock_get_or_404.return_value = mock_person
        mock_person.to_dict.return_value = {"id": str(self.test_person_id), "first_name": "Updated Name"}

        update_data = {
            "first_name": "Updated Name",
            "profile_picture_url": "http://new.com/new.jpg",
            "custom_fields": {"status": "active", "id": 123}
        }
        updated_person_dict = update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data)

        mock_get_or_404.assert_called_once_with(self.mock_db_session, Person, self.test_person_id, tree_id=self.test_tree_id)
        self.assertEqual(mock_person.first_name, "Updated Name")
        self.assertEqual(mock_person.profile_picture_url, "http://new.com/new.jpg")
        self.assertEqual(mock_person.custom_fields, {"status": "active", "id": 123})
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(mock_person)
        self.assertEqual(updated_person_dict, mock_person.to_dict.return_value)

    @patch('services.person_service._get_or_404')
    def test_update_person_db_clear_profile_url(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person, profile_picture_url="http://old.com/old.jpg", birth_date=None, death_date=None, is_living=True, privacy_level=PrivacyLevelEnum.inherit, custom_attributes={}, custom_fields={})
        mock_get_or_404.return_value = mock_person
        update_data = {"profile_picture_url": None}
        update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data)
        self.assertIsNone(mock_person.profile_picture_url)

    @patch('services.person_service._get_or_404')
    def test_update_person_db_update_custom_fields(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person, custom_fields={"old_key": "old_value"}, birth_date=None, death_date=None, is_living=True, privacy_level=PrivacyLevelEnum.inherit, custom_attributes={}, profile_picture_url=None)
        mock_get_or_404.return_value = mock_person
        update_data = {"custom_fields": {"new_key": "new_value", "old_key": "updated_value"}}
        update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data)
        self.assertEqual(mock_person.custom_fields, {"new_key": "new_value", "old_key": "updated_value"})

    @patch('services.person_service._get_or_404')
    def test_update_person_db_clear_custom_fields(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person, custom_fields={"old_key": "old_value"}, birth_date=None, death_date=None, is_living=True, privacy_level=PrivacyLevelEnum.inherit, custom_attributes={}, profile_picture_url=None)
        mock_get_or_404.return_value = mock_person
        update_data_empty_dict = {"custom_fields": {}}
        update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data_empty_dict)
        self.assertEqual(mock_person.custom_fields, {})
        
        mock_person.custom_fields = {"another_key": "another_value"}
        update_data_none = {"custom_fields": None}
        update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data_none)
        self.assertEqual(mock_person.custom_fields, {})

    @patch('services.person_service._get_or_404')
    def test_update_person_db_custom_fields_validation_not_dict(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person, birth_date=None, death_date=None, is_living=True, privacy_level=PrivacyLevelEnum.inherit, custom_attributes={}, profile_picture_url=None, custom_fields={})
        mock_get_or_404.return_value = mock_person
        update_data = {"custom_fields": "not a dictionary"}
        with self.assertRaises(HTTPException) as context:
            update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data)
        self.assertEqual(context.exception.code, 400)
        self.assertTrue(any("Custom fields must be a dictionary or null" in str(err) for err in context.exception.description.get("details", {}).values()))

    # --- Tests for upload_profile_picture_db ---
    @patch('services.person_service._get_or_404')
    @patch('services.person_service.secure_filename', side_effect=lambda x: x) # Mock secure_filename
    def test_upload_profile_picture_db_new_picture(self, mock_secure_filename, mock_get_or_404):
        mock_person = MagicMock(spec=Person)
        mock_person.profile_picture_url = None # No existing picture
        mock_person.to_dict.return_value = {"profile_picture_url": "new_key.jpg"}
        mock_get_or_404.return_value = mock_person

        file_stream = io.BytesIO(b"fake image data")
        filename = "profile.jpg"
        content_type = "image/jpeg"
        
        result = upload_profile_picture_db(
            self.mock_db_session, self.test_person_id, self.test_tree_id, self.test_user_id,
            file_stream, filename, content_type
        )

        mock_get_or_404.assert_called_once_with(self.mock_db_session, Person, self.test_person_id, tree_id=self.test_tree_id)
        self.mock_s3_client.upload_fileobj.assert_called_once_with(
            file_stream, config.OBJECT_STORAGE_BUCKET_NAME, ANY, ExtraArgs={'ContentType': content_type}
        )
        new_object_key = self.mock_s3_client.upload_fileobj.call_args[0][2]
        self.assertTrue(filename in new_object_key) # Check filename part is in key
        self.assertEqual(mock_person.profile_picture_url, new_object_key)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(mock_person)
        self.assertEqual(result, mock_person.to_dict.return_value)
        self.mock_s3_client.delete_object.assert_not_called() # No old picture to delete

    @patch('services.person_service._get_or_404')
    @patch('services.person_service.secure_filename', side_effect=lambda x: x)
    def test_upload_profile_picture_db_replace_existing(self, mock_secure_filename, mock_get_or_404):
        old_key = f"profile_pictures/{self.test_tree_id}/{self.test_person_id}/old_pic.jpg"
        mock_person = MagicMock(spec=Person)
        mock_person.profile_picture_url = old_key
        mock_get_or_404.return_value = mock_person

        file_stream = io.BytesIO(b"new fake image data")
        new_filename = "new_profile.png"
        
        upload_profile_picture_db(
            self.mock_db_session, self.test_person_id, self.test_tree_id, self.test_user_id,
            file_stream, new_filename, "image/png"
        )

        self.mock_s3_client.upload_fileobj.assert_called_once()
        self.mock_s3_client.delete_object.assert_called_once_with(
            Bucket=config.OBJECT_STORAGE_BUCKET_NAME, Key=old_key
        )
        self.assertNotEqual(mock_person.profile_picture_url, old_key) # URL should be updated
        self.assertTrue(new_filename in mock_person.profile_picture_url)

    @patch('services.person_service._get_or_404')
    def test_upload_profile_picture_db_s3_upload_fails(self, mock_get_or_404):
        mock_get_or_404.return_value = MagicMock(spec=Person, profile_picture_url=None)
        self.mock_s3_client.upload_fileobj.side_effect = S3UploadFailedError("Upload failed")

        with self.assertRaises(HTTPException) as context:
            upload_profile_picture_db(
                self.mock_db_session, self.test_person_id, self.test_tree_id, self.test_user_id,
                io.BytesIO(b"data"), "fail.jpg", "image/jpeg"
            )
        self.assertEqual(context.exception.code, 500)
        self.mock_db_session.rollback.assert_called_once()

    @patch('services.person_service._get_or_404')
    @patch('services.person_service.secure_filename', side_effect=lambda x: x)
    def test_upload_profile_picture_db_s3_old_delete_fails_logs_and_continues(self, mock_secure_filename, mock_get_or_404):
        old_key = "profile_pictures/some_old_key.jpg"
        mock_person = MagicMock(spec=Person, profile_picture_url=old_key)
        mock_get_or_404.return_value = mock_person
        
        self.mock_s3_client.delete_object.side_effect = ClientError({"Error": {"Code": "500", "Message": "Delete failed"}}, "delete_object")

        file_stream = io.BytesIO(b"new data")
        new_filename = "new.jpg"
        
        with patch('services.person_service.logger') as mock_logger: # Patch logger in the module
            upload_profile_picture_db(
                self.mock_db_session, self.test_person_id, self.test_tree_id, self.test_user_id,
                file_stream, new_filename, "image/jpeg"
            )
            mock_logger.error.assert_any_call( # Check if error was logged for delete failure
                f"Failed to delete old profile picture {old_key} from S3.", 
                error=ANY, person_id=self.test_person_id
            )

        self.mock_s3_client.upload_fileobj.assert_called_once() # New upload should still happen
        self.assertNotEqual(mock_person.profile_picture_url, old_key) # URL should be updated
        self.mock_db_session.commit.assert_called_once() # Commit should still happen


if __name__ == '__main__':
    unittest.main()
