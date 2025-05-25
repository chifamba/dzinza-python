import pytest
import json
from flask import session, g
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid

from models import User, RoleOptions
from backend.services.user_service import (
    _validate_password_complexity,
    MIN_PASSWORD_LENGTH,
    PASSWORD_COMPLEXITY_REGEX_STR
)
from config import Config

# Helper to create a user directly in the DB for testing specific states
def create_user_direct(db_session, username, email, password, role=RoleOptions.USER, is_active=True, full_name=None):
    from backend.services.user_service import hash_password # Corrected import
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
        full_name=full_name if full_name else username.capitalize()
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture(scope="function")
def inactive_user_direct(db_session):
    return create_user_direct(db_session, "inactiveuser", "inactive@example.com", "SecurePassword123!", is_active=False)

@pytest.fixture(scope="function")
def user_for_password_reset(db_session):
    return create_user_direct(db_session, "resetuser", "reset@example.com", "SecurePassword123!")


# --- Test Login Endpoint ---
def test_login_success(client, test_user):
    """Test successful login with valid credentials."""
    response = client.post('/api/login', json={
        'username': test_user.username,
        'password': 'SecurePassword123!'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Login successful'
    assert data['user']['username'] == test_user.username
    assert data['user']['role'] == test_user.role.value
    with client.session_transaction() as sess:
        assert sess['user_id'] == str(test_user.id)
        assert sess['username'] == test_user.username
        assert sess['role'] == test_user.role.value

def test_login_inactive_user(client, inactive_user_direct):
    """Test login attempt with an inactive user."""
    response = client.post('/api/login', json={
        'username': inactive_user_direct.username,
        'password': 'SecurePassword123!'
    })
    assert response.status_code == 401
    data = response.get_json()
    assert 'User account is inactive' in data['error']

def test_login_invalid_credentials(client, test_user):
    """Test login with invalid password."""
    response = client.post('/api/login', json={
        'username': test_user.username,
        'password': 'WrongPassword!'
    })
    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == 'Invalid username or password'

def test_login_missing_fields(client):
    """Test login with missing username or password."""
    response = client.post('/api/login', json={'username': 'test'})
    assert response.status_code == 400
    data = response.get_json()
    assert 'Missing username or password' in data.get('error', data.get('message', ''))


    response = client.post('/api/login', json={'password': 'test'})
    assert response.status_code == 400
    data = response.get_json()
    assert 'Missing username or password' in data.get('error', data.get('message', ''))


# --- Test Register Endpoint ---
def test_register_success(client, db_session):
    """Test successful user registration."""
    response = client.post('/api/register', json={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'NewPassword123!',
        'full_name': 'New User'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'User registered successfully'
    assert data['user']['username'] == 'newuser'
    
    user = db_session.query(User).filter_by(username='newuser').first()
    assert user is not None
    assert user.email == 'newuser@example.com'
    assert user.role == RoleOptions.USER # Default role

def test_register_username_exists(client, test_user):
    """Test registration with an existing username."""
    response = client.post('/api/register', json={
        'username': test_user.username, # Existing username
        'email': 'another@example.com',
        'password': 'NewPassword123!',
        'full_name': 'Another User'
    })
    assert response.status_code == 409
    data = response.get_json()
    assert 'Username already exists' in data['error']

def test_register_email_exists(client, test_user):
    """Test registration with an existing email."""
    response = client.post('/api/register', json={
        'username': 'unique_user',
        'email': test_user.email, # Existing email
        'password': 'NewPassword123!',
        'full_name': 'Unique User'
    })
    assert response.status_code == 409
    data = response.get_json()
    assert 'Email already exists' in data['error']

def test_register_invalid_email(client):
    """Test registration with an invalid email format."""
    response = client.post('/api/register', json={
        'username': 'newuser2',
        'email': 'invalid-email',
        'password': 'NewPassword123!',
        'full_name': 'New User Two'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'Invalid email format' in data['error']

def test_register_password_too_short(client):
    """Test registration with a password that is too short."""
    response = client.post('/api/register', json={
        'username': 'shortpassuser',
        'email': 'shortpass@example.com',
        'password': 'Short1!', # Too short
        'full_name': 'Short Pass User'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert f"Password must be at least {MIN_PASSWORD_LENGTH} characters long" in data['error']

def test_register_password_complexity_regex_fail(client):
    """Test registration with a password that fails complexity regex (e.g., no uppercase)."""
    response = client.post('/api/register', json={
        'username': 'weakpassuser',
        'email': 'weakpass@example.com',
        'password': 'weakpassword123!', # No uppercase
        'full_name': 'Weak Pass User'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "Password does not meet complexity requirements" in data['error']
    assert f"Must include uppercase, lowercase, digit, and special character. Regex: {PASSWORD_COMPLEXITY_REGEX_STR}" in data['error']


# --- Test Logout Endpoint ---
def test_logout_success(client, auth_headers):
    """Test successful logout."""
    # First, login to establish a session
    login_response = client.post('/api/login', json={
        'username': 'testuser', # Assuming test_user fixture username
        'password': 'SecurePassword123!'
    })
    assert login_response.status_code == 200

    with client.session_transaction() as sess:
        assert 'user_id' in sess

    # Now, logout
    response = client.post('/api/logout') # No headers needed as it uses session
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Logout successful'
    
    with client.session_transaction() as sess:
        assert 'user_id' not in sess
        assert 'username' not in sess
        assert 'role' not in sess
        assert 'active_tree_id' not in sess # Ensure active_tree_id is also cleared

def test_logout_no_session(client):
    """Test logout when no session exists."""
    response = client.post('/api/logout')
    assert response.status_code == 200 # Or 401 if preferred, current behavior is 200
    data = response.get_json()
    assert data['message'] == 'Logout successful' # Or an appropriate message for no active session


# --- Test Session Endpoint ---
def test_get_session_authenticated(client, test_user, auth_headers):
    """Test /api/session when authenticated."""
    # Login first
    client.post('/api/login', json={'username': test_user.username, 'password': 'SecurePassword123!'})

    response = client.get('/api/session')
    assert response.status_code == 200
    data = response.get_json()
    assert data['isAuthenticated'] is True
    assert data['user']['id'] == str(test_user.id)
    assert data['user']['username'] == test_user.username
    assert data['user']['role'] == test_user.role.value
    assert 'active_tree_id' in data # Should be None if not set

def test_get_session_not_authenticated(client):
    """Test /api/session when not authenticated."""
    response = client.get('/api/session')
    assert response.status_code == 200 # Endpoint itself doesn't require auth
    data = response.get_json()
    assert data['isAuthenticated'] is False
    assert data.get('user') is None
    assert data.get('active_tree_id') is None


# --- Test Password Reset Endpoints ---
@patch('backend.blueprints.auth.send_password_reset_email_celery') # Mock Celery task
def test_request_password_reset_success(mock_send_email, client, user_for_password_reset):
    """Test successful password reset request."""
    response = client.post('/api/request-password-reset', json={
        'email': user_for_password_reset.email
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'If an account with that email exists, a password reset link has been sent.'
    mock_send_email.delay.assert_called_once()
    # Further check: user_for_password_reset should have a token and expiry in DB
    user = User.query.get(user_for_password_reset.id)
    assert user.password_reset_token is not None
    assert user.password_reset_expires > datetime.utcnow()

@patch('backend.blueprints.auth.send_password_reset_email_celery')
def test_request_password_reset_email_not_found(mock_send_email, client):
    """Test password reset request for a non-existent email."""
    response = client.post('/api/request-password-reset', json={
        'email': 'nonexistent@example.com'
    })
    assert response.status_code == 200 # Should not reveal if email exists
    data = response.get_json()
    assert data['message'] == 'If an account with that email exists, a password reset link has been sent.'
    mock_send_email.delay.assert_not_called()

def test_reset_password_success(client, db_session, user_for_password_reset):
    """Test successful password reset with a valid token."""
    # Manually generate a token for the user (simulate what request_password_reset would do)
    token = str(uuid.uuid4())
    user_for_password_reset.password_reset_token = token
    user_for_password_reset.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    db_session.add(user_for_password_reset)
    db_session.commit()

    response = client.post(f'/api/reset-password/{token}', json={
        'new_password': 'NewSecurePassword123!'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Password has been reset successfully.'

    user = User.query.get(user_for_password_reset.id)
    assert user.password_reset_token is None
    assert user.password_reset_expires is None
    # Verify password changed (requires checking hash or trying to login)
    from backend.services.user_service import check_password_hash # Corrected import
    assert check_password_hash(user.hashed_password, 'NewSecurePassword123!')

def test_reset_password_invalid_token(client):
    """Test password reset with an invalid token."""
    response = client.post('/api/reset-password/invalid-token-format', json={
        'new_password': 'NewSecurePassword123!'
    })
    assert response.status_code == 400 # or 404
    data = response.get_json()
    assert 'Invalid or expired password reset token' in data['error']

def test_reset_password_expired_token(client, db_session, user_for_password_reset):
    """Test password reset with an expired token."""
    token = str(uuid.uuid4())
    user_for_password_reset.password_reset_token = token
    user_for_password_reset.password_reset_expires = datetime.utcnow() - timedelta(hours=1) # Expired
    db_session.add(user_for_password_reset)
    db_session.commit()

    response = client.post(f'/api/reset-password/{token}', json={
        'new_password': 'NewSecurePassword123!'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'Invalid or expired password reset token' in data['error']

def test_reset_password_weak_new_password(client, db_session, user_for_password_reset):
    """Test password reset with a new password that fails complexity."""
    token = str(uuid.uuid4())
    user_for_password_reset.password_reset_token = token
    user_for_password_reset.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    db_session.add(user_for_password_reset)
    db_session.commit()

    response = client.post(f'/api/reset-password/{token}', json={
        'new_password': 'weak' # Fails complexity
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "Password does not meet complexity requirements" in data['error']

# --- Test Rate Limiting (Conceptual - requires specific setup for Flask-Limiter) ---
# These tests would typically require overriding the limiter storage or time functions.
# For now, they serve as a placeholder for how you might approach them.

@patch('flask_limiter.Limiter.hit')
@patch('flask_limiter.Limiter.check')
def test_login_rate_limit_exceeded(mock_limiter_check, mock_limiter_hit, client, test_user, app):
    """Test login rate limit exceeded."""
    # Configure app for testing rate limits if not already done in conftest.py
    # For example, set a very low limit for the login endpoint
    # This is highly dependent on how Flask-Limiter is configured and used.
    
    # Simulate rate limit being exceeded
    # This often involves mocking the `limiter.check()` method or the storage backend.
    # A simple way is to make the check() method always return False (or raise RateLimitExceeded)
    
    # For this example, let's assume the limiter is configured with '1 per minute' for /api/login
    # and we mock the limiter to behave as if the limit is hit.
    
    # This is a simplified mock; real testing might involve manipulating time or storage.
    original_config = app.config.get("RATELIMIT_DEFAULT")
    app.config["RATELIMIT_DEFAULT"] = "1 per second" # Temporarily set a very strict limit for testing
    
    # Make one successful call
    client.post('/api/login', json={'username': 'someuser', 'password': 'somepassword'})
    
    # The second call should hit the limit
    response = client.post('/api/login', json={'username': 'someuser', 'password': 'somepassword'})
    # The actual status code depends on Flask-Limiter's configuration (e.g., 429 Too Many Requests)
    # For now, we'll just assert it's not 200 if the limit is hit.
    # A more robust test would check for 429.
    # This test needs proper Flask-Limiter setup to work correctly.
    # assert response.status_code == 429 
    
    app.config["RATELIMIT_DEFAULT"] = original_config # Reset config
    # This is a very basic example. True rate limit testing is more involved.
    pass # Placeholder until proper rate limit testing setup

