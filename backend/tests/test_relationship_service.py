import unittest
from unittest.mock import MagicMock, patch, ANY
import uuid
from datetime import date

from sqlalchemy.orm import Session as DBSession
from werkzeug.exceptions import HTTPException, NotFound, BadRequest

# Adjust imports based on your project structure
from models import Relationship, RelationshipTypeEnum, Person, User 
from services.relationship_service import (
    create_relationship_db,
    update_relationship_db,
    # get_relationship_db, # Add if testing get
    # get_all_relationships_db, # Add if testing get_all
)
# from utils import _get_or_404 # Mocked directly in tests

class TestRelationshipService(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock(spec=DBSession)
        self.test_user_id = uuid.uuid4()
        self.test_tree_id = uuid.uuid4()
        self.test_person1_id = uuid.uuid4()
        self.test_person2_id = uuid.uuid4()
        self.test_relationship_id = uuid.uuid4()

        # Mock user for created_by
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = self.test_user_id
        
        # Mock Person instances for _get_or_404 checks
        self.mock_person1 = MagicMock(spec=Person, id=self.test_person1_id, tree_id=self.test_tree_id)
        self.mock_person2 = MagicMock(spec=Person, id=self.test_person2_id, tree_id=self.test_tree_id)


    @patch('services.relationship_service._get_or_404')
    @patch('services.relationship_service.Relationship') # Mock the Relationship model class
    def test_create_relationship_db_with_location_and_notes(self, MockRelationshipModel, mock_get_or_404):
        # Configure _get_or_404 to return appropriate mock persons
        def get_person_mock_side_effect(db_session, model, person_id, **kwargs):
            if person_id == self.test_person1_id:
                return self.mock_person1
            elif person_id == self.test_person2_id:
                return self.mock_person2
            raise NotFound(f"Person with ID {person_id} not found.")
        mock_get_or_404.side_effect = get_person_mock_side_effect
        
        mock_relationship_instance = MockRelationshipModel.return_value
        mock_relationship_instance.to_dict.return_value = {"id": str(self.test_relationship_id), "relationship_type": "spouse_current"}

        relationship_data = {
            "person1_id": str(self.test_person1_id),
            "person2_id": str(self.test_person2_id),
            "relationship_type": RelationshipTypeEnum.spouse_current.value,
            "start_date": "2020-01-01",
            "location": "Paris, France",
            "notes": "Wedding ceremony details."
        }
        
        created_relationship = create_relationship_db(self.mock_db_session, self.test_user_id, self.test_tree_id, relationship_data)

        MockRelationshipModel.assert_called_once_with(
            tree_id=self.test_tree_id, 
            created_by=self.test_user_id,
            person1_id=self.test_person1_id, 
            person2_id=self.test_person2_id,
            relationship_type=RelationshipTypeEnum.spouse_current,
            start_date=date(2020, 1, 1),
            end_date=None, # Default
            certainty_level=None, # Default
            custom_attributes={}, # Default
            notes="Wedding ceremony details.",
            location="Paris, France"
        )
        self.mock_db_session.add.assert_called_once_with(mock_relationship_instance)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(mock_relationship_instance)
        self.assertEqual(created_relationship, mock_relationship_instance.to_dict.return_value)

    @patch('services.relationship_service._get_or_404')
    def test_update_relationship_db_location_and_notes(self, mock_get_or_404):
        mock_existing_relationship = MagicMock(spec=Relationship)
        mock_existing_relationship.id = self.test_relationship_id
        mock_existing_relationship.tree_id = self.test_tree_id
        mock_existing_relationship.person1_id = self.test_person1_id
        mock_existing_relationship.person2_id = self.test_person2_id
        mock_existing_relationship.relationship_type = RelationshipTypeEnum.partner
        mock_existing_relationship.start_date = None
        mock_existing_relationship.end_date = None
        mock_existing_relationship.notes = "Initial notes."
        mock_existing_relationship.location = "Old Location"
        mock_existing_relationship.custom_attributes = {}
        mock_existing_relationship.certainty_level = None

        mock_get_or_404.return_value = mock_existing_relationship # For the relationship itself
        # _get_or_404 for persons within update loop won't be called if person_ids are not in update_data

        mock_existing_relationship.to_dict.return_value = {"id": str(self.test_relationship_id), "notes": "Updated notes", "location": "New Location"}

        update_data = {
            "notes": "Updated notes",
            "location": "New Location",
            "start_date": "2021-05-10"
        }
        
        updated_relationship_dict = update_relationship_db(self.mock_db_session, self.test_relationship_id, self.test_tree_id, update_data)

        mock_get_or_404.assert_called_once_with(self.mock_db_session, Relationship, self.test_relationship_id, tree_id=self.test_tree_id)
        self.assertEqual(mock_existing_relationship.notes, "Updated notes")
        self.assertEqual(mock_existing_relationship.location, "New Location")
        self.assertEqual(mock_existing_relationship.start_date, date(2021,5,10))
        
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(mock_existing_relationship)
        self.assertEqual(updated_relationship_dict, mock_existing_relationship.to_dict.return_value)

if __name__ == '__main__':
    unittest.main()
