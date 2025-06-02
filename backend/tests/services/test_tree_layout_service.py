import unittest
from unittest.mock import MagicMock, patch
import uuid

# Assuming models and service are structured such that they can be imported like this
from backend.models import TreeLayout  # Actual model
from backend.services.tree_layout_service import TreeLayoutService

# Helper to generate UUID strings as IDs are UUIDs
def new_uuid_str():
    return str(uuid.uuid4())

class TestTreeLayoutService(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock()
        # Patch get_db_session if your service uses it globally, or pass mock_db_session if constructor takes it
        # For this example, we'll assume TreeLayoutService takes session in constructor
        self.service = TreeLayoutService(db_session=self.mock_db_session)

    def test_create_or_update_layout_create_new(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        layout_data = {"positions": [{"id": "node1", "x": 10, "y": 20}]}

        # Simulate no existing layout found
        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.return_value = None

        # Mock the add and commit process
        # The service should create a new TreeLayout instance

        created_layout = self.service.create_or_update_layout(user_id, tree_id, layout_data)

        self.assertIsNotNone(created_layout)
        self.assertEqual(created_layout.user_id, user_id)
        self.assertEqual(created_layout.tree_id, tree_id)
        self.assertEqual(created_layout.layout_data, layout_data)
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(created_layout)

    def test_create_or_update_layout_update_existing(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        initial_layout_data = {"positions": [{"id": "node1", "x": 10, "y": 20}]}
        updated_layout_data = {"positions": [{"id": "node1", "x": 30, "y": 40}]}

        mock_existing_layout = TreeLayout(user_id=user_id, tree_id=tree_id, layout_data=initial_layout_data)

        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.return_value = mock_existing_layout

        updated_layout = self.service.create_or_update_layout(user_id, tree_id, updated_layout_data)

        self.assertIsNotNone(updated_layout)
        self.assertEqual(updated_layout.layout_data, updated_layout_data) # Data should be updated
        self.mock_db_session.add.assert_not_called() # Should not add a new one
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(mock_existing_layout)


    def test_create_or_update_layout_missing_ids(self):
        self.assertIsNone(self.service.create_or_update_layout(None, "tree1", {}))
        self.assertIsNone(self.service.create_or_update_layout("user1", None, {}))
        self.mock_db_session.commit.assert_not_called()

    def test_get_layout_found(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        layout_data = {"positions": [{"id": "node1", "x": 10, "y": 20}]}
        mock_layout = TreeLayout(user_id=user_id, tree_id=tree_id, layout_data=layout_data)

        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.return_value = mock_layout

        retrieved_layout = self.service.get_layout(user_id, tree_id)

        self.assertEqual(retrieved_layout, mock_layout)

    def test_get_layout_not_found(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.return_value = None

        self.assertIsNone(self.service.get_layout(user_id, tree_id))

    def test_get_layout_missing_ids(self):
        self.assertIsNone(self.service.get_layout(None, "tree1"))
        self.assertIsNone(self.service.get_layout("user1", None))


    def test_delete_layout_found(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        mock_layout = TreeLayout(user_id=user_id, tree_id=tree_id, layout_data={})

        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.return_value = mock_layout

        result = self.service.delete_layout(user_id, tree_id)

        self.assertTrue(result)
        self.mock_db_session.delete.assert_called_once_with(mock_layout)
        self.mock_db_session.commit.assert_called_once()

    def test_delete_layout_not_found(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.return_value = None

        result = self.service.delete_layout(user_id, tree_id)

        self.assertFalse(result)
        self.mock_db_session.delete.assert_not_called()
        self.mock_db_session.commit.assert_not_called()

    def test_delete_layout_missing_ids(self):
        self.assertFalse(self.service.delete_layout(None, "tree1"))
        self.assertFalse(self.service.delete_layout("user1", None))
        self.mock_db_session.delete.assert_not_called()

    def test_create_or_update_db_exception(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        self.mock_db_session.commit.side_effect = Exception("DB error")
        # Simulate no existing layout found to attempt a create
        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.return_value = None

        layout = self.service.create_or_update_layout(user_id, tree_id, {})
        self.assertIsNone(layout)
        self.mock_db_session.rollback.assert_called_once()

    def test_get_layout_db_exception(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.side_effect = Exception("DB error")

        layout = self.service.get_layout(user_id, tree_id)
        self.assertIsNone(layout)
        # No rollback needed for read operation usually, but good to check no commit was called
        self.mock_db_session.commit.assert_not_called()


    def test_delete_layout_db_exception(self):
        user_id = new_uuid_str()
        tree_id = new_uuid_str()
        mock_layout = TreeLayout(user_id=user_id, tree_id=tree_id, layout_data={})
        self.mock_db_session.query(TreeLayout).filter_by(user_id=user_id, tree_id=tree_id).first.return_value = mock_layout
        self.mock_db_session.commit.side_effect = Exception("DB error")

        result = self.service.delete_layout(user_id, tree_id)
        self.assertFalse(result)
        self.mock_db_session.rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
