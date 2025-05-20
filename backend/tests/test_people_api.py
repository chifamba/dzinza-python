
import pytest
import json
import uuid
from datetime import date, datetime
from unittest.mock import patch, MagicMock

import os # For setting environment variables
# Assuming Flask app is in 'main.py' and SQLAlchemy db is in 'database.py'
# Adjust these imports if your project structure is different.
from backend.main import create_app # Import create_app factory
from backend.models import Person, User, Tree, TreeAccess, PrivacyLevelEnum, Base # Import Base for metadata
from backend.config import Config # Import default Config to modify for tests
from backend.database import get_engine # To get the engine for create_all/drop_all

TEST_USER_PASSWORD = "testpassword"

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-people-api-suite"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    DEBUG = False
    # Override DATABASE_URL used by backend.config at import time if possible,
    # or ensure create_app uses this SQLALCHEMY_DATABASE_URI.
    # The issue is backend.config.Config().DATABASE_URL is read from env.
    # So, we must set the ENV VAR if the app directly reads from Config.DATABASE_URL for engine creation.
    DATABASE_URL = "sqlite:///:memory:" # This will be used if create_app uses this config object's DATABASE_URL
    SKIP_DB_INIT = True # Prevent regular DB init logic if it conflicts

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    # Set DATABASE_URL environment variable for the test session
    # This ensures that when backend.config is loaded (implicitly by backend.main/backend.database),
    # it picks up the test database URL.
    os.environ['DATABASE_URL'] = "sqlite:///:memory:"
    os.environ['FLASK_ENV'] = "testing" # Ensures any FLASK_ENV specific logic uses testing mode

    # Create app with test configuration
    # The create_app function in main.py should ideally accept a config object.
    # Assuming create_app uses app_config_module.config by default,
    # and app_config_module.config is an instance of Config from backend.config.
    # We can't easily override that global instance *before* it's imported by backend.database.
    # Thus, setting the ENV VAR is the most reliable way for code that reads config via os.getenv.
    # If create_app can take a config_obj, that's better: test_app = create_app(TestConfig())
    
    # For now, assume create_app will pick up DATABASE_URL from env var due to os.environ set above.
    # The TestConfig class can be used if create_app is modified to accept it.
    
    # If create_app uses flask_app.config.from_object(app_config_module.config)
    # then app_config_module.config.DATABASE_URL needs to be sqlite:///:memory:
    # This is hard to patch before it's read by backend.database._create_actual_engine().
    # The most robust way for the current app structure is to ensure `backend.database._create_actual_engine()`
    # uses the Flask app's config['SQLALCHEMY_DATABASE_URI'] if available, or that
    # `backend.config.Config.DATABASE_URL` itself is patched or influenced by test settings.

    # Given the current structure, the test_client fixture in test_people_api.py
    # creates an app instance using flask_app_instance.test_client().
    # The app fixture there updates flask_app_instance.config.
    # The RuntimeError means that during import of backend.main (which creates a global app instance),
    # the DATABASE_URL is already checked.
    # The fix is:
    # 1. Comment out global `app = create_app()` in main.py (DONE in previous step)
    # 2. test_people_api.py imports create_app and the app fixture calls it.
    
    # The app fixture should create a NEW app instance for testing.
    
    # Patch the global config instance that backend.database will use.
    # This is needed because backend.database._create_actual_engine directly imports and uses backend.config.config
    with patch('backend.config.config') as mock_global_config:
        # Configure the mock_global_config to return the TestConfig values
        # This assumes backend.config.config is an instance of a class similar to Config
        mock_global_config.DATABASE_URL = "sqlite:///:memory:"
        mock_global_config.SQLALCHEMY_ECHO = False # Example of other relevant settings
        mock_global_config.SKIP_DB_INIT = True # Important for tests

        test_flask_app = create_app(app_config_obj=TestConfig()) # TestConfig is also passed for Flask app's own config

        with test_flask_app.app_context():
            engine = get_engine() # Get the engine; it should now use the patched config's DATABASE_URL
            Base.metadata.create_all(bind=engine) 
            yield test_flask_app
            Base.metadata.drop_all(bind=engine)
    
    # Clean up environment variables
    del os.environ['DATABASE_URL']
    del os.environ['FLASK_ENV']

@pytest.fixture()
def client(app): # app fixture is flask_app_instance
    """A test client for the app."""
    return app.test_client()

@pytest.fixture()
def db_session(app): # app fixture is flask_app_instance
    """
    Provides a transactional scope around a test.
    Ensures that the session used in tests is isolated and rolled back.
    """
    with app.app_context():
        connection = sqlalchemy_db.engine.connect()
        transaction = connection.begin()
        
        # Create a session specifically for this test, bound to the transaction
        test_scoped_session = sqlalchemy_db.create_scoped_session(
            options={'bind': connection, 'binds': {}}
        )
        
        # Backup original global session and override with test-specific session
        original_global_session = sqlalchemy_db.session
        sqlalchemy_db.session = test_scoped_session
        
        # flask.g.db will be patched per test via mock_g fixture

        yield test_scoped_session

        test_scoped_session.remove()
        transaction.rollback()
        connection.close()
        
        # Restore original session
        sqlalchemy_db.session = original_global_session


# --- Data Fixtures ---

@pytest.fixture
def test_user(db_session): # db_session is the transactional session for this test
    """Create a test user."""
    user_email = f"testuser_{uuid.uuid4()}@example.com"
    # Check if user already exists to prevent unique constraint errors if tests somehow share state (should not happen with proper session scoping)
    existing_user = db_session.query(User).filter_by(email=user_email).first()
    if existing_user:
        return existing_user

    user = User(
        id=uuid.uuid4(), # Explicitly set UUID if your model expects it
        email=user_email,
        first_name="Test",
        last_name="User",
        is_active=True
    )
    user.set_password(TEST_USER_PASSWORD) 
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_tree(db_session, test_user):
    """Create a test tree owned by test_user."""
    tree = Tree(
        id=uuid.uuid4(),
        name="Test Tree",
        user_id=test_user.id,
        privacy_level=PrivacyLevelEnum.private 
    )
    db_session.add(tree)
    db_session.commit()
    return tree

@pytest.fixture
def test_tree_access(db_session, test_user, test_tree):
    """Grant test_user 'edit' access to test_tree."""
    tree_access = TreeAccess(
        user_id=test_user.id,
        tree_id=test_tree.id,
        permission_level="edit" 
    )
    db_session.add(tree_access)
    db_session.commit()
    return tree_access


@pytest.fixture
def existing_person(db_session, test_user, test_tree):
    """Create a Person instance in the DB for GET/PUT/LIST tests."""
    person = Person(
        id=uuid.uuid4(),
        tree_id=test_tree.id,
        created_by=test_user.id,
        first_name="Existing",
        last_name="Person",
        birth_date=date(1990, 1, 1),
        is_living=True,
        privacy_level=PrivacyLevelEnum.public,
        profile_picture_url="http://example.com/existing.jpg",
        custom_attributes={"hobby": "testing", "skill": "pytest"},
        gender="Female" 
    )
    db_session.add(person)
    db_session.commit()
    return person

# --- Helper for flask.g patching ---

@pytest.fixture
def mock_g(db_session, test_tree): # db_session is the test session, test_tree provides the ID
    """
    Fixture to patch flask.g for decorators.
    It yields a MagicMock configured for g.db and g.active_tree_id.
    The patch target is 'flask.g' assuming decorators use 'from flask import g'.
    """
    mocked_g_object = MagicMock()
    mocked_g_object.db = db_session # Decorator uses this session
    mocked_g_object.active_tree_id = test_tree.id # Decorator uses this tree_id
    
    # If decorators are in, e.g., backend.auth.decorators and use `from flask import g`
    # patching 'flask.g' is suitable.
    # If they are in `backend.blueprints.people` and use `from flask import g`,
    # then patching `backend.blueprints.people.g` could be an alternative if `flask.g` patch doesn't work as expected.
    # However, 'flask.g' is the most fundamental proxy.
    with patch('flask.g', new=mocked_g_object) as patched_g:
        yield patched_g


# --- API Tests ---

# Test POST /api/trees/{tree_id}/people
def test_create_person_full_data(client, db_session, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)

    person_data = {
        "first_name": "ApiTest", "last_name": "User", "middle_names": "Mid",
        "maiden_name": "Maiden", "nickname": "ApiNick", "gender": "Male",
        "birth_date": "1992-05-10", "birth_date_approx": False, "birth_place": "Test City",
        "place_of_birth": "Test Hospital", "is_living": True,
        "privacy_level": "public", "notes": "API notes", "biography": "API bio",
        "profile_picture_url": "http://example.com/apitest.jpg",
        "custom_attributes": {"api_skill": "flask-testing", "role": "developer"}
    }
    
    response = client.post(f'/api/trees/{test_tree.id}/people', json=person_data)

    assert response.status_code == 201, f"Response JSON: {response.json}"
    data = response.json
    assert data['first_name'] == "ApiTest"
    assert data['profile_picture_url'] == "http://example.com/apitest.jpg"
    assert data['custom_attributes'] == {"api_skill": "flask-testing", "role": "developer"}
    assert 'id' in data

    person_id = data['id']
    created_person = db_session.get(Person, uuid.UUID(person_id))
    assert created_person is not None
    assert created_person.last_name == "User"
    assert created_person.profile_picture_url == "http://example.com/apitest.jpg"
    assert created_person.custom_attributes.get("api_skill") == "flask-testing"

def test_create_person_profile_url_none_or_empty(client, db_session, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)

    base_data = {"first_name": "ApiTest", "last_name": "NoPic", "is_living": True, "privacy_level": "public"}

    # Assuming service/model stores "" as is, or None as is.
    for url_value, expected_stored_url in [(None, None), ("", "")]: 
        person_data = {**base_data, "profile_picture_url": url_value}
        response = client.post(f'/api/trees/{test_tree.id}/people', json=person_data)
        assert response.status_code == 201, f"Response JSON: {response.json} for URL: '{url_value}'"
        data = response.json
        assert data['profile_picture_url'] == expected_stored_url
        
        created_person = db_session.get(Person, uuid.UUID(data['id']))
        assert created_person.profile_picture_url == expected_stored_url

def test_create_person_custom_attrs_none_or_empty(client, db_session, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)

    base_data = {"first_name": "ApiTest", "last_name": "NoCustom", "is_living": True, "privacy_level": "public"}
    
    # Service layer defaults None custom_attributes to {}. Empty dict {} remains {}.
    for attrs_value, expected_stored_attrs in [(None, {}), ({}, {})]: 
        person_data = {**base_data, "custom_attributes": attrs_value}
        response = client.post(f'/api/trees/{test_tree.id}/people', json=person_data)
        assert response.status_code == 201, f"Response JSON: {response.json} for Attrs: '{attrs_value}'"
        data = response.json
        assert data['custom_attributes'] == expected_stored_attrs
        
        created_person = db_session.get(Person, uuid.UUID(data['id']))
        assert created_person.custom_attributes == expected_stored_attrs

def test_create_person_missing_required_field(client, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)
    
    person_data = {"last_name": "MissingFirst", "is_living": True, "privacy_level": "public"} # first_name is missing
    response = client.post(f'/api/trees/{test_tree.id}/people', json=person_data)
    assert response.status_code == 400 # Assuming Flask-RESTx/Marshmallow validation returns 400 for schema errors
    assert 'errors' in response.json or 'error' in response.json # Check for error key
    if 'errors' in response.json: # Example for Marshmallow-like errors
         assert 'first_name' in response.json['errors']

# Test GET /api/trees/{tree_id}/people/{person_id}
def test_get_person_by_id(client, existing_person, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)

    response = client.get(f'/api/trees/{test_tree.id}/people/{existing_person.id}')
    assert response.status_code == 200, f"Response JSON: {response.json}"
    data = response.json
    assert data['id'] == str(existing_person.id)
    assert data['first_name'] == "Existing"
    assert data['profile_picture_url'] == "http://example.com/existing.jpg"
    assert data['custom_attributes'] == {"hobby": "testing", "skill": "pytest"}

def test_get_person_not_found(client, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)
    
    non_existent_uuid = uuid.uuid4()
    response = client.get(f'/api/trees/{test_tree.id}/people/{non_existent_uuid}')
    assert response.status_code == 404

# Test PUT /api/trees/{tree_id}/people/{person_id}
def test_update_person_profile_custom_attrs_and_unchanged_fields(client, db_session, existing_person, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)

    original_first_name = existing_person.first_name
    original_birth_date_iso = existing_person.birth_date.isoformat()

    update_data = {
        "profile_picture_url": "http://example.com/updated.jpg",
        "custom_attributes": {"hobby": "api-testing", "status": "updated"} # Merges with existing skill:pytest
    }
    response = client.put(f'/api/trees/{test_tree.id}/people/{existing_person.id}', json=update_data)
    assert response.status_code == 200, f"Response JSON: {response.json}"
    data = response.json
    assert data['profile_picture_url'] == "http://example.com/updated.jpg"
    
    expected_custom_attrs = {"hobby": "api-testing", "skill": "pytest", "status": "updated"}
    assert data['custom_attributes'] == expected_custom_attrs
    assert data['first_name'] == original_first_name # Check other fields unchanged
    assert data['birth_date'] == original_birth_date_iso


    updated_person_db = db_session.get(Person, existing_person.id)
    assert updated_person_db.profile_picture_url == "http://example.com/updated.jpg"
    assert updated_person_db.custom_attributes == expected_custom_attrs
    assert updated_person_db.first_name == original_first_name

def test_update_person_clear_attributes(client, db_session, existing_person, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)

    update_data = {"profile_picture_url": None, "custom_attributes": {}}
    response = client.put(f'/api/trees/{test_tree.id}/people/{existing_person.id}', json=update_data)
    assert response.status_code == 200, f"Response JSON: {response.json}"
    data = response.json
    assert data['profile_picture_url'] is None 
    assert data['custom_attributes'] == {} 

    updated_person_db = db_session.get(Person, existing_person.id)
    assert updated_person_db.profile_picture_url is None
    assert updated_person_db.custom_attributes == {}


def test_update_person_not_found(client, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)
    
    non_existent_uuid = uuid.uuid4()
    response = client.put(f'/api/trees/{test_tree.id}/people/{non_existent_uuid}', json={"first_name": "NotFound"})
    assert response.status_code == 404

def test_update_person_invalid_data(client, existing_person, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)
    
    update_data = {"birth_date": "not-a-date"} # Invalid date format
    response = client.put(f'/api/trees/{test_tree.id}/people/{existing_person.id}', json=update_data)
    assert response.status_code == 400 # Or 422 depending on validation library
    assert 'errors' in response.json or 'error' in response.json
    if 'errors' in response.json:
        assert 'birth_date' in response.json['errors']


# Test GET /api/trees/{tree_id}/people (List Endpoint)
def test_get_people_list(client, db_session, existing_person, test_user, test_tree, test_tree_access, mock_g):
    with client.session_transaction() as http_session:
        http_session['user_id'] = str(test_user.id)

    # Create another person in the same tree to test listing multiple
    person2_data_for_post = {
        "first_name": "ApiList", "last_name": "Person2", "is_living": True, "privacy_level": "public",
        "profile_picture_url": "http://example.com/list.jpg",
        "custom_attributes": {"in_list": True}
    }
    # Use the API to create the second person to ensure it's handled correctly by all layers
    post_response = client.post(f'/api/trees/{test_tree.id}/people', json=person2_data_for_post)
    assert post_response.status_code == 201
    person2_id = post_response.json['id']


    response = client.get(f'/api/trees/{test_tree.id}/people')
    assert response.status_code == 200, f"Response JSON: {response.json}"
    data = response.json
    assert isinstance(data, list)
    # The list should contain at least existing_person and person2
    # Depending on test execution order and isolation, there might be more if not cleaned,
    # but db_session fixture should provide good isolation.
    assert len(data) >= 2 

    found_existing_person = False
    found_person2 = False

    for p_data in data:
        if p_data['id'] == str(existing_person.id):
            found_existing_person = True
            assert p_data['profile_picture_url'] == existing_person.profile_picture_url
            assert p_data['custom_attributes'] == existing_person.custom_attributes
        elif p_data['id'] == person2_id:
            found_person2 = True
            assert p_data['first_name'] == "ApiList"
            assert p_data['profile_picture_url'] == "http://example.com/list.jpg"
            assert p_data['custom_attributes'] == {"in_list": True}
            
    assert found_existing_person, "Existing person not found in list"
    assert found_person2, "Second person (person2) not found in list"

# This is the problematic line 365 that pytest was complaining about.
# By adding a real Python comment or code here, we ensure that if there was
# any invisible character or strange cached state related to this line,
# it's definitively replaced.
# This is a dummy comment to ensure line 365 is clean.
# End of file.

