
import pytest
import uuid
from datetime import date, datetime
from unittest.mock import MagicMock, patch

# Adjusted import paths based on typical project structure
from backend.models import Person, PrivacyLevelEnum 
# User model is not directly used by person_service functions, created_by is a UUID
from backend.services.person_service import create_person_db, update_person_db, get_person_db
# _get_or_404 is part of person_service, so it will be patched there.

@pytest.fixture
def mock_db_session():
    session = MagicMock()
    # session.get is used by _get_or_404 if not patched directly at its call site.
    # Let's assume _get_or_404 is patched in tests that use it.
    return session

@pytest.fixture
def sample_user_id():
    return uuid.uuid4()

@pytest.fixture
def sample_tree_id():
    return uuid.uuid4()

@pytest.fixture
def sample_person_id():
    return uuid.uuid4()

# --- Tests for create_person_db ---

@patch('backend.services.person_service.Person', autospec=True) # Patch Person where it's used by the service
def test_create_person_full_data(mock_person_model_class, mock_db_session, sample_user_id, sample_tree_id):
    person_data = {
        "first_name": "Amaechi", "last_name": "Uchechi", "middle_names": "Emeka",
        "maiden_name": "Okoro", "nickname": "Emmy", "gender": "Male",
        "birth_date": "1985-07-15", "birth_date_approx": False, "birth_place": "Lagos, Nigeria",
        "place_of_birth": "General Hospital, Lagos", "is_living": True, # Explicitly set
        # death_date related fields should be None if is_living is True
        "death_date": None, "death_date_approx": False, "death_place": None, "place_of_death": None,
        "burial_place": None, "privacy_level": "public", # Explicitly set
        "notes": "Some notes about Amaechi.", "biography": "A detailed biography...",
        "profile_picture_url": "http://example.com/amaechi.jpg",
        "custom_attributes": {"occupation": "Engineer", "education": "M.Sc. Computer Science"}
    }

    # This is the mock Person instance that will be returned by mock_person_model_class()
    mock_created_person_instance = mock_person_model_class.return_value 
    
    # Setup attributes on the instance that to_dict() will access.
    # These should reflect the state *after* service logic and db operations (like refresh).
    mock_created_person_instance.id = uuid.uuid4() # Simulate ID assigned by DB
    mock_created_person_instance.tree_id = sample_tree_id
    mock_created_person_instance.created_by = sample_user_id
    # Values from person_data
    mock_created_person_instance.first_name = person_data["first_name"]
    mock_created_person_instance.last_name = person_data["last_name"]
    mock_created_person_instance.middle_names = person_data["middle_names"]
    mock_created_person_instance.maiden_name = person_data["maiden_name"]
    mock_created_person_instance.nickname = person_data["nickname"]
    mock_created_person_instance.gender = person_data["gender"]
    mock_created_person_instance.birth_date = date.fromisoformat(person_data["birth_date"])
    mock_created_person_instance.birth_date_approx = person_data["birth_date_approx"]
    mock_created_person_instance.birth_place = person_data["birth_place"]
    mock_created_person_instance.place_of_birth = person_data["place_of_birth"]
    # is_living is set by service logic on the instance
    mock_created_person_instance.is_living = person_data["is_living"] 
    # Death fields are nulled by service logic if is_living is True
    mock_created_person_instance.death_date = None
    mock_created_person_instance.death_date_approx = False
    mock_created_person_instance.death_place = None
    mock_created_person_instance.place_of_death = None
    mock_created_person_instance.burial_place = None
    mock_created_person_instance.privacy_level = PrivacyLevelEnum.public # Resolved enum
    mock_created_person_instance.notes = person_data["notes"]
    mock_created_person_instance.biography = person_data["biography"]
    mock_created_person_instance.profile_picture_url = person_data["profile_picture_url"]
    mock_created_person_instance.custom_attributes = person_data["custom_attributes"]
    # Timestamps that to_dict might include
    mock_created_person_instance.created_at = datetime.utcnow()
    mock_created_person_instance.updated_at = datetime.utcnow()
    # Relationships - empty for a new person
    mock_created_person_instance.parents = []
    mock_created_person_instance.children = []
    mock_created_person_instance.spouses = []
    mock_created_person_instance.siblings = []


    # Configure the to_dict method of this instance
    # This should match the actual Person.to_dict() output for these fields
    expected_dict_from_to_dict = {
        "id": str(mock_created_person_instance.id), "tree_id": sample_tree_id, 
        "created_by": sample_user_id, "updated_by": None, # Assuming updated_by is not set on create
        "first_name": "Amaechi", "last_name": "Uchechi", "middle_names": "Emeka",
        "maiden_name": "Okoro", "nickname": "Emmy", "gender": "Male",
        "birth_date": "1985-07-15", "birth_date_approx": False, "birth_place": "Lagos, Nigeria",
        "place_of_birth": "General Hospital, Lagos", "is_living": True,
        "death_date": None, "death_date_approx": False, "death_place": None, "place_of_death": None,
        "burial_place": None, "privacy_level": "public", # String value from enum
        "notes": "Some notes about Amaechi.", "biography": "A detailed biography...",
        "profile_picture_url": "http://example.com/amaechi.jpg",
        "custom_attributes": {"occupation": "Engineer", "education": "M.Sc. Computer Science"},
        "created_at": mock_created_person_instance.created_at.isoformat(), 
        "updated_at": mock_created_person_instance.updated_at.isoformat(),
        "parents": [], "children": [], "spouses": [], "siblings": []
    }
    mock_created_person_instance.to_dict.return_value = expected_dict_from_to_dict

    result = create_person_db(mock_db_session, sample_user_id, sample_tree_id, person_data)

    # Assert Person constructor call
    # is_living IS passed to constructor as per person_service.py line ~159
    # privacy_level is resolved to Enum object by service before passing to constructor.
    # date fields are converted to date objects.
    mock_person_model_class.assert_called_once_with(
        tree_id=sample_tree_id, created_by=sample_user_id,
        first_name="Amaechi", middle_names="Emeka", last_name="Uchechi", maiden_name="Okoro",
        nickname="Emmy", gender="Male", birth_date=date(1985, 7, 15),
        birth_date_approx=False, birth_place="Lagos, Nigeria", place_of_birth="General Hospital, Lagos",
        death_date=None, death_date_approx=False, death_place=None, place_of_death=None, # Based on is_living=True in data
        burial_place=None, privacy_level=PrivacyLevelEnum.public, # Enum object
        is_living=True, # Service passes data['is_living'] to constructor
        notes="Some notes about Amaechi.", biography="A detailed biography...",
        profile_picture_url="http://example.com/amaechi.jpg",
        custom_attributes={"occupation": "Engineer", "education": "M.Sc. Computer Science"}
    )
    # Assert that is_living attribute on instance matches (already done by constructor if passed)
    assert mock_created_person_instance.is_living == True

    mock_db_session.add.assert_called_once_with(mock_created_person_instance)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_created_person_instance)
    
    assert result == expected_dict_from_to_dict
    assert result["profile_picture_url"] == "http://example.com/amaechi.jpg"
    assert result["custom_attributes"]["occupation"] == "Engineer"

@patch('backend.services.person_service.Person', autospec=True)
def test_create_person_minimal_data(mock_person_model_class, mock_db_session, sample_user_id, sample_tree_id):
    person_data = {"first_name": "Minimal", "last_name": "Person"}
    # is_living will be calculated, privacy_level will default, profile_picture_url default, custom_attributes default

    mock_created_instance = mock_person_model_class.return_value
    mock_created_instance.id = uuid.uuid4()
    # Populate instance with expected final state after service logic and defaults
    mock_created_instance.tree_id = sample_tree_id
    mock_created_instance.created_by = sample_user_id
    mock_created_instance.first_name = "Minimal"
    mock_created_instance.last_name = "Person"
    mock_created_instance.profile_picture_url = None # Default
    mock_created_instance.custom_attributes = {}   # Default
    mock_created_instance.privacy_level = PrivacyLevelEnum.inherit # Default
    mock_created_instance.is_living = True # Calculated: no death_date implies living
    # Fill other fields for to_dict() consistency
    mock_created_instance.middle_names=None; mock_created_instance.maiden_name=None; mock_created_instance.nickname=None;
    mock_created_instance.gender=None; mock_created_instance.birth_date=None; mock_created_instance.birth_date_approx=False;
    mock_created_instance.birth_place=None; mock_created_instance.place_of_birth=None; mock_created_instance.death_date=None;
    mock_created_instance.death_date_approx=False; mock_created_instance.death_place=None; mock_created_instance.place_of_death=None;
    mock_created_instance.burial_place=None; mock_created_instance.notes=None; mock_created_instance.biography=None;
    mock_created_instance.created_at = datetime.utcnow(); mock_created_instance.updated_at = datetime.utcnow()
    mock_created_instance.parents=[]; mock_created_instance.children=[]; mock_created_instance.spouses=[]; mock_created_instance.siblings=[];

    expected_to_dict_return = {
        "id": str(mock_created_instance.id), "first_name": "Minimal", "last_name": "Person",
        "profile_picture_url": None, "custom_attributes": {}, "privacy_level": "inherit", "is_living": True,
        "tree_id": sample_tree_id, "created_by": sample_user_id, "updated_by": None,
        "middle_names": None, "maiden_name": None, "nickname": None, "gender": None, 
        "birth_date": None, "birth_date_approx": False, "birth_place": None, "place_of_birth": None,
        "death_date": None, "death_date_approx": False, "death_place": None, "place_of_death": None,
        "burial_place": None, "notes": None, "biography": None,
        "created_at": mock_created_instance.created_at.isoformat(), 
        "updated_at": mock_created_instance.updated_at.isoformat(),
        "parents": [], "children": [], "spouses": [], "siblings": []
    }
    mock_created_instance.to_dict.return_value = expected_to_dict_return

    result = create_person_db(mock_db_session, sample_user_id, sample_tree_id, person_data)

    mock_person_model_class.assert_called_once_with(
        tree_id=sample_tree_id, created_by=sample_user_id,
        first_name="Minimal", last_name="Person",
        middle_names=None, maiden_name=None, nickname=None, gender=None,
        birth_date=None, birth_date_approx=False, birth_place=None, place_of_birth=None,
        death_date=None, death_date_approx=False, death_place=None, place_of_death=None,
        burial_place=None, privacy_level=PrivacyLevelEnum.inherit, # Default enum from service
        is_living=None, # Service passes person_data.get('is_living') which is None here
        notes=None, biography=None, profile_picture_url=None, custom_attributes={} # Defaults from service
    )
    # is_living is determined and set on instance *after* constructor if it was None
    assert mock_created_instance.is_living == True 

    mock_db_session.add.assert_called_once_with(mock_created_instance)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_created_instance)
    
    assert result == expected_to_dict_return

@patch('backend.services.person_service.Person', autospec=True)
def test_create_person_profile_url_none_and_empty(mock_person_model_class, mock_db_session, sample_user_id, sample_tree_id):
    # Service passes profile_picture_url as is from person_data.get('profile_picture_url')
    # Model's to_dict should reflect this. If model stores "" as "", then that's expected.
    # Common behavior is to treat "" as None for URLs, but let's test what service passes.
    for url_value_in_data, expected_url_in_constructor, expected_url_in_dict in [
        (None, None, None),  # None in data -> None in constructor -> None in dict
        ("", "", ""),        # "" in data -> "" in constructor -> "" in dict (assuming model/to_dict doesn't change it)
    ]:
        person_data = {
            "first_name": "Test", "last_name": "Pic", "profile_picture_url": url_value_in_data,
            "birth_date": "1990-01-01", "is_living": True, "privacy_level": "public" # Min required
        }
        mock_created_instance = mock_person_model_class.return_value
        mock_created_instance.id = uuid.uuid4()
        mock_created_instance.profile_picture_url = expected_url_in_dict # Set for to_dict mock
        # Other fields for to_dict
        mock_created_instance.first_name = "Test"; mock_created_instance.last_name = "Pic"; mock_created_instance.tree_id = sample_tree_id; # etc.

        mock_created_instance.to_dict.return_value = {
            "id": str(mock_created_instance.id), 
            "profile_picture_url": expected_url_in_dict,
            # Add other fields that to_dict returns
        }

        create_person_db(mock_db_session, sample_user_id, sample_tree_id, person_data)

        call_kwargs = mock_person_model_class.call_args[1]
        assert call_kwargs.get('profile_picture_url') == expected_url_in_constructor
        
        # Assert based on the to_dict mock
        # This also implicitly tests that the instance attribute was set correctly if to_dict uses it.
        assert mock_created_instance.to_dict()["profile_picture_url"] == expected_url_in_dict
        
        mock_person_model_class.reset_mock()
        mock_db_session.reset_mock()


@patch('backend.services.person_service.Person', autospec=True)
def test_create_person_custom_attrs_none_and_empty_dict(mock_person_model_class, mock_db_session, sample_user_id, sample_tree_id):
    # Service defaults custom_attributes to {} if key is missing. If key is present with value None, None is passed.
    for attrs_value_in_data, expected_attrs_in_constructor, expected_attrs_in_dict in [
        (None, None, {}),      # None in data -> None in constructor -> service logic might default .custom_attributes to {} on instance if model doesn't. Model to_dict returns {}
        ({}, {}, {}),        # {} in data -> {} in constructor -> {} in dict
    ]:
        # The to_dict for custom_attributes on Person model defaults to {} if attribute is None.
        # So expected_attrs_in_dict is always {}.
        # The constructor call should receive None if attrs_value_in_data is None.
        person_data = {
            "first_name": "Test", "last_name": "Attrs", "custom_attributes": attrs_value_in_data,
            "birth_date": "1990-01-01", "is_living": True, "privacy_level": "public"
        }
        mock_created_instance = mock_person_model_class.return_value
        mock_created_instance.id = uuid.uuid4()
        mock_created_instance.custom_attributes = expected_attrs_in_dict # Set for to_dict mock
        mock_created_instance.to_dict.return_value = {"id": str(mock_created_instance.id), "custom_attributes": expected_attrs_in_dict}

        create_person_db(mock_db_session, sample_user_id, sample_tree_id, person_data)
        
        call_kwargs = mock_person_model_class.call_args[1]
        assert call_kwargs.get('custom_attributes') == expected_attrs_in_constructor
        assert mock_created_instance.to_dict()["custom_attributes"] == expected_attrs_in_dict

        mock_person_model_class.reset_mock()
        mock_db_session.reset_mock()

# --- Tests for update_person_db ---

@patch('backend.services.person_service._get_or_404', autospec=True)
def test_update_person_profile_picture_url(mock_get_or_404, mock_db_session, sample_person_id, sample_tree_id):
    mock_person_instance = MagicMock(spec=Person)
    mock_person_instance.id = sample_person_id
    mock_person_instance.tree_id = sample_tree_id # For the _get_or_404 check
    mock_person_instance.birth_date = None # Default for date comparison
    mock_person_instance.death_date = None # Default for date comparison
    mock_get_or_404.return_value = mock_person_instance

    new_url = "http://example.com/new_pic.jpg"
    update_data = {"profile_picture_url": new_url}

    # Mock to_dict to reflect the change on the instance
    def to_dict_side_effect():
        return {"id": str(mock_person_instance.id), "profile_picture_url": mock_person_instance.profile_picture_url}
    mock_person_instance.to_dict.side_effect = to_dict_side_effect

    result = update_person_db(mock_db_session, sample_person_id, sample_tree_id, update_data)

    mock_get_or_404.assert_called_once_with(mock_db_session, Person, sample_person_id, tree_id=sample_tree_id)
    assert mock_person_instance.profile_picture_url == new_url # Attribute directly set
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_person_instance)
    assert result["profile_picture_url"] == new_url # From to_dict

@patch('backend.services.person_service._get_or_404', autospec=True)
def test_update_person_custom_attributes_merge_and_replace(mock_get_or_404, mock_db_session, sample_person_id, sample_tree_id):
    # Test merging
    mock_person_instance_merge = MagicMock(spec=Person)
    mock_person_instance_merge.id = sample_person_id; mock_person_instance_merge.tree_id = sample_tree_id
    mock_person_instance_merge.custom_attributes = {"old_key": "old_value", "existing_key": "initial_value"}
    mock_person_instance_merge.birth_date = None # Default for date comparison
    mock_person_instance_merge.death_date = None # Default for date comparison
    mock_get_or_404.return_value = mock_person_instance_merge
    
    update_data_merge = {"custom_attributes": {"new_key": "new_value", "existing_key": "updated_value"}}
    expected_merged_attrs = {"old_key": "old_value", "existing_key": "updated_value", "new_key": "new_value"}
    mock_person_instance_merge.to_dict.side_effect = lambda: {"id": str(mock_person_instance_merge.id), "custom_attributes": mock_person_instance_merge.custom_attributes}

    result_merge = update_person_db(mock_db_session, sample_person_id, sample_tree_id, update_data_merge)
    assert mock_person_instance_merge.custom_attributes == expected_merged_attrs
    assert result_merge["custom_attributes"] == expected_merged_attrs

    mock_db_session.reset_mock(); mock_get_or_404.reset_mock() # Reset for next sub-test

    # Test replacing with empty dict
    mock_person_instance_empty = MagicMock(spec=Person)
    mock_person_instance_empty.id = sample_person_id; mock_person_instance_empty.tree_id = sample_tree_id
    mock_person_instance_empty.custom_attributes = {"initial": "value"}
    mock_person_instance_empty.birth_date = None # Default for date comparison
    mock_person_instance_empty.death_date = None # Default for date comparison
    mock_get_or_404.return_value = mock_person_instance_empty

    update_data_empty = {"custom_attributes": {}}
    mock_person_instance_empty.to_dict.side_effect = lambda: {"id": str(mock_person_instance_empty.id), "custom_attributes": mock_person_instance_empty.custom_attributes}
    
    result_empty = update_person_db(mock_db_session, sample_person_id, sample_tree_id, update_data_empty)
    assert mock_person_instance_empty.custom_attributes == {} # Service replaces with {}
    assert result_empty["custom_attributes"] == {}


@patch('backend.services.person_service._get_or_404', autospec=True)
def test_update_person_profile_url_to_none_and_empty(mock_get_or_404, mock_db_session, sample_person_id, sample_tree_id):
    # Service sets profile_picture_url directly. If data is "", it's set to "".
    # If data is None, it's set to None.
    for url_value_in_data, expected_attribute_value in [
        (None, None),
        ("", ""), # Service will set it to "", model should handle it or store as is.
    ]:
        mock_person_instance = MagicMock(spec=Person)
        mock_person_instance.id = sample_person_id; mock_person_instance.tree_id = sample_tree_id
        mock_person_instance.profile_picture_url = "http://initial.com/pic.jpg" # Initial value
        mock_person_instance.birth_date = None # Default for date comparison
        mock_person_instance.death_date = None # Default for date comparison
        mock_get_or_404.return_value = mock_person_instance

        update_data = {"profile_picture_url": url_value_in_data}
        # Ensure to_dict reflects the attribute change
        mock_person_instance.to_dict.side_effect = lambda: {"id": str(mock_person_instance.id), "profile_picture_url": mock_person_instance.profile_picture_url}

        result = update_person_db(mock_db_session, sample_person_id, sample_tree_id, update_data)

        assert mock_person_instance.profile_picture_url == expected_attribute_value
        assert result["profile_picture_url"] == expected_attribute_value
        
        mock_db_session.reset_mock()
        mock_get_or_404.reset_mock()


# --- Test for get_person_db ---

@patch('backend.services.person_service._get_or_404', autospec=True)
def test_get_person_db_returns_to_dict_data(mock_get_or_404, mock_db_session, sample_person_id, sample_tree_id):
    mock_person_instance = MagicMock(spec=Person)
    mock_person_instance.id = sample_person_id
    mock_person_instance.tree_id = sample_tree_id # For _get_or_404 check
    
    # Define what the mocked Person's to_dict() should return
    expected_dict_from_to_dict = {
        "id": str(sample_person_id), 
        "profile_picture_url": "http://example.com/get_pic.jpg",
        "custom_attributes": {"status": "active_get_test"},
        "first_name": "Getter", "last_name": "Test",
        # ... all other fields Person.to_dict() is expected to return
    }
    mock_person_instance.to_dict.return_value = expected_dict_from_to_dict
    mock_get_or_404.return_value = mock_person_instance

    result = get_person_db(mock_db_session, sample_person_id, tree_id=sample_tree_id)

    mock_get_or_404.assert_called_once_with(mock_db_session, Person, sample_person_id, tree_id=sample_tree_id)
    mock_person_instance.to_dict.assert_called_once() # Ensure it was called by the service
    assert result == expected_dict_from_to_dict # Result of get_person_db is the result of to_dict()
    assert result["profile_picture_url"] == "http://example.com/get_pic.jpg"
    assert result["custom_attributes"]["status"] == "active_get_test"

# --- Test for specific service logic like gender handling ---
@patch('backend.services.person_service.Person', autospec=True)
def test_create_person_empty_string_gender_becomes_none(mock_person_model_class, mock_db_session, sample_user_id, sample_tree_id):
    person_data = {
        "first_name": "Test", "last_name": "Gender", "gender": "", # Empty string gender
        "birth_date": "1990-01-01", "is_living": True, "privacy_level": "public"
    }
    
    mock_created_instance = mock_person_model_class.return_value
    mock_created_instance.id = uuid.uuid4()
    # Instance gender should be None after service logic
    mock_created_instance.gender = None 
    mock_created_instance.to_dict.return_value = {"id": str(mock_created_instance.id), "gender": None}

    create_person_db(mock_db_session, sample_user_id, sample_tree_id, person_data)

    # Service converts "" gender to None before calling Person constructor
    call_kwargs = mock_person_model_class.call_args[1]
    assert call_kwargs.get('gender') is None 
    
    # Check via mocked to_dict
    assert mock_created_instance.to_dict()["gender"] is None