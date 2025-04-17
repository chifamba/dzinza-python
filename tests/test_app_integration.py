# tests/test_app_integration.py
import unittest
import sys
import os
import shutil # For copying mock data
from unittest.mock import patch, MagicMock

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root) # Add project root for app import
sys.path.insert(0, src_path)

# Import the Flask app instance
try:
    from app import app # Import the app instance
    # Import models needed for creating test data if not mocking deeply
    from user import User, UserRole
    from person import Person
    from relationship import Relationship, RelationshipType
except ImportError as e:
    print(f"Error importing Flask app or components: {e}")
    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TESTING'] = True

# --- Configuration for Test Data ---
# Use separate files for integration tests to avoid conflicts
# These files will be copied/reset for each test
TEST_DATA_DIR = os.path.join(project_root, 'tests', 'test_data')
MOCK_DATA_SOURCE_DIR = os.path.join(project_root, 'data') # Where original mocks might be

TEST_USERS_FILE = os.path.join(TEST_DATA_DIR, 'users.json')
TEST_PEOPLE_FILE = os.path.join(TEST_DATA_DIR, 'people.json')
TEST_RELATIONSHIPS_FILE = os.path.join(TEST_DATA_DIR, 'relationships.json')
TEST_AUDIT_LOG = os.path.join(TEST_DATA_DIR, 'audit.log')

# Set TESTING config and paths for the app context
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
app.config['SECRET_KEY'] = 'test-secret-for-integration'
# --- Crucial: Override data paths used by the app ---
app.config['USER_DATA_PATH'] = TEST_USERS_FILE
app.config['PEOPLE_DATA_PATH'] = TEST_PEOPLE_FILE
app.config['RELATIONSHIPS_DATA_PATH'] = TEST_RELATIONSHIPS_FILE
app.config['AUDIT_LOG_FILE'] = TEST_AUDIT_LOG


class TestAppIntegration(unittest.TestCase):
    """
    Integration tests for user workflows in the Flask application.
    Uses a separate set of data files that are reset for each test.
    """

    @classmethod
    def setUpClass(cls):
        """Create the test data directory if it doesn't exist."""
        os.makedirs(TEST_DATA_DIR, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        """Remove the test data directory after all tests."""
        # Be careful with shutil.rmtree!
        # pass # Optionally leave the data for inspection
        try:
            shutil.rmtree(TEST_DATA_DIR)
        except OSError as e:
            print(f"Error removing test data directory {TEST_DATA_DIR}: {e}")


    def setUp(self):
        """Set up the test client and initialize clean data files for each test."""
        self.client = app.test_client()

        # --- Reset Data Files ---
        # Delete existing test files or copy from a clean source
        for f in [TEST_USERS_FILE, TEST_PEOPLE_FILE, TEST_RELATIONSHIPS_FILE, TEST_AUDIT_LOG]:
            if os.path.exists(f):
                os.remove(f)
        # Optionally copy baseline data if needed for tests
        # e.g., shutil.copy(os.path.join(MOCK_DATA_SOURCE_DIR, 'base_users.json'), TEST_USERS_FILE)

        # --- Re-initialize App Components (Important!) ---
        # Since data paths are changed via app.config, we need the app's
        # internal components (user_management, family_tree) to reload their data.
        # This might require modifying app.py to have a function to re-init components,
        # or carefully patching their load methods.
        # For simplicity here, we assume app components read paths from app.config on use.
        # A more robust way is patching the load_data calls within the app context.

        # Example using patching (if components are singletons loaded at startup):
        # We need to patch the *instances* used by the app routes.
        self.user_mgmt_patcher = patch('app.user_management', spec=True)
        self.family_tree_patcher = patch('app.family_tree', spec=True)
        self.audit_log_patcher = patch('app.audit_log', spec=True) # Patch audit log too

        self.mock_user_mgmt = self.user_mgmt_patcher.start()
        self.mock_family_tree = self.family_tree_patcher.start()
        self.mock_audit_log = self.audit_log_patcher.start() # Mock log_event

        # Configure mocks to interact with *real* data structures (but not files directly)
        # This makes tests more 'integration' like without hitting the disk repeatedly.
        self._test_users = {}
        self._test_people = {}
        self._test_relationships = {}

        def _mock_um_load_data(filepath, default): return list(self._test_users.values()) # Return dict values as list of dicts
        def _mock_um_save_data(filepath, data):
            self._test_users.clear()
            for user_dict in data: self._test_users[user_dict['username']] = user_dict
        def _mock_ft_load_people(filepath, default): return list(self._test_people.values())
        def _mock_ft_save_people(filepath, data):
            self._test_people.clear()
            for p_dict in data: self._test_people[p_dict['person_id']] = p_dict
        def _mock_ft_load_rels(filepath, default): return list(self._test_relationships.values())
        def _mock_ft_save_rels(filepath, data):
            self._test_relationships.clear()
            for r_dict in data: self._test_relationships[r_dict['rel_id']] = r_dict

        # Mock the underlying db_utils functions used by the components
        self.load_patch = patch('db_utils.load_data')
        self.save_patch = patch('db_utils.save_data')
        self.mock_load = self.load_patch.start()
        self.mock_save = self.save_patch.start()

        # Route load calls to appropriate mock handlers based on filepath
        def load_router(filepath, default=None):
            if 'users.json' in filepath: return _mock_um_load_data(filepath, default)
            if 'people.json' in filepath: return _mock_ft_load_people(filepath, default)
            if 'relationships.json' in filepath: return _mock_ft_load_rels(filepath, default)
            return default if default is not None else []
        self.mock_load.side_effect = load_router

        def save_router(filepath, data):
            if 'users.json' in filepath: _mock_um_save_data(filepath, data)
            if 'people.json' in filepath: _mock_ft_save_people(filepath, data)
            if 'relationships.json' in filepath: _mock_ft_save_rels(filepath, data)
        self.mock_save.side_effect = save_router

        # Re-initialize components within the app to use the mocked load/save
        # This requires components to have a reload method or similar mechanism.
        # If not, we rely on patching the instances as done above, and need
        # to make the *mocked* instances behave correctly with the in-memory data.
        # Let's make the mocked instances work with our in-memory dicts:

        # --- Configure Mock Instances ---
        # User Management
        self.mock_user_mgmt.users = self._test_users # Point mock's internal store
        self.mock_user_mgmt.validate_user.side_effect = self._um_validate_user
        self.mock_user_mgmt.get_user.side_effect = self._um_get_user
        self.mock_user_mgmt.add_user.side_effect = self._um_add_user
        self.mock_user_mgmt.delete_user.side_effect = self._um_delete_user
        self.mock_user_mgmt.get_all_users.side_effect = self._um_get_all_users

        # Family Tree
        self.mock_family_tree.people = self._test_people
        self.mock_family_tree.relationships = self._test_relationships
        self.mock_family_tree.add_person.side_effect = self._ft_add_person
        self.mock_family_tree.get_person.side_effect = self._ft_get_person
        self.mock_family_tree.add_relationship.side_effect = self._ft_add_relationship
        self.mock_family_tree.get_relationship.side_effect = self._ft_get_relationship
        self.mock_family_tree.search_person.side_effect = self._ft_search_person # Add mock search
        self.mock_family_tree.get_all_people.side_effect = lambda: [Person.from_dict(p) for p in self._test_people.values()]


    def tearDown(self):
        """Stop patchers and clear session."""
        self.user_mgmt_patcher.stop()
        self.family_tree_patcher.stop()
        self.audit_log_patcher.stop()
        self.load_patch.stop()
        self.save_patch.stop()
        # Clear session
        with self.client:
            with self.client.session_transaction() as sess:
                sess.clear()

    # --- Mock Implementation Helpers (to simulate real component logic) ---
    def _um_add_user(self, username, password, role):
        if username in self._test_users: return False
        new_user = User(username=username, role=role)
        new_user.set_password(password) # Hashes the password
        self._test_users[username] = new_user.to_dict() # Store as dict
        # Simulate saving
        self.mock_save(TEST_USERS_FILE, list(self._test_users.values()))
        return True

    def _um_get_user(self, username):
        user_dict = self._test_users.get(username)
        return User.from_dict(user_dict) if user_dict else None

    def _um_validate_user(self, username, password):
        user = self._um_get_user(username)
        if user and user.check_password(password):
            return user
        return None

    def _um_delete_user(self, username):
        if username in self._test_users:
            del self._test_users[username]
            self.mock_save(TEST_USERS_FILE, list(self._test_users.values()))
            return True
        return False

    def _um_get_all_users(self):
        return [User.from_dict(u) for u in self._test_users.values()]

    def _ft_add_person(self, person):
        if person.person_id in self._test_people: raise ValueError("Duplicate ID")
        self._test_people[person.person_id] = person.to_dict()
        self.mock_save(TEST_PEOPLE_FILE, list(self._test_people.values()))

    def _ft_get_person(self, person_id):
        p_dict = self._test_people.get(person_id)
        return Person.from_dict(p_dict) if p_dict else None

    def _ft_add_relationship(self, relationship):
         # Basic check if persons exist
        if relationship.person1_id not in self._test_people or \
           relationship.person2_id not in self._test_people:
            raise ValueError("Person not found for relationship")
        if relationship.rel_id in self._test_relationships: raise ValueError("Duplicate ID")
        self._test_relationships[relationship.rel_id] = relationship.to_dict()
        self.mock_save(TEST_RELATIONSHIPS_FILE, list(self._test_relationships.values()))

    def _ft_get_relationship(self, rel_id):
        r_dict = self._test_relationships.get(rel_id)
        return Relationship.from_dict(r_dict) if r_dict else None

    def _ft_search_person(self, query):
        results = []
        l_query = query.lower()
        for p_dict in self._test_people.values():
            if l_query in p_dict.get('name','').lower() or \
               l_query in p_dict.get('notes','').lower():
                results.append(Person.from_dict(p_dict))
        return results


    # --- Helper Methods ---
    def _login(self, username, password):
        """Logs in using the test client."""
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def _logout(self):
        """Logs out using the test client."""
        return self.client.get('/logout', follow_redirects=True)

    def _add_user_direct(self, username, password, role=UserRole.USER):
        """Adds user directly to mock data for test setup."""
        self._um_add_user(username, password, role)


    # --- Test Cases ---

    def test_login_add_person_logout_workflow(self):
        """Test login, add person, check if added, then logout."""
        # Setup: Add a user to the mock data
        self._add_user_direct("testuser", "password")

        # Step 1: Login
        login_response = self._login("testuser", "password")
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(b'Welcome testuser', login_response.data)
        self.assertIn(b'Logout', login_response.data)

        # Step 2: Go to Add Person page
        add_page_response = self.client.get('/add_person')
        self.assertEqual(add_page_response.status_code, 200)
        self.assertIn(b'Add New Person', add_page_response.data)

        # Step 3: Submit Add Person form
        person_data = {'name': 'Integration Test Person', 'birth_date': '1995-03-15', 'notes': 'Added via test'}
        add_post_response = self.client.post('/add_person', data=person_data, follow_redirects=True)
        self.assertEqual(add_post_response.status_code, 200)
        self.assertIn(b'Person added successfully!', add_post_response.data)
        # Check the underlying mock data
        self.assertEqual(len(self._test_people), 1)
        added_person_dict = list(self._test_people.values())[0]
        self.assertEqual(added_person_dict['name'], 'Integration Test Person')

        # Step 4: Verify person appears on index page (assuming index lists people)
        index_response = self.client.get('/')
        self.assertEqual(index_response.status_code, 200)
        self.assertIn(b'Integration Test Person', index_response.data) # Check if name is displayed

        # Step 5: Logout
        logout_response = self._logout()
        self.assertEqual(logout_response.status_code, 200)
        self.assertIn(b'Login', logout_response.data)
        self.assertNotIn(b'Logout', logout_response.data)

        # Step 6: Verify person is NOT visible after logout (if index requires login)
        # Or verify index page content changes for logged-out users
        # index_after_logout = self.client.get('/')
        # self.assertNotIn(b'Integration Test Person', index_after_logout.data)


    def test_add_edit_person_workflow(self):
        """Test adding a person and then editing them."""
        self._add_user_direct("editor", "editpass")
        self._login("editor", "editpass")

        # Add initial person
        person_data = {'name': 'Person To Edit', 'birth_date': '1980-01-01'}
        self.client.post('/add_person', data=person_data, follow_redirects=True)
        # Find the ID of the added person (assuming IDs are generated predictably or mockable)
        # For this test, let's assume the mock assigns 'p1'
        person_id = list(self._test_people.keys())[0] # Get the ID from mock data

        # Go to edit page
        edit_page_response = self.client.get(f'/edit_person/{person_id}')
        self.assertEqual(edit_page_response.status_code, 200)
        self.assertIn(b'Edit Person', edit_page_response.data)
        self.assertIn(b'Person To Edit', edit_page_response.data) # Check current name is in form

        # Submit edit form
        edit_data = {'name': 'Edited Name', 'birth_date': '1980-01-01', 'death_date': '2020-12-31', 'notes': 'Updated notes'}
        edit_post_response = self.client.post(f'/edit_person/{person_id}', data=edit_data, follow_redirects=True)
        self.assertEqual(edit_post_response.status_code, 200)
        self.assertIn(b'Person updated successfully!', edit_post_response.data)

        # Verify changes in mock data
        edited_person_dict = self._test_people.get(person_id)
        self.assertIsNotNone(edited_person_dict)
        self.assertEqual(edited_person_dict['name'], 'Edited Name')
        self.assertEqual(edited_person_dict['death_date'], '2020-12-31')
        self.assertEqual(edited_person_dict['notes'], 'Updated notes')

        # Verify changes on index page
        index_response = self.client.get('/')
        self.assertIn(b'Edited Name', index_response.data)
        self.assertNotIn(b'Person To Edit', index_response.data)

        self._logout()

    def test_add_relationship_workflow(self):
        """Test adding two people and then a relationship between them."""
        self._add_user_direct("relator", "relpass")
        self._login("relator", "relpass")

        # Add two people
        p1_data = {'name': 'Person One', 'birth_date': '1970-01-01'}
        self.client.post('/add_person', data=p1_data)
        p1_id = list(self._test_people.keys())[0]

        p2_data = {'name': 'Person Two', 'birth_date': '1972-02-02'}
        self.client.post('/add_person', data=p2_data)
        p2_id = list(self._test_people.keys())[1]

        # Go to add relationship page
        add_rel_page_response = self.client.get('/add_relationship')
        self.assertEqual(add_rel_page_response.status_code, 200)
        self.assertIn(b'Add New Relationship', add_rel_page_response.data)
        # Check if people appear in dropdowns (requires checking HTML content)
        self.assertIn(f'value="{p1_id}"'.encode(), add_rel_page_response.data)
        self.assertIn(f'value="{p2_id}"'.encode(), add_rel_page_response.data)

        # Submit add relationship form
        rel_data = {'person1_id': p1_id, 'person2_id': p2_id, 'type': RelationshipType.MARRIED.name}
        add_rel_post_response = self.client.post('/add_relationship', data=rel_data, follow_redirects=True)
        self.assertEqual(add_rel_post_response.status_code, 200)
        self.assertIn(b'Relationship added successfully!', add_rel_post_response.data)

        # Verify relationship in mock data
        self.assertEqual(len(self._test_relationships), 1)
        added_rel_dict = list(self._test_relationships.values())[0]
        self.assertEqual(added_rel_dict['person1_id'], p1_id)
        self.assertEqual(added_rel_dict['person2_id'], p2_id)
        self.assertEqual(added_rel_dict['type'], RelationshipType.MARRIED.name)

        # Verify relationship appears on index page (assuming relationships are shown)
        index_response = self.client.get('/')
        # This check depends heavily on how relationships are displayed
        # Example: Check if names appear together or relationship type is mentioned
        self.assertIn(b'Person One', index_response.data)
        self.assertIn(b'Person Two', index_response.data)
        self.assertIn(RelationshipType.MARRIED.name.encode(), index_response.data) # Check if type name is shown

        self._logout()

    def test_search_workflow(self):
        """Test adding people and searching for them."""
        self._add_user_direct("searcher", "searchpass")
        self._login("searcher", "searchpass")

        # Add people
        p1_data = {'name': 'John Doe', 'birth_date': '1985-06-20', 'notes': 'Lives in Texas'}
        self.client.post('/add_person', data=p1_data)
        p2_data = {'name': 'Jane Smith', 'birth_date': '1988-09-10', 'notes': 'Related to John'}
        self.client.post('/add_person', data=p2_data)
        p3_data = {'name': 'Johnny Appleseed', 'birth_date': '1774-09-26', 'notes': 'Historical figure'}
        self.client.post('/add_person', data=p3_data)

        # Perform search via GET (assuming search form is on index or dedicated page)
        search_get_response = self.client.get('/search?query=John')
        self.assertEqual(search_get_response.status_code, 200)
        self.assertIn(b'Search Results', search_get_response.data)
        self.assertIn(b'John Doe', search_get_response.data)
        self.assertIn(b'Jane Smith', search_get_response.data) # 'Related to John' in notes
        self.assertNotIn(b'Johnny Appleseed', search_get_response.data)

        # Perform search via POST (if search uses POST)
        search_post_response = self.client.post('/search', data={'query': 'texas'}, follow_redirects=True)
        self.assertEqual(search_post_response.status_code, 200)
        self.assertIn(b'Search Results', search_post_response.data)
        self.assertIn(b'John Doe', search_post_response.data) # 'Lives in Texas' in notes
        self.assertNotIn(b'Jane Smith', search_post_response.data)
        self.assertNotIn(b'Johnny Appleseed', search_post_response.data)

        # Perform search with no results
        no_results_response = self.client.get('/search?query=NoSuchName')
        self.assertEqual(no_results_response.status_code, 200)
        self.assertIn(b'No results found', no_results_response.data)
        self.assertNotIn(b'John Doe', no_results_response.data)

        self._logout()


if __name__ == '__main__':
    unittest.main()
