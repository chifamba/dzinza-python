# tests/test_family_tree.py
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, call # Import call

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Import necessary classes and functions
from src.person import Person
from src.relationship import Relationship, RelationshipType
from src.family_tree import FamilyTree
# Assuming db_utils is used for load/save
# from db_utils import load_data, save_data

# Mock data paths (adjust if necessary)
MOCK_PEOPLE_FILE = 'mock_data/people.json'
MOCK_RELATIONSHIPS_FILE = 'mock_data/relationships.json'

class TestFamilyTree(unittest.TestCase):
    """Test cases for the FamilyTree class."""

    def setUp(self):
        """Set up a fresh FamilyTree instance and mock data for each test."""
        # Mock load_data to return empty lists initially for a clean state
        self.load_patcher = patch('family_tree.load_data')
        self.mock_load_data = self.load_patcher.start()
        self.mock_load_data.side_effect = lambda filepath, default: default if default is not None else []

        # Mock save_data
        self.save_patcher = patch('family_tree.save_data')
        self.mock_save_data = self.save_patcher.start()

        # Create a new FamilyTree instance for each test
        self.tree = FamilyTree(people_file=MOCK_PEOPLE_FILE, relationships_file=MOCK_RELATIONSHIPS_FILE)

        # Add some initial data for tests that need it
        self.person1 = Person(person_id="p1", name="Alice", birth_date="1990-01-01")
        self.person2 = Person(person_id="p2", name="Bob", birth_date="1992-05-10")
        self.person3 = Person(person_id="p3", name="Charlie", birth_date="1988-11-20")
        self.relationship1 = Relationship(rel_id="r1", person1_id="p1", person2_id="p2", type=RelationshipType.MARRIED)


    def tearDown(self):
        """Stop the patchers after each test."""
        self.load_patcher.stop()
        self.save_patcher.stop()

    def test_initialization_loads_data(self):
        """Test that data is loaded during initialization."""
        # Reset mocks specifically for this test to check initial load calls
        self.mock_load_data.reset_mock()
        self.mock_load_data.side_effect = lambda filepath, default: default if default is not None else []

        # Re-initialize to trigger load
        FamilyTree(people_file=MOCK_PEOPLE_FILE, relationships_file=MOCK_RELATIONSHIPS_FILE)

        # Check that load_data was called for both files
        expected_calls = [
            call(MOCK_PEOPLE_FILE, default=[]),
            call(MOCK_RELATIONSHIPS_FILE, default=[])
        ]
        self.mock_load_data.assert_has_calls(expected_calls, any_order=True)

    def test_add_person(self):
        """Test adding a new person."""
        self.tree.add_person(self.person1)
        self.assertEqual(len(self.tree.people), 1)
        self.assertEqual(self.tree.people["p1"], self.person1)
        # Check if save_data was called
        self.mock_save_data.assert_called() # Called at least once (could be specific later)

    def test_add_person_duplicate_id(self):
        """Test adding a person with an existing ID."""
        self.tree.add_person(self.person1)
        with self.assertRaises(ValueError): # Or check for specific behavior like logging/ignoring
            self.tree.add_person(self.person1)
        self.assertEqual(len(self.tree.people), 1) # Should not add the duplicate

    def test_get_person(self):
        """Test retrieving a person by ID."""
        self.tree.add_person(self.person1)
        retrieved_person = self.tree.get_person("p1")
        self.assertEqual(retrieved_person, self.person1)

    def test_get_person_not_found(self):
        """Test retrieving a non-existent person."""
        retrieved_person = self.tree.get_person("nonexistent")
        self.assertIsNone(retrieved_person)

    def test_remove_person_simple(self):
        """Test removing a person who has no relationships."""
        self.tree.add_person(self.person1)
        self.tree.remove_person("p1")
        self.assertNotIn("p1", self.tree.people)
        self.assertIsNone(self.tree.get_person("p1"))
        # Check save was called after removal
        self.mock_save_data.assert_called()

    def test_remove_person_with_relationships(self):
        """Test removing a person involved in relationships."""
        self.tree.add_person(self.person1)
        self.tree.add_person(self.person2)
        self.tree.add_relationship(self.relationship1) # p1 married to p2

        self.assertEqual(len(self.tree.relationships), 1)

        # Remove person1
        self.tree.remove_person("p1")

        # Person should be gone
        self.assertNotIn("p1", self.tree.people)
        # Relationship involving the person should also be gone
        self.assertEqual(len(self.tree.relationships), 0)
        self.assertIsNone(self.tree.get_relationship("r1"))
        # Other person should still exist
        self.assertIn("p2", self.tree.people)
        # Check saves were called (person removal, relationship removal)
        self.assertTrue(self.mock_save_data.call_count >= 2)


    def test_remove_person_not_found(self):
        """Test removing a non-existent person."""
        # Should not raise an error, perhaps log or just do nothing
        try:
            self.tree.remove_person("nonexistent")
        except Exception as e:
            self.fail(f"remove_person raised an exception unexpectedly: {e}")
        # Ensure save wasn't called if nothing changed
        # self.mock_save_data.assert_not_called() # Depends on implementation detail

    def test_add_relationship(self):
        """Test adding a new relationship."""
        self.tree.add_person(self.person1)
        self.tree.add_person(self.person2)
        self.tree.add_relationship(self.relationship1)
        self.assertEqual(len(self.tree.relationships), 1)
        self.assertEqual(self.tree.relationships["r1"], self.relationship1)
        self.mock_save_data.assert_called()

    def test_add_relationship_duplicate_id(self):
        """Test adding a relationship with an existing ID."""
        self.tree.add_person(self.person1)
        self.tree.add_person(self.person2)
        self.tree.add_relationship(self.relationship1)
        with self.assertRaises(ValueError): # Or check behavior
            self.tree.add_relationship(self.relationship1)
        self.assertEqual(len(self.tree.relationships), 1)

    def test_add_relationship_person_not_found(self):
        """Test adding a relationship where one person doesn't exist."""
        self.tree.add_person(self.person1) # Only person1 exists
        rel_invalid = Relationship(rel_id="r_invalid", person1_id="p1", person2_id="nonexistent", type=RelationshipType.PARENT_OF)
        with self.assertRaises(ValueError): # Should fail if persons don't exist
            self.tree.add_relationship(rel_invalid)
        self.assertEqual(len(self.tree.relationships), 0)

    def test_get_relationship(self):
        """Test retrieving a relationship by ID."""
        self.tree.add_person(self.person1)
        self.tree.add_person(self.person2)
        self.tree.add_relationship(self.relationship1)
        retrieved_rel = self.tree.get_relationship("r1")
        self.assertEqual(retrieved_rel, self.relationship1)

    def test_get_relationship_not_found(self):
        """Test retrieving a non-existent relationship."""
        retrieved_rel = self.tree.get_relationship("nonexistent")
        self.assertIsNone(retrieved_rel)

    def test_remove_relationship(self):
        """Test removing a relationship by ID."""
        self.tree.add_person(self.person1)
        self.tree.add_person(self.person2)
        self.tree.add_relationship(self.relationship1)
        self.tree.remove_relationship("r1")
        self.assertNotIn("r1", self.tree.relationships)
        self.assertIsNone(self.tree.get_relationship("r1"))
        self.mock_save_data.assert_called()

    def test_remove_relationship_not_found(self):
        """Test removing a non-existent relationship."""
        try:
            self.tree.remove_relationship("nonexistent")
        except Exception as e:
            self.fail(f"remove_relationship raised an exception unexpectedly: {e}")
        # self.mock_save_data.assert_not_called() # Depends

    def test_find_relationships_for_person(self):
        """Test finding all relationships involving a specific person."""
        self.tree.add_person(self.person1)
        self.tree.add_person(self.person2)
        self.tree.add_person(self.person3)
        rel1 = Relationship(rel_id="r1", person1_id="p1", person2_id="p2", type=RelationshipType.MARRIED)
        rel2 = Relationship(rel_id="r2", person1_id="p3", person2_id="p1", type=RelationshipType.PARENT_OF) # p3 is parent of p1
        rel3 = Relationship(rel_id="r3", person1_id="p2", person2_id="p3", type=RelationshipType.SIBLING_OF) # p2 and p3 siblings

        self.tree.add_relationship(rel1)
        self.tree.add_relationship(rel2)
        self.tree.add_relationship(rel3)

        p1_rels = self.tree.find_relationships_for_person("p1")
        self.assertEqual(len(p1_rels), 2)
        self.assertIn(rel1, p1_rels)
        self.assertIn(rel2, p1_rels)

        p2_rels = self.tree.find_relationships_for_person("p2")
        self.assertEqual(len(p2_rels), 2)
        self.assertIn(rel1, p2_rels)
        self.assertIn(rel3, p2_rels)

        p3_rels = self.tree.find_relationships_for_person("p3")
        self.assertEqual(len(p3_rels), 2)
        self.assertIn(rel2, p3_rels)
        self.assertIn(rel3, p3_rels)

    def test_find_relationships_for_person_not_found(self):
        """Test finding relationships for a non-existent person."""
        rels = self.tree.find_relationships_for_person("nonexistent")
        self.assertEqual(len(rels), 0)

    def test_save_on_change(self):
        """Verify save is called after modifications."""
        # Add person
        self.mock_save_data.reset_mock()
        self.tree.add_person(self.person1)
        self.mock_save_data.assert_called_with(MOCK_PEOPLE_FILE, [p.to_dict() for p in self.tree.people.values()])

        # Add relationship
        self.mock_save_data.reset_mock()
        self.tree.add_person(self.person2) # Need p2 for relationship
        self.mock_save_data.reset_mock() # Reset after adding p2
        self.tree.add_relationship(self.relationship1)
        self.mock_save_data.assert_called_with(MOCK_RELATIONSHIPS_FILE, [r.to_dict() for r in self.tree.relationships.values()])

        # Remove relationship
        self.mock_save_data.reset_mock()
        self.tree.remove_relationship("r1")
        self.mock_save_data.assert_called_with(MOCK_RELATIONSHIPS_FILE, []) # Now empty

        # Remove person (should trigger save for people and relationships)
        self.mock_save_data.reset_mock()
        self.tree.remove_person("p1")
        expected_people_save = call(MOCK_PEOPLE_FILE, [self.person2.to_dict()]) # Only p2 left
        # Relationships already empty, might save empty list again or not call if no change
        # Check that people save was called correctly
        # Using assert_has_calls because order might not be guaranteed if both save
        self.mock_save_data.assert_has_calls([expected_people_save], any_order=True)


if __name__ == '__main__':
    unittest.main()
