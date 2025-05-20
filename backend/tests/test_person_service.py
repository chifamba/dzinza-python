import unittest
from unittest.mock import MagicMock, patch, call, ANY
import uuid
from datetime import date

from sqlalchemy.orm import Session as DBSession
from werkzeug.exceptions import HTTPException, NotFound, BadRequest

# Assuming your project structure allows this import path
# Adjust if your models/services are in a different relative path
from models import Person, PrivacyLevelEnum, User # Assuming User is needed for created_by
from services.person_service import (
    create_person_db,
    update_person_db
    # get_person_db, # Add if testing get
    # get_all_people_db, # Add if testing get_all
    # delete_person_db # Add if testing delete
)
# If _get_or_404 or _handle_sqlalchemy_error are used directly and need mocking from utils
# from utils import _get_or_404, _handle_sqlalchemy_error

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

    @patch('services.person_service.Person') # Mock the Person model class
    def test_create_person_db_with_all_new_fields(self, MockPerson):
        mock_person_instance = MockPerson.return_value
        mock_person_instance.to_dict.return_value = {"id": str(self.test_person_id), "first_name": "Test"} # Mock to_dict

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
            is_living=True, # Default when death_date is None
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
        mock_person_instance = MockPerson.return_value
        person_data = {
            "first_name": "Test",
            "profile_picture_url": "http://example.com/pic.png"
        }
        create_person_db(self.mock_db_session, self.test_user_id, self.test_tree_id, person_data)
        args, kwargs = MockPerson.call_args
        self.assertEqual(kwargs.get('profile_picture_url'), "http://example.com/pic.png")
        self.assertEqual(kwargs.get('custom_fields'), {}) # Should default to empty dict

    @patch('services.person_service.Person')
    def test_create_person_db_with_custom_fields_only(self, MockPerson):
        mock_person_instance = MockPerson.return_value
        person_data = {
            "first_name": "Test",
            "custom_fields": {"department": "dev"}
        }
        create_person_db(self.mock_db_session, self.test_user_id, self.test_tree_id, person_data)
        args, kwargs = MockPerson.call_args
        self.assertIsNone(kwargs.get('profile_picture_url')) # Should default to None
        self.assertEqual(kwargs.get('custom_fields'), {"department": "dev"})

    @patch('services.person_service.Person')
    def test_create_person_db_with_neither_new_field(self, MockPerson):
        mock_person_instance = MockPerson.return_value
        person_data = {"first_name": "Test"}
        create_person_db(self.mock_db_session, self.test_user_id, self.test_tree_id, person_data)
        args, kwargs = MockPerson.call_args
        self.assertIsNone(kwargs.get('profile_picture_url'))
        self.assertEqual(kwargs.get('custom_fields'), {})

    @patch('services.person_service._get_or_404') # Mock _get_or_404 to return a mock Person
    def test_update_person_db_profile_url_and_custom_fields(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person)
        mock_person.id = self.test_person_id
        mock_person.tree_id = self.test_tree_id
        # Set initial values for fields that might be auto-updated based on others (like is_living)
        mock_person.birth_date = date(1990, 1, 1)
        mock_person.death_date = None
        mock_person.is_living = True
        mock_person.privacy_level = PrivacyLevelEnum.inherit # Ensure it has a privacy_level
        mock_person.custom_attributes = {} # Ensure it has custom_attributes
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
        mock_person = MagicMock(spec=Person)
        mock_person.profile_picture_url = "http://old.com/old.jpg"
        # Set other required fields for update logic
        mock_person.birth_date = None 
        mock_person.death_date = None
        mock_person.is_living = True
        mock_person.privacy_level = PrivacyLevelEnum.inherit
        mock_person.custom_attributes = {}
        mock_person.custom_fields = {}
        mock_get_or_404.return_value = mock_person
        
        update_data = {"profile_picture_url": None}
        update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data)
        self.assertIsNone(mock_person.profile_picture_url)

    @patch('services.person_service._get_or_404')
    def test_update_person_db_update_custom_fields(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person)
        mock_person.custom_fields = {"old_key": "old_value"}
        # Set other required fields
        mock_person.birth_date = None
        mock_person.death_date = None
        mock_person.is_living = True
        mock_person.privacy_level = PrivacyLevelEnum.inherit
        mock_person.custom_attributes = {}
        mock_person.profile_picture_url = None
        mock_get_or_404.return_value = mock_person
        
        update_data = {"custom_fields": {"new_key": "new_value", "old_key": "updated_value"}}
        update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data)
        self.assertEqual(mock_person.custom_fields, {"new_key": "new_value", "old_key": "updated_value"})

    @patch('services.person_service._get_or_404')
    def test_update_person_db_clear_custom_fields(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person)
        mock_person.custom_fields = {"old_key": "old_value"}
        # Set other required fields
        mock_person.birth_date = None
        mock_person.death_date = None
        mock_person.is_living = True
        mock_person.privacy_level = PrivacyLevelEnum.inherit
        mock_person.custom_attributes = {}
        mock_person.profile_picture_url = None
        mock_get_or_404.return_value = mock_person

        update_data_empty_dict = {"custom_fields": {}}
        update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data_empty_dict)
        self.assertEqual(mock_person.custom_fields, {})
        
        # Test setting to None also results in empty dict
        mock_person.custom_fields = {"another_key": "another_value"} # Reset for next part
        update_data_none = {"custom_fields": None}
        update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data_none)
        self.assertEqual(mock_person.custom_fields, {})


    @patch('services.person_service._get_or_404')
    def test_update_person_db_custom_fields_validation_not_dict(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person)
        # Set other required fields
        mock_person.birth_date = None
        mock_person.death_date = None
        mock_person.is_living = True
        mock_person.privacy_level = PrivacyLevelEnum.inherit
        mock_person.custom_attributes = {}
        mock_person.profile_picture_url = None
        mock_person.custom_fields = {}
        mock_get_or_404.return_value = mock_person
        
        update_data = {"custom_fields": "not a dictionary"}
        with self.assertRaises(HTTPException) as context: # werkzeug.exceptions.BadRequest (subclass of HTTPException)
            update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data)
        
        self.assertEqual(context.exception.code, 400)
        # Assuming the service function aborts with a specific structure
        # self.assertIn("Custom fields must be a dictionary or null", context.exception.description.get("details").get("custom_fields"))
        # More robust check if abort description structure changes:
        self.assertTrue(any("Custom fields must be a dictionary or null" in str(err) for err in context.exception.description.get("details", {}).values()))


if __name__ == '__main__':
    unittest.main()
