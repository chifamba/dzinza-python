# tests/test_family_tree.py
import unittest
import os
import json
from unittest.mock import MagicMock, patch, mock_open

# Import refactored classes
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship
from src.audit_log import AuditLog # Import placeholder

# Mock GEDCOM availability if needed for tests
# from src import family_tree
# family_tree.GEDCOM_AVAILABLE = False # Or True

class TestFamilyTree(unittest.TestCase):
    """Test suite for the refactored FamilyTree class."""

    def setUp(self):
        """Set up a FamilyTree instance and sample persons for tests."""
        self.mock_audit_log = MagicMock(spec=AuditLog)
        # self.mock_encryptor = MagicMock(spec=DataEncryptor) # If testing encryption parts
        # self.encryption_key = "test_key"
        self.family_tree = FamilyTree(
            audit_log=self.mock_audit_log,
            # data_encryptor=self.mock_encryptor, # Pass mocks if needed
            # encryption_key=self.encryption_key
        )

        # Create sample persons
        self.user_id = "test_user"
        self.p1 = Person(self.user_id, "Alice", "Alpha", person_id="p1", date_of_birth="1950-01-01")
        self.p2 = Person(self.user_id, "Bob", "Beta", person_id="p2", date_of_birth="1952-02-02")
        self.p3 = Person(self.user_id, "Charlie", "Alpha", person_id="p3", date_of_birth="1975-03-03") # Child
        self.p4 = Person(self.user_id, "Diana", "Delta", person_id="p4", date_of_birth="1978-04-04") # Another Child

        # Add persons needed for most tests
        self.family_tree.add_person(self.p1)
        self.family_tree.add_person(self.p2)
        self.family_tree.add_person(self.p3)


    def test_add_person(self):
        """Test adding a person."""
        self.assertIn(self.p1.person_id, self.family_tree.person_nodes)
        self.assertEqual(self.family_tree.person_nodes[self.p1.person_id], self.p1)
        self.assertEqual(self.p1.family_tree, self.family_tree) # Check tree reference
        self.mock_audit_log.log_event.assert_called_with(
            "system", "person_added", f"Added person: {self.p1.person_id} ({self.p1.get_full_name()})"
        )

    def test_add_person_duplicate(self):
        """Test adding a person with an existing ID raises ValueError."""
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.family_tree.add_person(self.p1) # p1 already added in setUp

    def test_get_person_by_id(self):
        """Test retrieving a person by ID."""
        retrieved_person = self.family_tree.get_person_by_id(self.p1.person_id)
        self.assertEqual(retrieved_person, self.p1)
        self.assertIsNone(self.family_tree.get_person_by_id("nonexistent_id"))

    def test_link_persons(self):
        """Test linking two persons with a relationship."""
        rel_spouse = Relationship(self.p1.person_id, self.p2.person_id, "spouse")
        self.family_tree.link_persons(rel_spouse)

        # Check relationship is added to both persons
        self.assertIn(rel_spouse, self.p1.relationships)
        self.assertIn(rel_spouse, self.p2.relationships)
        self.mock_audit_log.log_event.assert_called_with(
            "system", "relationship_added", f"Added relationship: {rel_spouse}"
        )

    def test_link_persons_not_found(self):
        """Test linking raises ValueError if a person is not in the tree."""
        p_not_added = Person(self.user_id, "Eve", "Epsilon", person_id="p_not_added")
        rel_invalid = Relationship(self.p1.person_id, p_not_added.person_id, "friend")
        with self.assertRaisesRegex(ValueError, f"Person 2 with ID {p_not_added.person_id} not found"):
            self.family_tree.link_persons(rel_invalid)

    def test_unlink_persons(self):
        """Test removing a relationship between two persons."""
        rel_spouse = Relationship(self.p1.person_id, self.p2.person_id, "spouse")
        self.family_tree.link_persons(rel_spouse) # Add first
        self.assertIn(rel_spouse, self.p1.relationships) # Verify added

        self.family_tree.unlink_persons(rel_spouse) # Remove
        self.assertNotIn(rel_spouse, self.p1.relationships)
        self.assertNotIn(rel_spouse, self.p2.relationships)
        self.mock_audit_log.log_event.assert_called_with(
            "system", "relationship_removed", f"Removed relationship: {rel_spouse}"
        )

    def test_unlink_persons_not_found(self):
        """Test unlinking raises ValueError if relationship doesn't exist."""
        rel_nonexistent = Relationship(self.p1.person_id, self.p2.person_id, "friend")
        with self.assertRaisesRegex(ValueError, "Could not remove relationship"):
            self.family_tree.unlink_persons(rel_nonexistent)

    def test_delete_person(self):
        """Test deleting a person and cleaning up their relationships."""
        # Setup: p1 married to p2, parent of p3
        rel_spouse = Relationship(self.p1.person_id, self.p2.person_id, "spouse")
        rel_parent = Relationship(self.p1.person_id, self.p3.person_id, "parent")
        rel_child = Relationship(self.p3.person_id, self.p1.person_id, "child")
        self.family_tree.link_persons(rel_spouse)
        self.family_tree.link_persons(rel_parent)
        self.family_tree.link_persons(rel_child)

        self.assertIn(rel_spouse, self.p2.relationships) # p2 has spouse relationship
        self.assertIn(rel_child, self.p3.relationships) # p3 has child relationship

        # Delete p1
        self.family_tree.delete_person(self.p1.person_id)

        # Verify p1 is removed
        self.assertNotIn(self.p1.person_id, self.family_tree.person_nodes)

        # Verify relationships involving p1 are removed from others
        self.assertNotIn(rel_spouse, self.p2.relationships)
        self.assertNotIn(rel_child, self.p3.relationships)

        # Verify audit log calls
        self.mock_audit_log.log_event.assert_any_call(
            "system", "relationship_removed", f"Removed relationship involving deleted person {self.p1.person_id}: {rel_spouse}"
        )
        self.mock_audit_log.log_event.assert_any_call(
            "system", "relationship_removed", f"Removed relationship involving deleted person {self.p1.person_id}: {rel_parent}" # Parent rel on p1 removed
        )
        # The child relationship on p3 pointing to p1 should also be removed
        # We need to check the call based on the relationship object hash/equality
        # This check might be tricky with mocks, ensure delete_person removes from other_person.relationships
        # A simplified check:
        self.assertFalse(any(r.involves_person(self.p1.person_id) for r in self.p3.relationships))


        self.mock_audit_log.log_event.assert_called_with(
            "system", "person_deleted", f"Deleted person: {self.p1.person_id} ({self.p1.get_full_name()})"
        )


    def test_delete_person_not_found(self):
        """Test deleting a non-existent person raises ValueError."""
        with self.assertRaisesRegex(ValueError, "not found"):
            self.family_tree.delete_person("nonexistent_id")

    def test_validate_person_data(self):
        """Test the person data validation method."""
        valid_person = Person("user", "Valid", "Person", date_of_birth="2000-01-01")
        self.assertEqual(self.family_tree.validate_person_data(valid_person), [])

        invalid_person_dates = Person("user", "Invalid", "Dates", date_of_birth="2000-01-01", date_of_death="1999-12-31")
        errors = self.family_tree.validate_person_data(invalid_person_dates)
        self.assertIn("Date of death (1999-12-31 00:00:00) cannot be before date of birth (2000-01-01 00:00:00).", errors)

        # Add more validation tests (e.g., invalid URLs if implemented)

    def test_check_relationship_consistency(self):
        """Test relationship consistency checks."""
        # Setup consistent relationships: p1 parent of p3
        rel_parent = Relationship(self.p1.person_id, self.p3.person_id, "parent")
        rel_child = Relationship(self.p3.person_id, self.p1.person_id, "child")
        self.family_tree.link_persons(rel_parent)
        self.family_tree.link_persons(rel_child)
        self.assertEqual(self.family_tree.check_relationship_consistency(self.p1.person_id), [])
        self.assertEqual(self.family_tree.check_relationship_consistency(self.p3.person_id), [])

        # Introduce inconsistency: Remove child rel from p1
        self.p1.remove_relationship(rel_parent) # p1 no longer knows it's parent of p3
        errors_p1 = self.family_tree.check_relationship_consistency(self.p1.person_id)
        errors_p3 = self.family_tree.check_relationship_consistency(self.p3.person_id)
        # p1 has no relationships, so no errors for p1
        self.assertEqual(errors_p1, [])
        # p3 still thinks p1 is parent, but p1 doesn't have corresponding parent relationship
        self.assertTrue(any("lacks corresponding 'parent' relationship" in e for e in errors_p3))

    def test_find_duplicates(self):
        """Test finding duplicate persons (basic check)."""
        # p1 = Alice Alpha (1950-01-01)
        p1_duplicate = Person(self.user_id, "Alice", "Alpha", person_id="p1_dup", date_of_birth="1950-01-01")
        p_different_name = Person(self.user_id, "Alicia", "Alpha", person_id="p_diff_name", date_of_birth="1950-01-01")
        p_different_dob = Person(self.user_id, "Alice", "Alpha", person_id="p_diff_dob", date_of_birth="1951-01-01")

        self.family_tree.add_person(p1_duplicate)
        self.family_tree.add_person(p_different_name)
        self.family_tree.add_person(p_different_dob)

        duplicates = self.family_tree.find_duplicates(threshold=0.9) # High threshold requires name and DOB match

        found_pair = False
        for p_a, p_b, score in duplicates:
            if {p_a.person_id, p_b.person_id} == {self.p1.person_id, p1_duplicate.person_id}:
                found_pair = True
                self.assertAlmostEqual(score, 1.0) # Should be perfect match with basic check
                break
        self.assertTrue(found_pair, "Expected duplicate pair (p1, p1_duplicate) not found.")
        self.assertEqual(len(duplicates), 1) # Only one pair should match perfectly

    def test_merge_persons(self):
        """Test merging two persons."""
        # Setup: p1 married to p2. p1_dup has relationship with p3.
        p1_dup = Person(self.user_id, "Alice", "Alpha", person_id="p1_dup", date_of_birth="1950-01-01")
        self.family_tree.add_person(p1_dup)

        rel_spouse = Relationship(self.p1.person_id, self.p2.person_id, "spouse")
        rel_friend = Relationship(p1_dup.person_id, self.p3.person_id, "friend")
        self.family_tree.link_persons(rel_spouse)
        self.family_tree.link_persons(rel_friend)

        # Add some unique data to duplicate
        p1_dup.add_document("dup_doc.txt")
        p1_dup.add_name("Ali", "nickname", "eng")

        # Merge p1_dup into p1
        self.family_tree.merge_persons(self.p1.person_id, p1_dup.person_id)

        # Verify p1_dup is removed
        self.assertIsNone(self.family_tree.get_person_by_id(p1_dup.person_id))

        # Verify data is merged into p1
        self.assertIn("dup_doc.txt", self.p1.documents)
        self.assertTrue(any(n['name'] == 'Ali' for n in self.p1.names))

        # Verify relationships are re-linked to p1
        # p1 should now have spouse relationship with p2 AND friend relationship with p3
        p1_rel_types = {rel.relationship_type for rel in self.p1.relationships}
        p1_others = {rel.get_other_person(self.p1.person_id) for rel in self.p1.relationships}

        self.assertIn("spouse", p1_rel_types)
        self.assertIn("friend", p1_rel_types)
        self.assertIn(self.p2.person_id, p1_others)
        self.assertIn(self.p3.person_id, p1_others)

        # Verify p3 now has friend relationship linked to p1
        self.assertTrue(any(r.relationship_type == "friend" and r.get_other_person(self.p3.person_id) == self.p1.person_id for r in self.p3.relationships))

        # Verify audit log calls for merge steps
        self.mock_audit_log.log_event.assert_any_call("system", "merge_start", f"Starting merge of {p1_dup.person_id} into {self.p1.person_id}.")
        self.mock_audit_log.log_event.assert_any_call("system-merge", "person_deleted", f"Deleted person: {p1_dup.person_id} ({p1_dup.get_full_name()})")
        self.mock_audit_log.log_event.assert_any_call("system", "merge_complete", f"Completed merge of {p1_dup.person_id} into {self.p1.person_id}.")


    def test_merge_persons_not_found(self):
        """Test merging raises ValueError if persons not found."""
        with self.assertRaisesRegex(ValueError, "Primary person nonexistent not found"):
            self.family_tree.merge_persons("nonexistent", self.p1.person_id)
        with self.assertRaisesRegex(ValueError, "Duplicate person nonexistent not found"):
            self.family_tree.merge_persons(self.p1.person_id, "nonexistent")

    # --- Import/Export Tests ---
    # These tests use mock_open to simulate file operations without actual files

    @patch("builtins.open", new_callable=mock_open, read_data='{"persons": [{"person_id": "p_json", "first_name": "Json", "last_name": "Person"}]}')
    def test_import_json(self, mock_file):
        """Test importing data from a JSON file."""
        self.family_tree.import_file("dummy.json")
        mock_file.assert_called_with("dummy.json", 'r', encoding='utf-8')
        self.assertIsNotNone(self.family_tree.get_person_by_id("p_json"))
        self.assertEqual(self.family_tree.get_person_by_id("p_json").get_full_name(), "Json Person")
        self.mock_audit_log.log_event.assert_any_call("system", "import_start", "Starting import from dummy.json.")
        self.mock_audit_log.log_event.assert_any_call("system-import", "person_added", "Added person: p_json (Json Person)")
        self.mock_audit_log.log_event.assert_any_call("system", "import_complete", "Import from dummy.json complete. Added 1 persons and 0 relationships.")


    @patch("builtins.open", new_callable=mock_open)
    def test_export_json(self, mock_file):
        """Test exporting data to a JSON file."""
        # Add data to export
        self.family_tree.link_persons(Relationship(self.p1.person_id, self.p2.person_id, "spouse"))
        self.family_tree.export_file("output.json")

        mock_file.assert_called_with("output.json", 'w', encoding='utf-8')
        # Get the data that was written to the mock file handle
        # mock_file() gives the file handle, .write.call_args gives args passed to write
        written_data_json = mock_file().write.call_args[0][0]
        written_data = json.loads(written_data_json) # Assumes plain JSON for test

        self.assertIn("persons", written_data)
        self.assertIn("relationships", written_data)
        self.assertEqual(len(written_data["persons"]), 3) # p1, p2, p3 from setUp
        self.assertEqual(len(written_data["relationships"]), 1) # spouse rel
        self.assertEqual(written_data["relationships"][0]["relationship_type"], "spouse")
        self.mock_audit_log.log_event.assert_any_call("system", "export_start", "Starting export to output.json.")
        self.mock_audit_log.log_event.assert_any_call("system", "export_complete", "Export to output.json complete.")


    @patch("builtins.open", new_callable=mock_open, read_data='person_id,first_name,last_name\np_csv,Csv,Person')
    def test_import_csv(self, mock_file):
        """Test importing data from a CSV file."""
        self.family_tree.import_file("dummy.csv")
        mock_file.assert_called_with("dummy.csv", 'r', encoding='utf-8', newline='')
        self.assertIsNotNone(self.family_tree.get_person_by_id("p_csv"))
        self.assertEqual(self.family_tree.get_person_by_id("p_csv").get_full_name(), "Csv Person")

    @patch("builtins.open", new_callable=mock_open)
    def test_export_csv(self, mock_file):
        """Test exporting data to a CSV file."""
        self.family_tree.export_file("output.csv")
        mock_file.assert_called_with("output.csv", 'w', encoding='utf-8', newline='')
        written_data = mock_file().write.call_args_list
        # Check header and data row (basic check)
        self.assertIn("person_id,creator_user_id", written_data[0][0][0]) # Header
        self.assertIn(self.p1.person_id, written_data[1][0][0]) # Data for p1


    @patch("builtins.open", new_callable=mock_open, read_data='<family_tree><persons><person person_id="p_xml" first_name="Xml" last_name="Person"/></persons></family_tree>')
    @patch("xml.etree.ElementTree.parse") # Mock the XML parser
    def test_import_xml(self, mock_parse, mock_file):
        """Test importing data from an XML file."""
        # Configure the mock XML parser
        mock_person_elem = MagicMock()
        mock_person_elem.attrib = {"person_id": "p_xml", "first_name": "Xml", "last_name": "Person"}
        mock_persons_root = MagicMock()
        mock_persons_root.findall.return_value = [mock_person_elem] # Return mock person element
        mock_relationships_root = MagicMock()
        mock_relationships_root.findall.return_value = [] # No relationships in this test
        mock_root = MagicMock()
        # Make findall return the correct mock based on the tag searched
        mock_root.findall.side_effect = lambda path: mock_persons_root.findall(path) if 'person' in path else mock_relationships_root.findall(path)

        mock_tree = MagicMock()
        mock_tree.getroot.return_value = mock_root
        mock_parse.return_value = mock_tree

        self.family_tree.import_file("dummy.xml")
        mock_file.assert_called_with("dummy.xml", 'r', encoding='utf-8') # Check open call
        mock_parse.assert_called_with("dummy.xml") # Check ET.parse call
        self.assertIsNotNone(self.family_tree.get_person_by_id("p_xml"))
        self.assertEqual(self.family_tree.get_person_by_id("p_xml").get_full_name(), "Xml Person")


    @patch("builtins.open", new_callable=mock_open)
    @patch("xml.etree.ElementTree.ElementTree") # Mock the tree object
    def test_export_xml(self, mock_ET_Tree, mock_file):
        """Test exporting data to an XML file."""
        mock_tree_instance = MagicMock()
        mock_ET_Tree.return_value = mock_tree_instance # ET.ElementTree(root) returns mock

        self.family_tree.export_file("output.xml")

        mock_file.assert_called_with("output.xml", 'w', encoding='utf-8')
        # Check that the write method was called on the mock tree instance
        mock_tree_instance.write.assert_called_once()
        # Further checks could inspect the structure passed to ET.ElementTree if needed

    # Add GEDCOM tests if library is available and mocked appropriately

    def test_search_person(self):
        """Test searching for persons."""
        # p1 = Alice Alpha, p2 = Bob Beta, p3 = Charlie Alpha
        results_name = self.family_tree.search_person("Alpha", fields=["names"])
        self.assertCountEqual([p.person_id for p in results_name], [self.p1.person_id, self.p3.person_id])

        results_dob = self.family_tree.search_person("1952", fields=["date_of_birth"])
        self.assertEqual([p.person_id for p in results_dob], [self.p2.person_id])

        results_partial_name = self.family_tree.search_person("ali", fields=["names"])
        self.assertEqual([p.person_id for p in results_partial_name], [self.p1.person_id]) # Alice

        results_no_match = self.family_tree.search_person("Zebra", fields=["names"])
        self.assertEqual(results_no_match, [])

    # Add tests for reporting methods if needed


if __name__ == "__main__":
    unittest.main()
