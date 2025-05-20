import unittest
from unittest.mock import MagicMock, patch, ANY, call
import uuid
from datetime import date

from sqlalchemy.orm import Session as DBSession
from werkzeug.exceptions import HTTPException, NotFound, BadRequest

# Adjust imports based on your project structure
from models import Event, Person, Tree, PrivacyLevelEnum, TreePrivacySettingEnum # Added relevant models
from services.event_service import (
    create_event_db,
    get_event_db,
    update_event_db,
    delete_event_db,
    get_events_for_person_db,
    get_events_for_tree_db,
    _validate_person_ids # Test this helper too
)
from config import config # For pagination defaults

class TestEventService(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock(spec=DBSession)
        self.test_user_id = uuid.uuid4()
        self.test_tree_id = uuid.uuid4()
        self.test_event_id = uuid.uuid4()
        self.test_person_id = uuid.uuid4()
        self.related_person1_id = uuid.uuid4()
        self.related_person2_id = uuid.uuid4()
        
        self.patcher_get_or_404 = patch('services.event_service._get_or_404')
        self.patcher_paginate_query = patch('services.event_service.paginate_query')

        self.mock_get_or_404 = self.patcher_get_or_404.start()
        self.mock_paginate_query = self.patcher_paginate_query.start()

    def tearDown(self):
        self.patcher_get_or_404.stop()
        self.patcher_paginate_query.stop()
        patch.stopall()

    # --- Tests for _validate_person_ids ---
    def test_validate_person_ids_success(self):
        mock_person1 = MagicMock(spec=Person, id=self.related_person1_id)
        mock_person2 = MagicMock(spec=Person, id=self.related_person2_id)
        
        # Configure query mock
        def query_side_effect(*args):
            if args[0] == Person.id: # Simulating query(Person.id)
                mock_query_obj = MagicMock()
                # Simulate filter().one_or_none()
                def filter_one_or_none_side_effect(condition):
                    # This is a simplification; real conditions are more complex.
                    # We assume the condition checks person_id and tree_id.
                    # Here, we check if the ID in condition matches our mock persons.
                    # A more robust mock would parse the SQLAlchmey condition.
                    if self.related_person1_id in condition.right.value: return mock_person1
                    if self.related_person2_id in condition.right.value: return mock_person2
                    return None
                
                mock_query_obj.filter.return_value.one_or_none.side_effect = filter_one_or_none_side_effect
                return mock_query_obj
            return MagicMock() # Default mock for other queries

        self.mock_db_session.query.side_effect = query_side_effect
        
        ids_to_validate = [str(self.related_person1_id), str(self.related_person2_id)]
        validated_ids = _validate_person_ids(self.mock_db_session, self.test_tree_id, ids_to_validate, "related_ids")
        self.assertEqual(len(validated_ids), 2)
        self.assertIn(self.related_person1_id, validated_ids)
        self.assertIn(self.related_person2_id, validated_ids)

    def test_validate_person_ids_invalid_uuid_format(self):
        with self.assertRaises(HTTPException) as context:
            _validate_person_ids(self.mock_db_session, self.test_tree_id, ["invalid-uuid"], "related_ids")
        self.assertEqual(context.exception.code, 400)
        self.assertIn("Invalid UUID format", context.exception.description['details']['related_ids'][0])

    def test_validate_person_ids_person_not_found(self):
        self.mock_db_session.query(Person.id).filter().one_or_none.return_value = None # Person not found
        non_existent_id = str(uuid.uuid4())
        with self.assertRaises(HTTPException) as context:
            _validate_person_ids(self.mock_db_session, self.test_tree_id, [non_existent_id], "related_ids")
        self.assertEqual(context.exception.code, 400)
        self.assertIn(f"Person with ID {non_existent_id} not found", context.exception.description['details']['related_ids'][0])

    # --- Tests for create_event_db ---
    @patch('services.event_service.Event') # Mock the Event model
    def test_create_event_db_success_with_person_and_related(self, MockEventModel):
        mock_event_instance = MockEventModel.return_value
        mock_event_instance.to_dict.return_value = {"id": str(self.test_event_id), "event_type": "BIRTH"}

        # Mock _get_or_404 for person_id validation
        self.mock_get_or_404.return_value = MagicMock(spec=Person) 
        # Mock _validate_person_ids to return valid UUIDs
        with patch('services.event_service._validate_person_ids', return_value=[self.related_person1_id]) as mock_validate_ids:
            event_data = {
                "event_type": "MARRIAGE", "date": "2023-01-15",
                "person_id": str(self.test_person_id),
                "related_person_ids": [str(self.related_person1_id)],
                "place": "Chapel"
            }
            created_event = create_event_db(self.mock_db_session, self.test_user_id, self.test_tree_id, event_data)

        MockEventModel.assert_called_once()
        _, kwargs = MockEventModel.call_args
        self.assertEqual(kwargs['person_id'], self.test_person_id)
        self.assertEqual(kwargs['related_person_ids'], [str(self.related_person1_id)])
        self.assertEqual(kwargs['event_type'], "MARRIAGE")
        self.assertEqual(kwargs['place'], "Chapel")

        self.mock_db_session.add.assert_called_once_with(mock_event_instance)
        self.assertEqual(created_event, mock_event_instance.to_dict.return_value)

    @patch('services.event_service.Event')
    def test_create_event_db_tree_event_no_person_id(self, MockEventModel):
        mock_event_instance = MockEventModel.return_value
        mock_event_instance.to_dict.return_value = {"id": str(self.test_event_id), "event_type": "TREE_ANNIVERSARY"}
        
        # _get_or_404 should not be called if person_id is not in event_data
        self.mock_get_or_404.reset_mock() 

        event_data = {"event_type": "TREE_ANNIVERSARY", "date": "2023-05-05", "description": "Tree founded"}
        created_event = create_event_db(self.mock_db_session, self.test_user_id, self.test_tree_id, event_data)

        self.mock_get_or_404.assert_not_called() # Important check
        MockEventModel.assert_called_once()
        _, kwargs = MockEventModel.call_args
        self.assertIsNone(kwargs['person_id'])
        self.assertEqual(kwargs['event_type'], "TREE_ANNIVERSARY")
        self.assertEqual(created_event, mock_event_instance.to_dict.return_value)

    def test_create_event_db_missing_event_type(self):
        with self.assertRaises(HTTPException) as context:
            create_event_db(self.mock_db_session, self.test_user_id, self.test_tree_id, {"date": "2023-01-01"})
        self.assertEqual(context.exception.code, 400)
        self.assertIn("Event type is required", context.exception.description['details']['event_type'])

    def test_create_event_db_invalid_date_format(self):
        with self.assertRaises(HTTPException) as context:
            create_event_db(self.mock_db_session, self.test_user_id, self.test_tree_id, {"event_type": "TEST", "date": "invalid-date"})
        self.assertEqual(context.exception.code, 400)
        self.assertIn("Invalid date format", context.exception.description['details']['date'])

    # --- Tests for update_event_db ---
    def test_update_event_db_success(self):
        mock_event = MagicMock(spec=Event)
        self.mock_get_or_404.side_effect = [mock_event] # First for event, then for person if person_id updated
        mock_event.to_dict.return_value = {"id": str(self.test_event_id), "description": "Updated Desc"}

        update_data = {"description": "Updated Desc", "place": "New Place"}
        updated_event = update_event_db(self.mock_db_session, self.test_event_id, self.test_tree_id, update_data)
        
        self.mock_get_or_404.assert_called_once_with(self.mock_db_session, Event, self.test_event_id, tree_id=self.test_tree_id)
        self.assertEqual(mock_event.description, "Updated Desc")
        self.assertEqual(mock_event.place, "New Place")
        self.mock_db_session.commit.assert_called_once()
        self.assertEqual(updated_event, mock_event.to_dict.return_value)

    def test_update_event_db_clear_person_id(self):
        mock_event = MagicMock(spec=Event, person_id=self.test_person_id)
        self.mock_get_or_404.return_value = mock_event
        
        update_data = {"person_id": None}
        update_event_db(self.mock_db_session, self.test_event_id, self.test_tree_id, update_data)
        self.assertIsNone(mock_event.person_id)

    # --- Tests for delete_event_db ---
    def test_delete_event_db_success(self):
        mock_event = MagicMock(spec=Event)
        self.mock_get_or_404.return_value = mock_event
        
        result = delete_event_db(self.mock_db_session, self.test_event_id, self.test_tree_id)
        
        self.mock_db_session.delete.assert_called_once_with(mock_event)
        self.mock_db_session.commit.assert_called_once()
        self.assertTrue(result)

    # --- Tests for get_events_for_person_db ---
    def test_get_events_for_person_db_success(self):
        mock_person = MagicMock(spec=Person)
        self.mock_get_or_404.return_value = mock_person # For the initial person check
        
        mock_paginated_result = {"items": [{"event_type": "BIRTH"}], "total_items": 1}
        self.mock_paginate_query.return_value = mock_paginated_result
        
        result = get_events_for_person_db(self.mock_db_session, self.test_tree_id, self.test_person_id, 1, 10, "date", "asc")
        
        self.mock_get_or_404.assert_called_once_with(self.mock_db_session, Person, self.test_person_id, tree_id=self.test_tree_id)
        self.mock_paginate_query.assert_called_once()
        # Add more detailed query checks if necessary, e.g. for the OR condition
        self.assertEqual(result, mock_paginated_result)

    # --- Tests for get_events_for_tree_db ---
    def test_get_events_for_tree_db_with_filter(self):
        mock_paginated_result = {"items": [], "total_items": 0}
        self.mock_paginate_query.return_value = mock_paginated_result
        filters = {"event_type": "MARRIAGE"}
        
        result = get_events_for_tree_db(self.mock_db_session, self.test_tree_id, 1, 10, "date", "asc", filters=filters)
        
        self.mock_paginate_query.assert_called_once()
        # query_obj = self.mock_paginate_query.call_args[0][0]
        # self.assertIn("events.event_type ILIKE '%MARRIAGE%'", str(query_obj).lower()) # Example of checking filter
        self.assertEqual(result, mock_paginated_result)

if __name__ == '__main__':
    unittest.main()
