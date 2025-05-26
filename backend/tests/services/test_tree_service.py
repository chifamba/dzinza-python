import pytest
import uuid
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session as DBSession

from services.tree_service import get_tree_data_for_visualization_db
from models import Person, Relationship, Tree, PersonTreeAssociation, Event, GenderEnum, RelationshipTypeEnum
from config import config as app_config # Import the actual config instance

# Helper function to create mock person objects
def create_mock_person(id_val, first_name="Test", last_name="User", tree_id=None):
    person = MagicMock(spec=Person)
    person.id = id_val
    person.first_name = first_name
    person.last_name = last_name
    person.nickname = None
    person.gender = GenderEnum.male 
    person.birth_date = None
    person.death_date = None
    person.is_living = True
    person.to_dict = MagicMock(return_value={
        "id": str(id_val), "first_name": first_name, "last_name": last_name, 
        "gender": "male", "birth_date": None, "death_date": None, "is_living": True
    })
    if tree_id:
        person.tree_associations = [MagicMock(spec=PersonTreeAssociation, tree_id=tree_id, person_id=id_val)]
    return person

# Helper function to create mock relationship objects
def create_mock_relationship(id_val, person1_id, person2_id):
    relationship = MagicMock(spec=Relationship)
    relationship.id = id_val
    relationship.person1_id = person1_id
    relationship.person2_id = person2_id
    relationship.relationship_type = RelationshipTypeEnum.married_to
    relationship.to_dict = MagicMock(return_value={
        "id": str(id_val), "person1_id": str(person1_id), "person2_id": str(person2_id),
        "relationship_type": "married_to"
    })
    return relationship

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=DBSession)

@pytest.fixture
def mock_tree():
    tree = MagicMock(spec=Tree)
    tree.id = uuid.uuid4()
    return tree

def test_get_tree_data_visualization_initial_page(mock_db_session, mock_tree):
    """Test initial page request for tree visualization data."""
    page = 1
    per_page = 2 # Using a small number for easier testing
    tree_id = mock_tree.id

    # Mock persons
    person1_id, person2_id, person3_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    mock_persons_page1 = [
        create_mock_person(person1_id, "Person", "One", tree_id=tree_id),
        create_mock_person(person2_id, "Person", "Two", tree_id=tree_id)
    ]
    # This person would be on page 2
    # mock_person3 = create_mock_person(person3_id, "Person", "Three", tree_id=tree_id)


    # Mock relationships (only between persons on page 1 for this test)
    relationship1_id = uuid.uuid4()
    mock_relationships = [
        create_mock_relationship(relationship1_id, person1_id, person2_id)
    ]
    
    # Mock events (empty for simplicity for now)
    mock_events = []

    # Mock paginate_query result for Persons
    mock_paginated_persons_result = {
        "items": mock_persons_page1,
        "total_items": 3, # Total 3 persons in the tree
        "total_pages": 2,
        "current_page": page,
        "per_page": per_page,
        "has_next_page": True,
        "has_prev_page": False,
    }

    with patch('services.tree_service._get_or_404', return_value=mock_tree) as mock_get_or_404, \
         patch('services.tree_service.paginate_query', return_value=mock_paginated_persons_result) as mock_paginate_query, \
         patch.object(mock_db_session, 'query') as mock_db_query:

        # Mock relationship query
        # This query should filter for relationships involving person1_id or person2_id
        rel_query_mock = MagicMock()
        rel_query_mock.all.return_value = mock_relationships 
        
        # Mock event query
        event_query_mock = MagicMock()
        event_query_mock.all.return_value = mock_events

        # Configure the db.query(Relationship) and db.query(Event) calls
        def query_side_effect(model):
            if model == Relationship:
                return rel_query_mock
            elif model == Person: # This is for the persons_query inside the service
                # The actual persons_query is passed to paginate_query, so paginate_query handles its execution.
                # We don't need to mock its .all() or similar here directly for this test structure.
                # We just need to ensure db.query(Person) returns something that paginate_query can use.
                return MagicMock() 
            elif model == Event:
                return event_query_mock
            elif model == Tree: # For _get_or_404
                 # This is handled by mock_get_or_404, but if db.query(Tree) is called directly
                tree_query_mock = MagicMock()
                tree_query_mock.filter.return_value.one_or_none.return_value = mock_tree
                return tree_query_mock
            return MagicMock() # Default mock for other queries
        
        mock_db_query.side_effect = query_side_effect

        result = get_tree_data_for_visualization_db(mock_db_session, tree_id, page, per_page)

        mock_get_or_404.assert_called_once_with(mock_db_session, Tree, tree_id)
        
        # Assert paginate_query was called for Person
        # The first argument to paginate_query is the SQLAlchemy query object. 
        # We can check the model it's querying if needed, or be less specific.
        mock_paginate_query.assert_called_once()
        call_args = mock_paginate_query.call_args[0]
        assert call_args[1] == Person # Check model being paginated
        assert call_args[2] == page
        assert call_args[3] == per_page
        assert call_args[4] == app_config.PAGINATION_DEFAULTS["max_per_page"]
        # Default sort_by is "created_at", sort_order is "asc"
        assert call_args[5] == "created_at" 
        assert call_args[6] == "asc"

        # Assert nodes
        assert len(result["nodes"]) == per_page
        assert result["nodes"][0]["id"] == str(person1_id)
        assert result["nodes"][1]["id"] == str(person2_id)

        # Assert links (only relationship between person1 and person2 should be present)
        assert len(result["links"]) == 1
        assert result["links"][0]["id"] == str(relationship1_id)
        assert result["links"][0]["source"] == str(person1_id)
        assert result["links"][0]["target"] == str(person2_id)
        
        # Assert relationship query was filtered for persons on the current page
        # This is a bit tricky to assert directly on the filter condition with complex ORs.
        # Instead, we check that db.query(Relationship) was called, and trust the logic inside the function
        # based on the fact that we only provided relationships for page 1 persons.
        # A more robust way would be to capture the filter arguments.
        # For this example, we'll check that the query for relationships was made.
        assert rel_query_mock.filter.called # Check that filter was applied on relationship query

        # Assert pagination metadata
        assert result["pagination"]["current_page"] == page
        assert result["pagination"]["per_page"] == per_page
        assert result["pagination"]["total_items"] == 3
        assert result["pagination"]["total_pages"] == 2
        assert result["pagination"]["has_next_page"] is True


def test_get_tree_data_visualization_last_page(mock_db_session, mock_tree):
    """Test last page request for tree visualization data."""
    page = 2 
    per_page = 2
    tree_id = mock_tree.id

    person3_id = uuid.uuid4()
    mock_persons_page2 = [
        create_mock_person(person3_id, "Person", "Three", tree_id=tree_id)
    ]

    mock_paginated_persons_result = {
        "items": mock_persons_page2,
        "total_items": 3,
        "total_pages": 2,
        "current_page": page,
        "per_page": per_page,
        "has_next_page": False, # Key check for last page
        "has_prev_page": True,
    }
    
    # No relationships for this single person on the last page in this scenario
    mock_relationships_page2 = []
    mock_events_page2 = []

    with patch('services.tree_service._get_or_404', return_value=mock_tree), \
         patch('services.tree_service.paginate_query', return_value=mock_paginated_persons_result) as mock_paginate_query, \
         patch.object(mock_db_session, 'query') as mock_db_query:

        rel_query_mock = MagicMock()
        rel_query_mock.all.return_value = mock_relationships_page2
        event_query_mock = MagicMock()
        event_query_mock.all.return_value = mock_events_page2
        
        def query_side_effect(model):
            if model == Relationship: return rel_query_mock
            if model == Person: return MagicMock()
            if model == Event: return event_query_mock
            if model == Tree: 
                tree_query_mock = MagicMock()
                tree_query_mock.filter.return_value.one_or_none.return_value = mock_tree
                return tree_query_mock
            return MagicMock()
        mock_db_query.side_effect = query_side_effect

        result = get_tree_data_for_visualization_db(mock_db_session, tree_id, page, per_page)
        
        mock_paginate_query.assert_called_once() # Ensure paginate_query was called
        
        assert len(result["nodes"]) == 1 # Only one person on the last page
        assert result["nodes"][0]["id"] == str(person3_id)
        assert len(result["links"]) == 0 # No links for this person
        
        assert result["pagination"]["current_page"] == page
        assert result["pagination"]["has_next_page"] is False
        assert result["pagination"]["total_items"] == 3


def test_get_tree_data_visualization_empty_tree(mock_db_session, mock_tree):
    """Test visualization data for an empty tree."""
    page = 1
    per_page = 10
    tree_id = mock_tree.id

    mock_paginated_persons_result = {
        "items": [], # No persons
        "total_items": 0,
        "total_pages": 0, # Or 1, depending on paginate_query implementation for 0 items
        "current_page": page,
        "per_page": per_page,
        "has_next_page": False,
        "has_prev_page": False,
    }

    with patch('services.tree_service._get_or_404', return_value=mock_tree), \
         patch('services.tree_service.paginate_query', return_value=mock_paginated_persons_result) as mock_paginate_query, \
         patch.object(mock_db_session, 'query') as mock_db_query: # Mock db.query generally

        # Ensure relationship and event queries also return empty when no persons
        rel_query_mock = MagicMock()
        rel_query_mock.all.return_value = []
        event_query_mock = MagicMock()
        event_query_mock.all.return_value = []

        def query_side_effect(model):
            if model == Relationship: return rel_query_mock
            if model == Person: return MagicMock() 
            if model == Event: return event_query_mock
            if model == Tree: 
                tree_query_mock = MagicMock()
                tree_query_mock.filter.return_value.one_or_none.return_value = mock_tree
                return tree_query_mock
            return MagicMock()
        mock_db_query.side_effect = query_side_effect
        
        result = get_tree_data_for_visualization_db(mock_db_session, tree_id, page, per_page)

        mock_paginate_query.assert_called_once()
        assert len(result["nodes"]) == 0
        assert len(result["links"]) == 0
        assert len(result["events"]) == 0
        assert result["pagination"]["total_items"] == 0
        assert result["pagination"]["has_next_page"] is False

def test_get_tree_data_visualization_fewer_persons_than_per_page(mock_db_session, mock_tree):
    """Test when total persons are fewer than per_page."""
    page = 1
    per_page = 10 # Requesting 10
    tree_id = mock_tree.id

    person1_id = uuid.uuid4()
    mock_persons = [create_mock_person(person1_id, "Solo", "Person", tree_id=tree_id)]

    mock_paginated_persons_result = {
        "items": mock_persons,
        "total_items": 1, # Only 1 person in total
        "total_pages": 1,
        "current_page": page,
        "per_page": per_page, # Still reflects requested per_page
        "has_next_page": False,
        "has_prev_page": False,
    }

    with patch('services.tree_service._get_or_404', return_value=mock_tree), \
         patch('services.tree_service.paginate_query', return_value=mock_paginated_persons_result) as mock_paginate_query, \
         patch.object(mock_db_session, 'query') as mock_db_query:
        
        rel_query_mock = MagicMock()
        rel_query_mock.all.return_value = [] # No relationships for a solo person
        event_query_mock = MagicMock()
        event_query_mock.all.return_value = [] # No events for simplicity

        def query_side_effect(model):
            if model == Relationship: return rel_query_mock
            if model == Person: return MagicMock()
            if model == Event: return event_query_mock
            if model == Tree: 
                tree_query_mock = MagicMock()
                tree_query_mock.filter.return_value.one_or_none.return_value = mock_tree
                return tree_query_mock
            return MagicMock()
        mock_db_query.side_effect = query_side_effect

        result = get_tree_data_for_visualization_db(mock_db_session, tree_id, page, per_page)

        mock_paginate_query.assert_called_once()
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["id"] == str(person1_id)
        assert len(result["links"]) == 0
        assert result["pagination"]["total_items"] == 1
        assert result["pagination"]["total_pages"] == 1
        assert result["pagination"]["has_next_page"] is False
        assert result["pagination"]["current_page"] == page
        assert result["pagination"]["per_page"] == per_page # per_page in pagination reflects requested
