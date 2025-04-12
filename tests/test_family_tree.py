# tests/test_family_tree.py
import unittest
import os
import json
import csv
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock, mock_open, ANY # Import ANY
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship
from src.audit_log import AuditLog # Assuming AuditLog is needed for mock type hint
from src.encryption import DataEncryptor # Assuming for mock type hint

# Mock placeholder classes if they are not importable or complex
class MockAuditLog:
    def log_event(self, user, event, description):
        print(f"AUDIT LOG MOCK [{user}] {event}: {description}")

class MockDataEncryptor:
    def encrypt(self, data):
        return data # Passthrough for testing
    def decrypt(self, data):
        return data # Passthrough for testing

class TestFamilyTree(unittest.TestCase):
    """Unit tests for the FamilyTree class."""

    def setUp(self):
        """Set up a fresh family tree and mock dependencies for each test."""
        # Use mock objects for dependencies
        self.mock_audit_log = MagicMock(spec=AuditLog)
        self.mock_encryptor = MagicMock(spec=DataEncryptor)
        self.mock_encryptor.encrypt.side_effect = lambda d: d # Mock encryption passthrough
        self.mock_encryptor.decrypt.side_effect = lambda d: d # Mock decryption passthrough

        self.family_tree = FamilyTree(audit_log=self.mock_audit_log, encryptor=self.mock_encryptor)

        # Add some initial data for tests that need it
        self.person1 = Person(person_id="p1", first_name="Alice", last_name="Alpha")
        self.person2 = Person(person_id="p2", first_name="Bob", last_name="Beta")
        self.person3 = Person(person_id="p3", first_name="Charlie", last_name="Gamma") # Changed last name for clarity
        self.family_tree.add_person(self.person1, user="system")
        self.family_tree.add_person(self.person2, user="system")
        self.family_tree.add_person(self.person3, user="system")
        self.family_tree.add_relationship("p1", "p2", "spouse", user="system")
        self.family_tree.add_relationship("p3", "p1", "child", user="system") # p3 is child of p1

        # Reset mocks for calls made during setup if necessary for specific tests
        self.mock_audit_log.reset_mock()

    def test_add_person(self):
        """Test adding a person."""
        # Person data is now added in setUp, let's test adding another one
        new_person_data = {'person_id': 'p4', 'first_name': 'David', 'last_name': 'Delta'}
        new_person = Person(**new_person_data)
        self.family_tree.add_person(new_person, user="test_user")

        # Check if person was added
        self.assertIn("p4", self.family_tree.persons)
        self.assertEqual(self.family_tree.persons["p4"].first_name, "David")

        # Check if audit log was called correctly for this specific addition
        self.mock_audit_log.log_event.assert_called_with(
            "test_user",
            "person_added",
            f"Added person: p4 ({new_person.get_full_name()})" # Use the actual person added
        )

    def test_add_person_duplicate_id(self):
        """Test adding a person with a duplicate ID."""
        person_dup = Person(person_id="p1", first_name="Alicia", last_name="Alpha")
        with self.assertRaises(ValueError):
            self.family_tree.add_person(person_dup, user="test_user")
        # Ensure no audit log event for the failed addition attempt
        # This depends on implementation detail (log before or after check)
        # Let's assume it doesn't log if it fails early. If it does, adjust assertion.

    def test_get_person(self):
        """Test retrieving a person."""
        person = self.family_tree.get_person("p1")
        self.assertIsNotNone(person)
        self.assertEqual(person.person_id, "p1")
        self.assertEqual(person.first_name, "Alice")

    def test_get_person_not_found(self):
        """Test retrieving a non-existent person."""
        person = self.family_tree.get_person("p99")
        self.assertIsNone(person)

    def test_update_person(self):
        """Test updating a person's details."""
        update_data = {"first_name": "Alicia", "last_name": "AlphaUpdated"}
        success = self.family_tree.update_person("p1", update_data, user="test_user")
        self.assertTrue(success)
        updated_person = self.family_tree.get_person("p1")
        self.assertEqual(updated_person.first_name, "Alicia")
        self.assertEqual(updated_person.last_name, "AlphaUpdated")
        self.mock_audit_log.log_event.assert_called_with(
            "test_user",
            "person_updated",
            f"Updated person: p1 (Alicia AlphaUpdated)" # Check against updated name
        )

    def test_update_person_not_found(self):
        """Test updating a non-existent person."""
        update_data = {"first_name": "Nobody"}
        success = self.family_tree.update_person("p99", update_data, user="test_user")
        self.assertFalse(success)
        # Ensure no audit log event for failed update
        # self.mock_audit_log.log_event.assert_not_called() # Be careful if other logs happen

    def test_delete_person(self):
        """Test deleting a person and cleaning up their relationships."""
        # Ensure relationships exist before deletion
        self.assertIn("p1", self.family_tree.relationships)
        self.assertTrue(any(r.person2_id == "p2" for r in self.family_tree.relationships.get("p1", []))) # p1 -> p2 spouse
        self.assertTrue(any(r.person2_id == "p3" for r in self.family_tree.relationships.get("p1", []))) # p1 -> p3 parent (derived)
        self.assertIn("p2", self.family_tree.relationships)
        self.assertTrue(any(r.person2_id == "p1" for r in self.family_tree.relationships.get("p2", []))) # p2 -> p1 spouse
        self.assertIn("p3", self.family_tree.relationships)
        self.assertTrue(any(r.person2_id == "p1" for r in self.family_tree.relationships.get("p3", []))) # p3 -> p1 child

        # Delete person p1
        success = self.family_tree.delete_person("p1", user="test_user")
        self.assertTrue(success)

        # Check person is removed
        self.assertNotIn("p1", self.family_tree.persons)

        # Check relationships involving p1 are removed from other persons' entries
        self.assertNotIn("p1", self.family_tree.relationships) # p1's own entry removed
        if "p2" in self.family_tree.relationships: # Check if p2 still has relationships
             self.assertFalse(any(r.person2_id == "p1" for r in self.family_tree.relationships.get("p2", [])))
        if "p3" in self.family_tree.relationships: # Check if p3 still has relationships
             self.assertFalse(any(r.person2_id == "p1" for r in self.family_tree.relationships.get("p3", [])))

        # Check audit logs
        # Use ANY for the relationship representation string if it's complex or varies
        self.mock_audit_log.log_event.assert_any_call(
            "test_user",
            "relationship_removed",
            # Match the exact string format from your application code
            # Example: "Removed relationship involving deleted person p1: p1 <-> p2 (spouse)"
            # Using ANY if the exact string is hard to predict or match reliably
            f"Removed relationship involving deleted person p1: {ANY}"
        )
        self.mock_audit_log.log_event.assert_any_call(
            "test_user",
            "relationship_removed",
             # Example: "Removed relationship involving deleted person p1: p3 -> p1 (child)"
            f"Removed relationship involving deleted person p1: {ANY}"
        )
         # Check the main deletion log event
        self.mock_audit_log.log_event.assert_any_call(
            "test_user",
            "person_deleted",
            "Deleted person: p1 (Alice Alpha)" # Name before deletion
        )

    def test_delete_person_not_found(self):
        """Test deleting a non-existent person."""
        success = self.family_tree.delete_person("p99", user="test_user")
        self.assertFalse(success)

    def test_add_relationship(self):
        """Test adding a relationship."""
        # Relationship p1-p2 (spouse) and p3-p1 (child) added in setUp
        # Add a new one: p2 is child of p4 (p4 needs to exist first)
        person4 = Person(person_id="p4", first_name="David", last_name="Delta")
        self.family_tree.add_person(person4, user="system")
        self.mock_audit_log.reset_mock() # Reset after setup/adding p4

        success = self.family_tree.add_relationship("p2", "p4", "child", user="test_user")
        self.assertTrue(success)

        # Check relationship exists in both directions (if reciprocal)
        self.assertIn("p2", self.family_tree.relationships)
        self.assertTrue(any(r.person2_id == "p4" and r.rel_type == "child" for r in self.family_tree.relationships["p2"]))
        self.assertIn("p4", self.family_tree.relationships)
        # Check for the reciprocal relationship (parent)
        self.assertTrue(any(r.person2_id == "p2" and r.rel_type == "parent" for r in self.family_tree.relationships["p4"]))

        # Check audit log
        # Check both the primary and reciprocal relationship logs
        self.mock_audit_log.log_event.assert_any_call(
            "test_user",
            "relationship_added",
            f"Added relationship: {ANY}" # Use ANY or the exact format
        )


    def test_add_relationship_person_not_found(self):
        """Test adding a relationship with a non-existent person."""
        with self.assertRaises(ValueError):
            self.family_tree.add_relationship("p1", "p99", "sibling", user="test_user")
        with self.assertRaises(ValueError):
            self.family_tree.add_relationship("p99", "p1", "sibling", user="test_user")

    def test_get_relationships(self):
        """Test retrieving relationships for a person."""
        rels = self.family_tree.get_relationships("p1")
        self.assertIsNotNone(rels)
        self.assertEqual(len(rels), 2) # spouse(p2), parent(p3) - derived from child(p3->p1)

        rel_types = {r.rel_type for r in rels}
        person_ids = {r.person2_id for r in rels}

        self.assertIn("spouse", rel_types)
        self.assertIn("parent", rel_types) # Derived from child relationship
        self.assertIn("p2", person_ids)
        self.assertIn("p3", person_ids)


    def test_get_relationships_not_found(self):
        """Test retrieving relationships for a non-existent person."""
        rels = self.family_tree.get_relationships("p99")
        self.assertEqual(rels, []) # Should return empty list

    def test_update_relationship(self):
        """Test updating an existing relationship."""
        # Update p1-p2 from spouse to divorced
        success = self.family_tree.update_relationship("p1", "p2", "spouse", {"rel_type": "divorced"}, user="test_user")
        self.assertTrue(success)

        # Check relationship type is updated for p1 -> p2
        p1_rels = self.family_tree.get_relationships("p1")
        p1_p2_rel = next((r for r in p1_rels if r.person2_id == "p2"), None)
        self.assertIsNotNone(p1_p2_rel)
        self.assertEqual(p1_p2_rel.rel_type, "divorced")

        # Check reciprocal relationship type is updated for p2 -> p1
        p2_rels = self.family_tree.get_relationships("p2")
        p2_p1_rel = next((r for r in p2_rels if r.person2_id == "p1"), None)
        self.assertIsNotNone(p2_p1_rel)
        self.assertEqual(p2_p1_rel.rel_type, "divorced") # Assuming reciprocal update

        # Check audit log
        self.mock_audit_log.log_event.assert_any_call( # Use any_call if multiple updates logged
            "test_user",
            "relationship_updated",
            f"Updated relationship: {ANY}" # Use ANY or exact format
        )

    def test_update_relationship_not_found(self):
        """Test updating a non-existent relationship."""
        success = self.family_tree.update_relationship("p1", "p3", "sibling", {"notes": "abc"}, user="test_user")
        self.assertFalse(success)

    def test_delete_relationship(self):
        """Test deleting a specific relationship."""
        # Delete p1 <-> p2 (spouse) relationship
        success = self.family_tree.delete_relationship("p1", "p2", "spouse", user="test_user")
        self.assertTrue(success)

        # Check relationship is removed for p1
        p1_rels = self.family_tree.get_relationships("p1")
        self.assertFalse(any(r.person2_id == "p2" for r in p1_rels))

        # Check relationship is removed for p2
        p2_rels = self.family_tree.get_relationships("p2")
        self.assertFalse(any(r.person2_id == "p1" for r in p2_rels))

        # Check audit log
        self.mock_audit_log.log_event.assert_any_call( # Use any_call for multiple logs
            "test_user",
            "relationship_removed",
            f"Removed relationship: {ANY}" # Use ANY or exact format
        )

    def test_delete_relationship_not_found(self):
        """Test deleting a non-existent relationship."""
        success = self.family_tree.delete_relationship("p1", "p3", "sibling", user="test_user")
        self.assertFalse(success)

    # --- Import/Export Tests ---

    @patch("builtins.open", new_callable=mock_open, read_data='{"persons": [{"person_id": "p10", "first_name": "Imported"}], "relationships": []}')
    @patch("os.path.exists", return_value=True) # Mock file existence
    def test_import_json(self, mock_exists, mock_file):
        """Test importing data from a JSON file."""
        self.family_tree.import_file("dummy.json", user="test_user")
        mock_file.assert_called_once_with("dummy.json", 'r', encoding='utf-8')
        self.assertIn("p10", self.family_tree.persons)
        self.assertEqual(self.family_tree.persons["p10"].first_name, "Imported")
        # Check audit log for import start/end or individual items
        self.mock_audit_log.log_event.assert_any_call("test_user", "import_started", "Started import from dummy.json")
        self.mock_audit_log.log_event.assert_any_call("test_user", "person_added", "Added person: p10 (Imported)")


    @patch("builtins.open", new_callable=mock_open)
    def test_export_json(self, mock_file):
        """Test exporting data to a JSON file."""
        self.family_tree.export_file("output.json", user="test_user")

        # Check that open was called correctly
        mock_file.assert_called_once_with("output.json", 'w', encoding='utf-8')

        # Get all data written to the mock file handle
        # mock_open().write() accumulates calls; access them via handle.write_calls
        handle = mock_file()
        # Combine all written chunks into a single string
        written_data_json = "".join(call.args[0] for call in handle.write.call_args_list)

        # Check if *something* was written (basic check)
        self.assertTrue(len(written_data_json) > 0, "No data written to JSON file mock")

        # Now try to parse the written data
        try:
            written_data = json.loads(written_data_json)
        except json.JSONDecodeError as e:
            self.fail(f"Failed to decode JSON written by export_file: {e}\nData: {written_data_json}")

        # Validate structure and content (example)
        self.assertIn("persons", written_data)
        self.assertIn("relationships", written_data)
        self.assertEqual(len(written_data["persons"]), 3) # p1, p2, p3 from setup
        # Find person p1 in the exported data
        p1_exported = next((p for p in written_data["persons"] if p.get("person_id") == "p1"), None)
        self.assertIsNotNone(p1_exported)
        self.assertEqual(p1_exported.get("first_name"), "Alice")

        # Check audit log
        self.mock_audit_log.log_event.assert_called_with("test_user", "export_completed", "Exported data to output.json")


    # Mock CSV data: header + one person
    csv_data = "person_id,first_name,last_name\np10,Imported,CSV\n"
    @patch("builtins.open", mock_open(read_data=csv_data))
    @patch("os.path.exists", return_value=True)
    def test_import_csv(self, mock_exists, mock_file):
        """Test importing data from a CSV file."""
        # Note: CSV import might only handle persons, or need separate files. Adjust based on implementation.
        # Assuming a simple CSV format for persons for this test.
        self.family_tree.import_file("dummy.csv", user="test_user")
        mock_file.assert_called_once_with("dummy.csv", 'r', newline='', encoding='utf-8')
        self.assertIn("p10", self.family_tree.persons)
        self.assertEqual(self.family_tree.persons["p10"].first_name, "Imported")
        self.assertEqual(self.family_tree.persons["p10"].last_name, "CSV")
        self.mock_audit_log.log_event.assert_any_call("test_user", "import_started", "Started import from dummy.csv")
        self.mock_audit_log.log_event.assert_any_call("test_user", "person_added", "Added person: p10 (Imported CSV)")

    @patch("builtins.open", new_callable=mock_open)
    def test_export_csv(self, mock_file):
        """Test exporting data to a CSV file."""
        # Assuming export_file handles .csv extension for person export
        self.family_tree.export_file("output.csv", user="test_user")
        mock_file.assert_called_once_with("output.csv", 'w', newline='', encoding='utf-8')

        # Check content written
        handle = mock_file()
        written_data_csv = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertTrue(len(written_data_csv) > 0, "No data written to CSV file mock")
        # Basic check for header and data (adjust columns as needed)
        self.assertIn("person_id,first_name,last_name", written_data_csv) # Example header
        self.assertIn("p1,Alice,Alpha", written_data_csv) # Example data

        self.mock_audit_log.log_event.assert_called_with("test_user", "export_completed", "Exported data to output.csv")


    # Mock XML data
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<family_tree>
    <persons>
        <person person_id="p10">
            <first_name>Imported</first_name>
            <last_name>XML</last_name>
        </person>
    </persons>
    <relationships/>
</family_tree>
"""
    @patch("builtins.open", mock_open(read_data=xml_data))
    @patch("os.path.exists", return_value=True)
    def test_import_xml(self, mock_exists, mock_file):
        """Test importing data from an XML file."""
        self.family_tree.import_file("dummy.xml", user="test_user")
        mock_file.assert_called_once_with("dummy.xml", 'r', encoding='utf-8')
        self.assertIn("p10", self.family_tree.persons)
        self.assertEqual(self.family_tree.persons["p10"].first_name, "Imported")
        self.assertEqual(self.family_tree.persons["p10"].last_name, "XML")
        self.mock_audit_log.log_event.assert_any_call("test_user", "import_started", "Started import from dummy.xml")
        self.mock_audit_log.log_event.assert_any_call("test_user", "person_added", "Added person: p10 (Imported XML)")


    @patch("xml.etree.ElementTree.ElementTree.write") # Patch the write method of the ET instance
    def test_export_xml(self, mock_et_write):
        """Test exporting data to an XML file."""
        # We patch the write method directly to avoid issues with mock_open and binary/text mode for XML
        self.family_tree.export_file("output.xml", user="test_user")

        # Check that the write method was called, indicating export process ran
        mock_et_write.assert_called_once()

        # Optionally, inspect the arguments passed to write if needed
        # args, kwargs = mock_et_write.call_args
        # self.assertEqual(args[0], "output.xml") # Check filename passed to write
        # self.assertEqual(kwargs.get('encoding'), 'utf-8')
        # self.assertTrue(kwargs.get('xml_declaration'))

        # Check audit log
        self.mock_audit_log.log_event.assert_called_with("test_user", "export_completed", "Exported data to output.xml")


    def test_find_person_by_name(self):
        """Test finding persons by name."""
        results = self.family_tree.find_person_by_name("Alice")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].person_id, "p1")

        results = self.family_tree.find_person_by_name("Beta") # Last name
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].person_id, "p2")

        results = self.family_tree.find_person_by_name("NonExistent")
        self.assertEqual(len(results), 0)

    def test_find_relationships_by_type(self):
        """Test finding relationships by type."""
        results = self.family_tree.find_relationships_by_type("spouse")
        self.assertEqual(len(results), 1) # Only p1-p2 relationship is spouse
        rel = results[0]
        # Check if the relationship involves p1 and p2
        self.assertTrue( (rel.person1_id == "p1" and rel.person2_id == "p2") or \
                         (rel.person1_id == "p2" and rel.person2_id == "p1") )
        self.assertEqual(rel.rel_type, "spouse")

        results = self.family_tree.find_relationships_by_type("child")
        self.assertEqual(len(results), 1) # p3 -> p1
        self.assertEqual(results[0].person1_id, "p3")
        self.assertEqual(results[0].person2_id, "p1")

        results = self.family_tree.find_relationships_by_type("sibling")
        self.assertEqual(len(results), 0)

    # Add more tests for edge cases, encryption/decryption hooks, complex scenarios etc.

if __name__ == '__main__':
    unittest.main()
