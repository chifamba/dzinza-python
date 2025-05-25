import pytest
from unittest.mock import patch, MagicMock, mock_open
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from flask import Flask, g, abort
import os
import json
import uuid
from datetime import datetime

from utils import (
    load_encryption_key,
    EncryptedString,
    apply_sorting,
    paginate_query,
    get_pagination_params,
    _handle_sqlalchemy_error,
    _get_or_404
)
from models import User  # For _get_or_404 and paginate_query
from config import Config


# --- Test load_encryption_key ---
@patch.dict(os.environ, {'ENCRYPTION_KEY_B64': Fernet.generate_key().decode()})
def test_load_encryption_key_from_env():
    key = load_encryption_key("dummy_path.json")
    assert isinstance(key, bytes)
    assert len(key) == 44 # Fernet keys are base64 encoded, 32 bytes raw

@patch('builtins.open', new_callable=mock_open, read_data=json.dumps({'key_b64': Fernet.generate_key().decode()}))
@patch.dict(os.environ, clear=True) # Ensure env var is not used
def test_load_encryption_key_from_file(mock_file):
    key = load_encryption_key("path/to/encryption_key.json")
    assert isinstance(key, bytes)
    mock_file.assert_called_once_with("path/to/encryption_key.json", 'r')

@patch('builtins.open', side_effect=FileNotFoundError)
@patch.dict(os.environ, clear=True)
def test_load_encryption_key_file_not_found_raises_error(mock_file):
    with pytest.raises(FileNotFoundError): # Or RuntimeError as per current code
        load_encryption_key("path/to/nonexistent_key.json")

@patch('builtins.open', new_callable=mock_open, read_data=json.dumps({'wrong_key_name': 'some_value'}))
@patch.dict(os.environ, clear=True)
def test_load_encryption_key_file_missing_key_b64_raises_error(mock_file):
    with pytest.raises(ValueError) as excinfo: # Or RuntimeError
        load_encryption_key("path/to/invalid_key.json")
    assert "key_b64 not found in encryption key file" in str(excinfo.value)

@patch('builtins.open', new_callable=mock_open, read_data="this is not json")
@patch.dict(os.environ, clear=True)
def test_load_encryption_key_file_invalid_json_raises_error(mock_file):
     with pytest.raises(json.JSONDecodeError): # Or RuntimeError
        load_encryption_key("path/to/bad_json_key.json")

# --- Test EncryptedString TypeDecorator ---
@pytest.fixture
def fernet_instance():
    key = Fernet.generate_key()
    return Fernet(key)

def test_encrypted_string_process_bind_param_with_fernet(fernet_instance):
    decorator = EncryptedString(255, fernet_suite=fernet_instance)
    encrypted_value = decorator.process_bind_param("my secret data", None)
    assert isinstance(encrypted_value, str) # Stored as string in DB
    # Check if it's decryptable
    decrypted = fernet_instance.decrypt(encrypted_value.encode()).decode()
    assert decrypted == "my secret data"

def test_encrypted_string_process_bind_param_none_value(fernet_instance):
    decorator = EncryptedString(255, fernet_suite=fernet_instance)
    assert decorator.process_bind_param(None, None) is None

def test_encrypted_string_process_bind_param_no_fernet():
    decorator = EncryptedString(255, fernet_suite=None)
    # Should ideally log a warning and return the value as is, or raise error
    # Current implementation returns value as is if fernet_suite is None
    assert decorator.process_bind_param("my secret data", None) == "my secret data"


def test_encrypted_string_process_result_value_with_fernet(fernet_instance):
    decorator = EncryptedString(255, fernet_suite=fernet_instance)
    encrypted_data_str = fernet_instance.encrypt("my secret data".encode()).decode()
    decrypted_value = decorator.process_result_value(encrypted_data_str, None)
    assert decrypted_value == "my secret data"

def test_encrypted_string_process_result_value_none_value(fernet_instance):
    decorator = EncryptedString(255, fernet_suite=fernet_instance)
    assert decorator.process_result_value(None, None) is None

def test_encrypted_string_process_result_value_no_fernet():
    decorator = EncryptedString(255, fernet_suite=None)
    # Should return the value as is if fernet_suite is None
    assert decorator.process_result_value("encrypted_looking_string", None) == "encrypted_looking_string"

def test_encrypted_string_process_result_value_invalid_token(fernet_instance):
    decorator = EncryptedString(255, fernet_suite=fernet_instance)
    # This should log an error and return the original (undecryptable) string or None
    # Current implementation logs and returns original value
    original_value = "this is not a valid fernet token"
    result = decorator.process_result_value(original_value, None)
    assert result == original_value # Or check for logged error


# --- Test apply_sorting ---
Base = declarative_base()
class SortableModel(Base):
    __tablename__ = 'sortable_model'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    created_at = Column(String) # Using String for simplicity in this standalone test

def test_apply_sorting_valid_column_asc():
    query = MagicMock()
    sorted_query = apply_sorting(query, SortableModel, "name", "asc")
    query.order_by.assert_called_once()
    call_args = query.order_by.call_args[0][0]
    assert str(call_args) == "sortable_model.name ASC" # Check the SQL expression

def test_apply_sorting_valid_column_desc():
    query = MagicMock()
    sorted_query = apply_sorting(query, SortableModel, "created_at", "desc")
    query.order_by.assert_called_once()
    call_args = query.order_by.call_args[0][0]
    assert str(call_args) == "sortable_model.created_at DESC"

def test_apply_sorting_invalid_column(caplog):
    query = MagicMock()
    sorted_query = apply_sorting(query, SortableModel, "non_existent_column", "asc")
    query.order_by.assert_not_called() # Should not sort by invalid column
    assert "Invalid sort_by column" in caplog.text # Check for log message
    assert sorted_query == query # Returns original query

def test_apply_sorting_no_sort_by():
    query = MagicMock()
    # Assuming default sort by 'id' if not specified and model has 'id'
    # Or, if no default, it shouldn't call order_by.
    # Current `apply_sorting` defaults to model.id if sort_by is None and model has id.
    # If SortableModel had no 'id', it would not sort.
    sorted_query = apply_sorting(query, SortableModel, None, "asc")
    query.order_by.assert_called_once()
    call_args = query.order_by.call_args[0][0]
    assert str(call_args) == "sortable_model.id ASC"


# --- Test paginate_query ---
# This requires a more involved setup with a real session and query object.
# We'll use User model and a mock session for simplicity here,
# but ideally, this would be an integration test.

@pytest.fixture
def mock_user_query_results():
    users = []
    for i in range(15): # Create 15 mock users
        user = MagicMock(spec=User)
        user.id = uuid.uuid4()
        user.username = f"user{i}"
        user.email = f"user{i}@example.com"
        user.role = "user"
        user.full_name = f"User {i}"
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        user.to_dict = MagicMock(return_value={
            'id': str(user.id), 'username': user.username, 'email': user.email,
            'role': user.role, 'full_name': user.full_name,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat()
        })
        users.append(user)
    return users

def test_paginate_query_first_page(mock_user_query_results):
    mock_query = MagicMock()
    mock_query.count.return_value = 15
    mock_query.limit().offset().all.return_value = mock_user_query_results[:5] # Page 1, 5 per page

    result = paginate_query(mock_query, 1, 5, User)
    
    assert len(result['items']) == 5
    assert result['pagination']['total_items'] == 15
    assert result['pagination']['total_pages'] == 3
    assert result['pagination']['page'] == 1
    assert result['pagination']['per_page'] == 5
    assert result['pagination']['has_next'] is True
    assert result['pagination']['has_prev'] is False
    mock_query.limit.assert_called_with(5)
    mock_query.limit().offset.assert_called_with(0)

def test_paginate_query_middle_page(mock_user_query_results):
    mock_query = MagicMock()
    mock_query.count.return_value = 15
    mock_query.limit().offset().all.return_value = mock_user_query_results[5:10] # Page 2, 5 per page

    result = paginate_query(mock_query, 2, 5, User)
    assert len(result['items']) == 5
    assert result['pagination']['page'] == 2
    assert result['pagination']['has_next'] is True
    assert result['pagination']['has_prev'] is True

def test_paginate_query_last_page(mock_user_query_results):
    mock_query = MagicMock()
    mock_query.count.return_value = 15
    mock_query.limit().offset().all.return_value = mock_user_query_results[10:] # Page 3, 5 per page

    result = paginate_query(mock_query, 3, 5, User)
    assert len(result['items']) == 5
    assert result['pagination']['page'] == 3
    assert result['pagination']['has_next'] is False
    assert result['pagination']['has_prev'] is True

def test_paginate_query_empty_result(mock_user_query_results):
    mock_query = MagicMock()
    mock_query.count.return_value = 0
    mock_query.limit().offset().all.return_value = []

    result = paginate_query(mock_query, 1, 5, User)
    assert len(result['items']) == 0
    assert result['pagination']['total_items'] == 0
    assert result['pagination']['total_pages'] == 0 # Or 1, depending on desired behavior for 0 items
    assert result['pagination']['page'] == 1


# --- Test get_pagination_params ---
def test_get_pagination_params_defaults():
    mock_request = MagicMock()
    mock_request.args = {}
    params = get_pagination_params(mock_request)
    assert params['page'] == 1
    assert params['per_page'] == Config.DEFAULT_PER_PAGE
    assert params['sort_by'] is None
    assert params['sort_order'] == 'asc'

def test_get_pagination_params_valid_inputs():
    mock_request = MagicMock()
    mock_request.args = {'page': '2', 'per_page': '20', 'sort_by': 'name', 'sort_order': 'desc'}
    params = get_pagination_params(mock_request)
    assert params['page'] == 2
    assert params['per_page'] == 20
    assert params['sort_by'] == 'name'
    assert params['sort_order'] == 'desc'

def test_get_pagination_params_invalid_numeric():
    mock_request = MagicMock()
    mock_request.args = {'page': 'abc', 'per_page': 'xyz'}
    params = get_pagination_params(mock_request)
    assert params['page'] == 1 # Defaults on error
    assert params['per_page'] == Config.DEFAULT_PER_PAGE # Defaults on error

def test_get_pagination_params_per_page_exceeds_max():
    mock_request = MagicMock()
    mock_request.args = {'per_page': str(Config.MAX_PER_PAGE + 10)}
    params = get_pagination_params(mock_request)
    assert params['per_page'] == Config.MAX_PER_PAGE

def test_get_pagination_params_invalid_sort_order():
    mock_request = MagicMock()
    mock_request.args = {'sort_order': 'diagonal'}
    params = get_pagination_params(mock_request)
    assert params['sort_order'] == 'asc' # Defaults


# --- Test _handle_sqlalchemy_error ---
# This requires a Flask app context to use abort
def test_handle_sqlalchemy_error_integrity_username(app):
    with app.app_context():
        error = IntegrityError("Mock statement", {}, MagicMock(pgcode='23505', diag=MagicMock(constraint_name='users_username_key')))
        with pytest.raises(Exception) as excinfo: # werkzeug.exceptions.HTTPException (Conflict)
             _handle_sqlalchemy_error(error, "User")
        assert excinfo.value.code == 409
        assert "Username already exists" in excinfo.value.description

def test_handle_sqlalchemy_error_integrity_email(app):
    with app.app_context():
        error = IntegrityError("Mock statement", {}, MagicMock(pgcode='23505', diag=MagicMock(constraint_name='users_email_key')))
        with pytest.raises(Exception) as excinfo:
             _handle_sqlalchemy_error(error, "User")
        assert excinfo.value.code == 409
        assert "Email already exists" in excinfo.value.description
        
def test_handle_sqlalchemy_error_integrity_foreign_key(app):
    with app.app_context():
        # Simulate a foreign key violation, e.g., trying to add a person to a non-existent tree
        error = IntegrityError("Mock statement", {}, MagicMock(pgcode='23503', diag=MagicMock(constraint_name='fk_person_tree_id')))
        with pytest.raises(Exception) as excinfo:
            _handle_sqlalchemy_error(error, "Person")
        assert excinfo.value.code == 400 # Or 409 depending on how you want to treat it
        assert "Related resource not found or invalid" in excinfo.value.description # Generic message

def test_handle_sqlalchemy_error_no_result_found(app):
     with app.app_context():
        error = NoResultFound("Mock NoResultFound")
        with pytest.raises(Exception) as excinfo:
            _handle_sqlalchemy_error(error, "Resource")
        assert excinfo.value.code == 404
        assert "Resource not found" in excinfo.value.description

def test_handle_sqlalchemy_error_generic(app, caplog):
    with app.app_context():
        error = IntegrityError("Generic IntegrityError", {}, MagicMock(pgcode='XXXXX')) # Some other code
        with pytest.raises(Exception) as excinfo:
            _handle_sqlalchemy_error(error, "Data")
        assert excinfo.value.code == 500 # Default to 500
        assert "Database error occurred" in excinfo.value.description
        assert "Unhandled SQLAlchemy error" in caplog.text


# --- Test _get_or_404 ---
# Requires Flask app context and a db session with data
def test_get_or_404_found(app, db_session, test_user):
    with app.app_context():
        g.db = db_session # Simulate request context
        found_user = _get_or_404(User, test_user.id)
        assert found_user is not None
        assert found_user.id == test_user.id

def test_get_or_404_not_found(app, db_session):
    with app.app_context():
        g.db = db_session
        non_existent_uuid = uuid.uuid4()
        with pytest.raises(Exception) as excinfo: # werkzeug.exceptions.NotFound
            _get_or_404(User, non_existent_uuid, "Custom User")
        assert excinfo.value.code == 404
        assert "Custom User not found" in excinfo.value.description


def test_get_or_404_with_tree_id_found(app, db_session, sample_person_payload, sample_tree):
    # sample_person_payload needs a person created and associated with sample_tree
    from backend.models import Person
    person = Person(
        id=uuid.uuid4(),
        tree_id=sample_tree.id,
        first_name=sample_person_payload['first_name'],
        last_name=sample_person_payload['last_name'],
        gender=sample_person_payload['gender']
    )
    db_session.add(person)
    db_session.commit()

    with app.app_context():
        g.db = db_session
        g.active_tree_id = str(sample_tree.id) # Simulate decorator setting this
        
        found_person = _get_or_404(Person, person.id, tree_id_attr='tree_id')
        assert found_person is not None
        assert found_person.id == person.id
        assert found_person.tree_id == sample_tree.id

def test_get_or_404_with_tree_id_not_found_in_tree(app, db_session, sample_person_payload, sample_tree, another_tree):
    from backend.models import Person
    person_in_another_tree = Person(
        id=uuid.uuid4(),
        tree_id=another_tree.id, # Belongs to a different tree
        first_name="OtherTree", last_name="Person", gender="male"
    )
    db_session.add(person_in_another_tree)
    db_session.commit()

    with app.app_context():
        g.db = db_session
        g.active_tree_id = str(sample_tree.id) # Current active tree

        with pytest.raises(Exception) as excinfo:
            _get_or_404(Person, person_in_another_tree.id, "Member", tree_id_attr='tree_id')
        assert excinfo.value.code == 404 # Not found in the *active* tree
        assert "Member not found or not accessible in the current tree" in excinfo.value.description
