import unittest
import uuid
import json
from unittest.mock import patch, MagicMock, ANY

from flask import Flask, g, session
from werkzeug.exceptions import BadRequest, NotFound, Forbidden

# Adjust imports based on your project structure
from blueprints.relationships import relationships_bp

class TestRelationshipsAPI(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'super_secret_key_for_testing_session_relationships'
        self.app.register_blueprint(relationships_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.test_user_id = str(uuid.uuid4())
        self.test_tree_id = str(uuid.uuid4())
        self.test_relationship_id = str(uuid.uuid4())
        self.test_person1_id = str(uuid.uuid4())
        self.test_person2_id = str(uuid.uuid4())

        # Patch service functions
        self.patcher_create_relationship_db = patch('blueprints.relationships.create_relationship_db')
        self.patcher_update_relationship_db = patch('blueprints.relationships.update_relationship_db')
        self.patcher_get_relationship_db = patch('blueprints.relationships.get_relationship_db')
        self.patcher_get_all_relationships_db = patch('blueprints.relationships.get_all_relationships_db')
        self.patcher_delete_relationship_db = patch('blueprints.relationships.delete_relationship_db')

        self.mock_create_relationship_db = self.patcher_create_relationship_db.start()
        self.mock_update_relationship_db = self.patcher_update_relationship_db.start()
        self.mock_get_relationship_db = self.patcher_get_relationship_db.start()
        self.mock_get_all_relationships_db = self.patcher_get_all_relationships_db.start()
        self.mock_delete_relationship_db = self.patcher_delete_relationship_db.start()

        # Patch decorators
        self.patcher_require_auth = patch('blueprints.relationships.require_auth') # Assuming it's in decorators
        self.patcher_require_tree_access = patch('blueprints.relationships.require_tree_access')
        
        self.mock_require_auth_decorator = self.patcher_require_auth.start()
        self.mock_require_tree_access_decorator = self.patcher_require_tree_access.start()

        self.mock_require_auth_decorator.side_effect = lambda func: func
        self.mock_require_tree_access_decorator.side_effect = lambda level: (lambda func: func)


    def tearDown(self):
        self.patcher_create_relationship_db.stop()
        self.patcher_update_relationship_db.stop()
        self.patcher_get_relationship_db.stop()
        self.patcher_get_all_relationships_db.stop()
        self.patcher_delete_relationship_db.stop()
        self.patcher_require_auth.stop()
        self.patcher_require_tree_access.stop()

    def test_create_relationship_with_location_and_notes(self):
        relationship_payload = {
            "person1_id": self.test_person1_id,
            "person2_id": self.test_person2_id,
            "relationship_type": "spouse_current",
            "location": "City Hall",
            "notes": "A very happy day."
        }
        mock_response_data = {"id": self.test_relationship_id, **relationship_payload}
        self.mock_create_relationship_db.return_value = mock_response_data

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id # Ensure g.active_tree_id is a string for blueprint
                
                response = client.post('/api/relationships', json=relationship_payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, mock_response_data)
        self.mock_create_relationship_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_user_id), uuid.UUID(self.test_tree_id), relationship_payload
        )

    def test_update_relationship_with_location_and_notes(self):
        update_payload = {
            "location": "Reception Hall",
            "notes": "Party details.",
            "relationship_type": "partner" # Can update other fields too
        }
        mock_response_data = {"id": self.test_relationship_id, **update_payload}
        self.mock_update_relationship_db.return_value = mock_response_data

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.put(f'/api/relationships/{self.test_relationship_id}', json=update_payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, mock_response_data)
        self.mock_update_relationship_db.assert_called_once_with(
            g.db, uuid.UUID(self.test_relationship_id), uuid.UUID(self.test_tree_id), update_payload
        )
    
    def test_create_relationship_missing_required_fields(self):
        # Missing person2_id and relationship_type
        relationship_payload = {"person1_id": self.test_person1_id, "location": "Someplace"}
        # Service layer is expected to abort(400)
        self.mock_create_relationship_db.side_effect = BadRequest(description={"message": "Validation failed", "details": {"person2_id": "Required."}})

        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.test_user_id
                sess['active_tree_id'] = self.test_tree_id
            with self.app.app_context():
                g.db = MagicMock()
                g.active_tree_id = self.test_tree_id
                response = client.post('/api/relationships', json=relationship_payload)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("person2_id", response.json['message']['details'])


if __name__ == '__main__':
    unittest.main()
