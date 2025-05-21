import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import uuid

from backend.services.user_service import (
    authenticate_user_db,
    register_user_db,
    request_password_reset_db,
    reset_password_db,
    update_user_role_db,
    delete_user_db,
    _validate_password_complexity, # Also test this directly
    hash_password,
    check_password_hash,
    MIN_PASSWORD_LENGTH,
    PASSWORD_COMPLEXITY_REGEX_STR
)
from backend.models import User, RoleOptions, db
from backend.config import Config

# Helper to create a user directly for service tests
def create_user_for_service_test(session, username, email, password_plain, role=RoleOptions.USER, is_active=True):
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password_plain),
        role=role,
        is_active=is_active,
        full_name=username.capitalize()
    )
    session.add(user)
    session.commit()
    return user

# --- Test _validate_password_complexity ---
def test_validate_password_complexity_success():
    assert _validate_password_complexity("SecurePass1!") is None # Should not raise

def test_validate_password_complexity_too_short():
    with pytest.raises(ValueError) as excinfo:
        _validate_password_complexity("Short1!")
    assert f"Password must be at least {MIN_PASSWORD_LENGTH} characters long" in str(excinfo.value)

def test_validate_password_complexity_no_uppercase():
    with pytest.raises(ValueError) as excinfo:
        _validate_password_complexity("securepass1!")
    assert "Password does not meet complexity requirements" in str(excinfo.value)
    assert f"Regex: {PASSWORD_COMPLEXITY_REGEX_STR}" in str(excinfo.value)

def test_validate_password_complexity_no_lowercase():
    with pytest.raises(ValueError) as excinfo:
        _validate_password_complexity("SECUREPASS1!")
    assert "Password does not meet complexity requirements" in str(excinfo.value)

def test_validate_password_complexity_no_digit():
    with pytest.raises(ValueError) as excinfo:
        _validate_password_complexity("SecurePass!")
    assert "Password does not meet complexity requirements" in str(excinfo.value)

def test_validate_password_complexity_no_special():
    with pytest.raises(ValueError) as excinfo:
        _validate_password_complexity("SecurePass1")
    assert "Password does not meet complexity requirements" in str(excinfo.value)


# --- Test authenticate_user_db ---
def test_authenticate_user_db_success(db_session, test_user): # test_user fixture creates user with "SecurePassword123!"
    user = authenticate_user_db(db_session, test_user.username, "SecurePassword123!")
    assert user is not None
    assert user.username == test_user.username

def test_authenticate_user_db_inactive_user(db_session):
    inactive = create_user_for_service_test(db_session, "inactive_svc", "inactive_svc@example.com", "SecurePassword123!", is_active=False)
    user = authenticate_user_db(db_session, inactive.username, "SecurePassword123!")
    assert user is None # Or raise specific exception if designed that way

def test_authenticate_user_db_wrong_password(db_session, test_user):
    user = authenticate_user_db(db_session, test_user.username, "WrongPassword!")
    assert user is None

def test_authenticate_user_db_user_not_found(db_session):
    user = authenticate_user_db(db_session, "nonexistentuser", "SecurePassword123!")
    assert user is None

def test_authenticate_user_db_case_insensitive_username(db_session, test_user):
    # Assuming test_user.username is 'testuser'
    user = authenticate_user_db(db_session, "TestUser", "SecurePassword123!") # Different case
    assert user is not None
    assert user.username == test_user.username

def test_authenticate_user_db_case_insensitive_email(db_session, test_user):
    # Assuming test_user.email is 'test@example.com'
    user = authenticate_user_db(db_session, "Test@Example.com", "SecurePassword123!") # Different case
    assert user is not None
    assert user.email == test_user.email


# --- Test register_user_db ---
def test_register_user_db_success(db_session):
    user = register_user_db(db_session, "newreguser", "newreg@example.com", "RegistPass123!", "New Reg User")
    assert user is not None
    assert user.username == "newreguser"
    assert user.email == "newreg@example.com"
    assert user.full_name == "New Reg User"
    assert user.role == RoleOptions.USER
    assert user.is_active is True
    assert check_password_hash(user.hashed_password, "RegistPass123!")

def test_register_user_db_duplicate_username(db_session, test_user):
    with pytest.raises(IntegrityError): # Assuming DB raises IntegrityError
        register_user_db(db_session, test_user.username, "another_email@example.com", "Password123!")
        db_session.commit() # register_user_db adds, commit here to trigger constraint

def test_register_user_db_duplicate_email(db_session, test_user):
     with pytest.raises(IntegrityError):
        register_user_db(db_session, "another_user", test_user.email, "Password123!")
        db_session.commit()

def test_register_user_db_password_validation_fail(db_session):
    with pytest.raises(ValueError) as excinfo:
        register_user_db(db_session, "weakpassuser2", "weakpass2@example.com", "weak", "Weak User")
    assert "Password must be at least" in str(excinfo.value)


# --- Test request_password_reset_db ---
@patch('backend.services.user_service.send_password_reset_email_celery')
def test_request_password_reset_db_success(mock_send_email, db_session, test_user):
    success = request_password_reset_db(db_session, test_user.email, "http://localhost:3000/reset")
    assert success is True
    mock_send_email.delay.assert_called_once()
    # Check token and expiry on user object
    user_reloaded = db_session.query(User).get(test_user.id)
    assert user_reloaded.password_reset_token is not None
    assert user_reloaded.password_reset_expires > datetime.utcnow()

@patch('backend.services.user_service.send_password_reset_email_celery')
def test_request_password_reset_db_user_not_found(mock_send_email, db_session):
    success = request_password_reset_db(db_session, "nonexistent@example.com", "http://localhost:3000/reset")
    assert success is False # Service indicates user not found or email not sent
    mock_send_email.delay.assert_not_called()

@patch('backend.services.user_service.send_password_reset_email_celery')
def test_request_password_reset_db_missing_frontend_url(mock_send_email, db_session, test_user, monkeypatch):
    monkeypatch.setattr(Config, 'FRONTEND_APP_URL', None)
    with pytest.raises(ValueError) as excinfo: # Or check for logged error and False return
         request_password_reset_db(db_session, test_user.email) # Call without frontend_url_base
    assert "FRONTEND_APP_URL is not configured" in str(excinfo.value) # Assuming it raises an error
    mock_send_email.delay.assert_not_called()
    monkeypatch.undo() # Clean up

# --- Test reset_password_db ---
def test_reset_password_db_success(db_session, test_user):
    token = str(uuid.uuid4())
    test_user.password_reset_token = token
    test_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    db_session.add(test_user)
    db_session.commit()

    success = reset_password_db(db_session, token, "NewerPassword123!")
    assert success is True
    user_reloaded = db_session.query(User).get(test_user.id)
    assert user_reloaded.password_reset_token is None
    assert user_reloaded.password_reset_expires is None
    assert check_password_hash(user_reloaded.hashed_password, "NewerPassword123!")

def test_reset_password_db_invalid_token(db_session):
    success = reset_password_db(db_session, "invalid-token", "NewerPassword123!")
    assert success is False

def test_reset_password_db_expired_token(db_session, test_user):
    token = str(uuid.uuid4())
    test_user.password_reset_token = token
    test_user.password_reset_expires = datetime.utcnow() - timedelta(hours=1) # Expired
    db_session.add(test_user)
    db_session.commit()
    
    success = reset_password_db(db_session, token, "NewerPassword123!")
    assert success is False

def test_reset_password_db_weak_new_password(db_session, test_user):
    token = str(uuid.uuid4())
    test_user.password_reset_token = token
    test_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    db_session.add(test_user)
    db_session.commit()

    with pytest.raises(ValueError) as excinfo: # Assuming _validate_password_complexity is called
        reset_password_db(db_session, token, "weak")
    assert "Password does not meet complexity requirements" in str(excinfo.value)


# --- Test update_user_role_db ---
def test_update_user_role_db_success(db_session, test_user):
    updated_user = update_user_role_db(db_session, str(test_user.id), RoleOptions.ADMIN)
    assert updated_user is not None
    assert updated_user.role == RoleOptions.ADMIN
    user_reloaded = db_session.query(User).get(test_user.id)
    assert user_reloaded.role == RoleOptions.ADMIN

def test_update_user_role_db_user_not_found(db_session):
    non_existent_uuid = str(uuid.uuid4())
    updated_user = update_user_role_db(db_session, non_existent_uuid, RoleOptions.ADMIN)
    assert updated_user is None

def test_update_user_role_db_same_role(db_session, test_user):
    initial_role = test_user.role
    updated_user = update_user_role_db(db_session, str(test_user.id), initial_role)
    assert updated_user is not None
    assert updated_user.role == initial_role # No change, but successful operation

def test_update_user_role_db_invalid_role_string(db_session, test_user):
    with pytest.raises(ValueError): # Or specific error type if service handles it
        update_user_role_db(db_session, str(test_user.id), "invalid_role_value")

# --- Test delete_user_db ---
def test_delete_user_db_success(db_session, test_user):
    user_id_str = str(test_user.id)
    success = delete_user_db(db_session, user_id_str)
    assert success is True
    deleted_user = db_session.query(User).get(user_id_str)
    assert deleted_user is None

def test_delete_user_db_user_not_found(db_session):
    non_existent_uuid = str(uuid.uuid4())
    success = delete_user_db(db_session, non_existent_uuid)
    assert success is False

# Add test for IntegrityError when deleting user with dependent data if applicable
# e.g., if a user has trees and on_delete is RESTRICT for user_id in Tree.
# This depends on your model's cascade/deletion rules.
# For example:
# def test_delete_user_db_with_dependencies(db_session, test_user_with_tree):
#     with pytest.raises(IntegrityError): # Or check for False return and logged error
#         delete_user_db(db_session, str(test_user_with_tree.id))
#         db_session.commit() # To trigger the constraint if not immediate
