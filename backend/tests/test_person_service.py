import unittest
from unittest.mock import MagicMock, patch, call, ANY
import uuid
from datetime import date
import io # For mocking file streams

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import or_, and_ # For constructing filter expressions to compare
from werkzeug.exceptions import HTTPException, NotFound, BadRequest
from botocore.exceptions import S3UploadFailedError, ClientError # For S3 error simulation

# Assuming your project structure allows this import path
# Adjust if your models/services are in a different relative path
from models import Person, PrivacyLevelEnum, User 
from services.person_service import (
    create_person_db,
    update_person_db,
    upload_profile_picture_db,
    get_all_people_db # Added for testing
)
from config import config # For S3 bucket name etc.
# utils._get_or_404 is mocked directly where used by specific service functions

# Helper to roughly compare SQLAlchemy filter expressions by their string representation
# This is a simplification and might be fragile for very complex queries.
def compare_filter_expression(expr1, expr2):
    return str(expr1) == str(expr2)

class TestPersonService(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock(spec=DBSession)
        self.test_user_id = uuid.uuid4()
        self.test_tree_id = uuid.uuid4()
        self.test_person_id = uuid.uuid4()

        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = self.test_user_id
        
        self.mock_s3_client = MagicMock()
        self.patcher_get_storage_client = patch('services.person_service.get_storage_client', return_value=self.mock_s3_client)
        self.patcher_create_bucket = patch('services.person_service.create_bucket_if_not_exists', return_value=True)
        
        self.mock_get_storage_client = self.patcher_get_storage_client.start()
        self.mock_create_bucket = self.patcher_create_bucket.start()

        # Mock for paginate_query used in get_all_people_db
        self.patcher_paginate_query = patch('services.person_service.paginate_query')
        self.mock_paginate_query = self.patcher_paginate_query.start()
        self.mock_paginate_query.return_value = {"items": [], "total_items": 0} # Default mock response

        # Mock the query object that db.query(Person) would return
        self.mock_query_object = MagicMock()
        self.mock_db_session.query.return_value.filter.return_value = self.mock_query_object # Initial filter by tree_id

    def tearDown(self):
        self.patcher_get_storage_client.stop()
        self.patcher_create_bucket.stop()
        self.patcher_paginate_query.stop()
        patch.stopall()

    # --- Tests for get_all_people_db search and filtering ---
    def test_get_all_people_db_search_term(self):
        filters = {'search_term': 'John'}
        get_all_people_db(self.mock_db_session, self.test_tree_id, filters=filters)
        
        # Check that query.filter was called with an OR condition for name fields
        self.mock_query_object.filter.assert_called_once()
        args, _ = self.mock_query_object.filter.call_args
        filter_clause = args[0] # The SQLAlchemy filter clause
        
        # Rough check: ensure it's an OR clause and contains ILIKE for relevant fields
        self.assertEqual(filter_clause.operator, or_)
        clauses_str = [str(c) for c in filter_clause.clauses]
        self.assertIn(str(Person.first_name.ilike('%John%')), clauses_str)
        self.assertIn(str(Person.last_name.ilike('%John%')), clauses_str)
        self.assertIn(str(Person.nickname.ilike('%John%')), clauses_str)
        self.assertIn(str(Person.maiden_name.ilike('%John%')), clauses_str)
        self.mock_paginate_query.assert_called_once()


    def test_get_all_people_db_birth_date_range(self):
        filters = {'birth_date_range_start': '2000-01-01', 'birth_date_range_end': '2000-12-31'}
        get_all_people_db(self.mock_db_session, self.test_tree_id, filters=filters)
        
        self.mock_query_object.filter.assert_called_once()
        args, _ = self.mock_query_object.filter.call_args
        filter_clause = args[0]
        
        # Expected conditions
        expected_start_cond = Person.birth_date >= date(2000, 1, 1)
        expected_end_cond = Person.birth_date <= date(2000, 12, 31)

        # This check is approximate. A more robust way would be to compile and compare SQL,
        # or use a library that helps inspect SQLAlchemy expressions.
        self.assertEqual(filter_clause.operator, and_) # Implicit AND
        self.assertTrue(any(compare_filter_expression(c, expected_start_cond) for c in filter_clause.clauses))
        self.assertTrue(any(compare_filter_expression(c, expected_end_cond) for c in filter_clause.clauses))
        self.mock_paginate_query.assert_called_once()

    def test_get_all_people_db_death_date_range(self):
        filters = {'death_date_range_start': '2020-01-01'}
        get_all_people_db(self.mock_db_session, self.test_tree_id, filters=filters)
        
        self.mock_query_object.filter.assert_called_once()
        args, _ = self.mock_query_object.filter.call_args
        filter_clause = args[0]
        expected_cond = Person.death_date >= date(2020, 1, 1)
        self.assertTrue(compare_filter_expression(filter_clause.clauses[0], expected_cond)) # Assuming only one condition
        self.mock_paginate_query.assert_called_once()

    def test_get_all_people_db_invalid_date_format(self):
        filters = {'birth_date_range_start': 'invalid-date'}
        with self.assertRaises(HTTPException) as context:
            get_all_people_db(self.mock_db_session, self.test_tree_id, filters=filters)
        self.assertEqual(context.exception.code, 400)
        self.assertIn("Invalid date format", context.exception.description['details']['birth_date_range_start'])
        self.mock_paginate_query.assert_not_called() # Should abort before pagination

    def test_get_all_people_db_custom_fields_filter(self):
        filters = {'custom_fields_key': 'hobby', 'custom_fields_value': 'coding'}
        get_all_people_db(self.mock_db_session, self.test_tree_id, filters=filters)
        
        self.mock_query_object.filter.assert_called_once()
        args, _ = self.mock_query_object.filter.call_args
        filter_clause = args[0]
        expected_cond = Person.custom_fields['hobby'].astext == 'coding'
        self.assertTrue(compare_filter_expression(filter_clause.clauses[0], expected_cond))
        self.mock_paginate_query.assert_called_once()

    def test_get_all_people_db_combined_filters(self):
        filters = {
            'search_term': 'Smith',
            'is_living': True,
            'birth_date_range_end': '1990-12-31',
            'custom_fields_key': 'occupation', 
            'custom_fields_value': 'engineer'
        }
        get_all_people_db(self.mock_db_session, self.test_tree_id, filters=filters)
        
        self.mock_query_object.filter.assert_called_once()
        args, _ = self.mock_query_object.filter.call_args
        filter_clause = args[0] # This will be an AND clause of multiple conditions
        
        self.assertEqual(filter_clause.operator, and_)
        self.assertEqual(len(filter_clause.clauses), 4) # is_living, search_term (OR), birth_date, custom_fields
        
        # Example check for one of the clauses
        is_living_cond_found = any(compare_filter_expression(c, Person.is_living == True) for c in filter_clause.clauses)
        self.assertTrue(is_living_cond_found)
        
        # search_term itself is an OR clause, one of the ANDed clauses
        search_term_clause_found = any(c.operator == or_ and len(c.clauses) == 4 for c in filter_clause.clauses)
        self.assertTrue(search_term_clause_found)
        
        self.mock_paginate_query.assert_called_once()

    # --- Existing tests below (abbreviated for brevity, ensure they remain) ---
    @patch('services.person_service.Person') 
    def test_create_person_db_with_all_new_fields(self, MockPerson):
        mock_person_instance = MockPerson.return_value
        mock_person_instance.to_dict.return_value = {"id": str(self.test_person_id), "first_name": "Test"} 
        person_data = { "first_name": "Test", "last_name": "User", "profile_picture_url": "http://example.com/profile.jpg", "custom_fields": {"hobby": "testing"}}
        created_person = create_person_db(self.mock_db_session, self.test_user_id, self.test_tree_id, person_data)
        MockPerson.assert_called_once()
        self.mock_db_session.add.assert_called_once_with(mock_person_instance)
        self.assertEqual(created_person, mock_person_instance.to_dict.return_value)

    @patch('services.person_service._get_or_404') 
    def test_update_person_db_profile_url_and_custom_fields(self, mock_get_or_404):
        mock_person = MagicMock(spec=Person)
        mock_get_or_404.return_value = mock_person
        mock_person.to_dict.return_value = {"id": str(self.test_person_id), "first_name": "Updated Name"}
        update_data = { "first_name": "Updated Name", "profile_picture_url": "http://new.com/new.jpg", "custom_fields": {"status": "active"}}
        updated_person_dict = update_person_db(self.mock_db_session, self.test_person_id, self.test_tree_id, update_data)
        self.assertEqual(mock_person.first_name, "Updated Name")
        self.assertEqual(updated_person_dict, mock_person.to_dict.return_value)

    @patch('services.person_service._get_or_404')
    @patch('services.person_service.secure_filename', side_effect=lambda x: x) 
    def test_upload_profile_picture_db_new_picture(self, mock_secure_filename, mock_get_or_404):
        mock_person = MagicMock(spec=Person, profile_picture_url=None)
        mock_person.to_dict.return_value = {"profile_picture_url": "new_key.jpg"}
        mock_get_or_404.return_value = mock_person
        file_stream = io.BytesIO(b"fake image data")
        result = upload_profile_picture_db(self.mock_db_session, self.test_person_id, self.test_tree_id, self.test_user_id, file_stream, "profile.jpg", "image/jpeg")
        self.mock_s3_client.upload_fileobj.assert_called_once()
        self.assertEqual(result, mock_person.to_dict.return_value)

if __name__ == '__main__':
    unittest.main()
