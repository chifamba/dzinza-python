from unittest.mock import patch, MagicMock
import uuid
import pytest # Added pytest for raises
from werkzeug.exceptions import HTTPException, NotFound # For testing _get_or_404 behavior
from models import User # Assuming models.py is accessible
from services.user_service import (
    _deep_update_dict,
    update_user_profile_db,
    get_user_profile_by_id_db,
    get_user_settings_db, # Added for completeness if tests are written later
    update_user_settings_db, # Added for completeness
    update_user_avatar_path_db # Added for completeness
)
# Placeholder for other imports if needed for more tests later
# e.g. from sqlalchemy.exc import IntegrityError

# --- Tests for User Profile and Settings Service Functions ---

def test_deep_update_dict_simple():
    original = {"a": 1, "b": {"c": 2, "d": 3}}
    update = {"b": {"c": 4, "e": 5}, "f": 6}
    expected = {"a": 1, "b": {"c": 4, "d": 3, "e": 5}, "f": 6}
    assert _deep_update_dict(original, update) == expected

def test_deep_update_dict_add_new_nested():
    original = {"a": 1}
    update = {"b": {"c": 2}}
    expected = {"a": 1, "b": {"c": 2}}
    assert _deep_update_dict(original, update) == expected

def test_deep_update_dict_empty_original():
    original = {}
    update = {"a": 1, "b": {"c": 2}}
    expected = {"a": 1, "b": {"c": 2}}
    assert _deep_update_dict(original, update) == expected

def test_deep_update_dict_empty_update():
    original = {"a": 1, "b": {"c": 2}}
    update = {}
    expected = {"a": 1, "b": {"c": 2}}
    assert _deep_update_dict(original, update) == expected

@patch('services.user_service.log_activity') # Mock the audit logger
@patch('services.user_service._get_or_404')   # Mock fetching the user
def test_update_user_profile_db_success(mock_get_user, mock_log_activity):
    mock_db_session = MagicMock() # Mock SQLAlchemy session
    user_id = uuid.uuid4()

    # Setup mock user object
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.full_name = "Old Name"
    mock_user.email = "old@example.com"
    mock_user.email_verified = True

    mock_get_user.return_value = mock_user # _get_or_404 returns this user

    update_data = {
        "full_name": "New Name",
        "email": "new@example.com"
    }

    updated_user = update_user_profile_db(mock_db_session, user_id, update_data, actor_user_id=user_id)

    assert updated_user is not None
    assert updated_user.full_name == "New Name"
    assert updated_user.email == "new@example.com"
    assert updated_user.email_verified == False # Important check

    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_with(mock_user)

    mock_log_activity.assert_called_once()
    # Example of checking log_activity args (optional, can be very detailed)
    # log_args = mock_log_activity.call_args[1] # Get kwargs
    # assert log_args['action_type'] == "UPDATE_PROFILE"
    # assert log_args['entity_id'] == user_id

@patch('services.user_service._get_or_404')
def test_get_user_profile_db_not_found(mock_get_user):
    mock_db_session = MagicMock()
    user_id_not_found = uuid.uuid4()
    mock_get_user.side_effect = NotFound("User not found") # Simulate _get_or_404 raising NotFound

    with pytest.raises(HTTPException) as exc_info:
        get_user_profile_by_id_db(mock_db_session, user_id_not_found)
    assert exc_info.value.code == 404

# Placeholder test to confirm file creation and test discovery
def test_placeholder_user_service():
    assert True
