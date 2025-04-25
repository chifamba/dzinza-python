# backend/tests/test_app_integration.py
import unittest
import os
import shutil
import uuid # Import uuid
import base64 # Import base64
from unittest.mock import patch, MagicMock

# Corrected Imports: Use absolute path from 'backend'
try:
    from  app import app # Assuming app instance is here
    from  src.user import User, UserRole # Import UserRole
    from  src.person import Person
    from  src.relationship import Relationship, RelationshipType
    # Import components being patched using absolute paths
    import  src.user_management
    import  src.family_tree
    import  src.audit_log
    import  src.db_utils
    # Import hashing function if used directly in mocks
    from  src.encryption import hash_password
except ImportError as e:
    print(f"Error importing test dependencies for test_app_integration: {e}")
    from flask import Flask
    app = Flask(__name__)
    # Define dummy classes/mocks if needed
    class User:
        def __init__(self, user_id, username, password_hash, role): pass
        def set_password(self, pwd): pass
        def to_dict(self): return {}
    class UserRole: USER = 'basic'; ADMIN = 'admin'
    class Person:
         def __init__(self, person_id, creator_user_id, **kwargs): pass
         def to_dict(self): return {}
    class Relationship:
         def __init__(self, person1_id, person2_id, rel_type, **kwargs): pass
         def to_dict(self): return {}
    class RelationshipType: MARRIED = 'married'; PARENT_OF = 'parent'; SIBLING_OF = 'sibling'
    def hash_password(pwd): return b'dummy_hash'


# --- Setup ---
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
TEST_USERS_FILE = os.path.join(TEST_DATA_DIR, 'users.json')
TEST_PEOPLE_FILE = os.path.join(TEST_DATA_DIR, 'people.json')
TEST_RELATIONSHIPS_FILE = os.path.join(TEST_DATA_DIR, 'relationships.json')
TEST_AUDIT_LOG = os.path.join(TEST_DATA_DIR, 'audit.log')

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
app.config['SECRET_KEY'] = 'test-secret-for-integration'
app.config['USER_DATA_PATH'] = TEST_USERS_FILE
app.config['PEOPLE_DATA_PATH'] = TEST_PEOPLE_FILE
app.config['RELATIONSHIPS_DATA_PATH'] = TEST_RELATIONSHIPS_FILE
app.config['AUDIT_LOG_FILE'] = TEST_AUDIT_LOG

class TestAppIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.makedirs(TEST_DATA_DIR, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        # shutil.rmtree(TEST_DATA_DIR)
        pass

    def setUp(self):
        self.client = app.test_client()

        # Clear files if using file-based mocks
        for f in [TEST_USERS_FILE, TEST_PEOPLE_FILE, TEST_RELATIONSHIPS_FILE, TEST_AUDIT_LOG]:
            if os.path.exists(f):
                os.remove(f)

        # Patch Components using absolute paths
        # Patch the actual classes used by the app routes
        self.user_mgmt_patcher = patch(' app.user_manager', spec= src.user_management.UserManagement) # Patch instance in app.py
        self.family_tree_patcher = patch(' app.family_tree', spec= src.family_tree.FamilyTree) # Patch instance in app.py
        self.audit_log_patcher = patch(' src.audit_log.log_audit', spec=True) # Patch function directly
        # Patch db_utils if they are imported directly into app routes (less likely)
        # self.load_patch = patch(' app.load_data') # Example if imported into app.py
        # self.save_patch = patch(' app.save_data') # Example

        self.mock_user_mgmt = self.user_mgmt_patcher.start()
        self.mock_family_tree = self.family_tree_patcher.start()
        self.mock_audit_log = self.audit_log_patcher.start()
        # self.mock_load = self.load_patch.start() # Start if patched
        # self.mock_save = self.save_patch.start() # Start if patched

        # Configure Mocks to simulate behavior
        self._test_users = {}
        self._test_people = {}
        self._test_relationships = {}

        # Simulate methods on the mocked instances
        self.mock_user_mgmt.login_user.side_effect = self._um_login_user
        self.mock_user_mgmt.find_user_by_username.side_effect = self._um_find_user_by_username
        self.mock_user_mgmt.register_user.side_effect = self._um_register_user
        self.mock_user_mgmt.delete_user.side_effect = self._um_delete_user
        self.mock_user_mgmt.get_all_users.side_effect = lambda: list(self._test_users.values()) # Return list of User objects

        self.mock_family_tree.add_person.side_effect = self._ft_add_person
        self.mock_family_tree.find_person.side_effect = self._ft_find_person
        self.mock_family_tree.add_relationship.side_effect = self._ft_add_relationship
        self.mock_family_tree.get_relationship.side_effect = self._ft_get_relationship
        self.mock_family_tree.edit_person.side_effect = self._ft_edit_person
        # Add mocks for other methods used by routes

    # --- Mock Implementation Helpers (Simulate component logic) ---
    def _um_register_user(self, username, password, role="basic"):
        if username in self._test_users: return None # Simulate failure
        user_id = str(uuid.uuid4())
        # Use actual hash_password if available
        hashed_pw_b64 = base64.b64encode(hash_password(password)).decode('utf-8')
        new_user = User(user_id=user_id, username=username, password_hash_b64=hashed_pw_b64, role=role)
        self._test_users[username] = new_user # Store User object if needed by other mocks
        # Simulate saving if necessary for the test logic being verified
        # self.mock_save(...)
        return new_user # Return the created User object

    def _um_find_user_by_username(self, username):
        return self._test_users.get(username)

    def _um_login_user(self, username, password):
        user = self._um_find_user_by_username(username)
        if user:
             # Need verify_password or User.check_password method
             # Assuming User has check_password that handles b64 decoding
             if hasattr(user, 'check_password') and user.check_password(password):
                 return user
             # Or manually verify if User doesn't have check_password
             # elif user.password_hash_b64 and verify_password(password, base64.b64decode(user.password_hash_b64)):
             #    return user
        return None

    def _um_delete_user(self, user_id, actor_username): # Adapt signature if needed
        # Find user by ID or username depending on how UserManagement works
        user_to_del = next((u for u in self._test_users.values() if u.user_id == user_id), None)
        if user_to_del:
            del self._test_users[user_to_del.username]
            # self.mock_save(...)
            return True
        return False

    def _ft_add_person(self, **person_data): # Assuming it takes kwargs
        person_id = str(uuid.uuid4())
        new_person = Person(person_id=person_id, **person_data)
        self._test_people[person_id] = new_person
        # self.mock_save(...)
        return new_person # Return the object

    def _ft_find_person(self, person_id=None, name=None):
        if person_id:
            return self._test_people.get(person_id)
        # Add name search logic if needed by tests
        return None

    def _ft_edit_person(self, person_id, updates, edited_by):
        person = self._test_people.get(person_id)
        if not person: return False
        for key, value in updates.items():
            if hasattr(person, key):
                setattr(person, key, value)
        # self.mock_save(...)
        return True

    def _ft_add_relationship(self, **rel_data):
        # Check if persons exist
        p1 = self._test_people.get(rel_data['person1_id'])
        p2 = self._test_people.get(rel_data['person2_id'])
        if not p1 or not p2: return None # Simulate failure
        rel_id = str(uuid.uuid4())
        new_rel = Relationship(rel_id=rel_id, **rel_data)
        self._test_relationships[rel_id] = new_rel
        # self.mock_save(...)
        return new_rel

    def _ft_get_relationship(self, rel_id):
         return self._test_relationships.get(rel_id)

    # --- Helper Methods ---
    def _login(self, username, password):
        return self.client.post('/api/login', json=dict( # Use JSON for API
            username=username,
            password=password
        ), follow_redirects=True)

    def _logout(self):
        return self.client.post('/api/logout', follow_redirects=True) # POST for logout

    def _add_user_direct(self, username, password, role=UserRole.USER): # Use imported UserRole
        """Adds user directly to mock data for test setup."""
        # Use the mock registration method which handles hashing etc.
        self._um_register_user(username, password, role)

    # --- Test Cases ---
    # Adapt test cases to use JSON requests and check JSON responses
    def test_login_add_person_logout_workflow(self):
        """Test login, add person, check if added, then logout."""
        self._add_user_direct("testuser", "password")

        # Login
        login_response = self._login("testuser", "password")
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json['message'], "Login successful!")
        self.assertEqual(login_response.json['user']['username'], "testuser")

        # Add Person (assuming /api/people endpoint)
        person_data = {'first_name': 'Integration', 'last_name':'Test', 'birth_date': '1995-03-15', 'notes': 'Added via test'}
        add_post_response = self.client.post('/api/people', json=person_data, follow_redirects=True)
        self.assertEqual(add_post_response.status_code, 201) # Expect 201 Created
        added_person_id = add_post_response.json['id']
        self.assertIsNotNone(added_person_id)

        # Verify person in mock data (or by GET request)
        self.assertIn(added_person_id, self._test_people)
        self.assertEqual(self._test_people[added_person_id].first_name, 'Integration')

        # Logout
        logout_response = self._logout()
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(logout_response.json['message'], "Logout successful")

    # ... (Adapt other integration tests similarly for API interaction) ...

    def tearDown(self):
        self.user_mgmt_patcher.stop()
        self.family_tree_patcher.stop()
        self.audit_log_patcher.stop()
        # self.load_patch.stop() # Stop if patched
        # self.save_patch.stop() # Stop if patched
        # Clear session if using Flask sessions
        with self.client:
            with self.client.session_transaction() as sess:
                sess.clear()

if __name__ == '__main__':
    unittest.main()
