import unittest
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship
from src.encryption import DataEncryptor


class TestFamilyTree(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
        self.encryptor = DataEncryptor("test_key")
        self.family_tree = FamilyTree(encryption_key="test_key")
        self.person1 = Person(
            "person1", "Name1", "LastName1", "1970-01-01", "Place1", encryption_key="test_key"
        )
        self.person2 = Person(
            "person2", "Name2", "LastName2", "1975-05-10", "Place2", encryption_key="test_key"
        )
        self.person3 = Person(
            "person3", "Name3", "LastName3", "1995-11-15", "Place3", encryption_key="test_key"
        )

    def test_add_person(self):
        """Test adding a person to the family tree."""
        self.family_tree.add_person(self.person1)
        self.assertIn(self.person1.person_id, self.family_tree.person_nodes)

    def test_add_person_with_parents(self):
        """Test adding a person to the family tree with parents."""
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        self.family_tree.add_person(self.person3, [self.person1, self.person2])
        self.assertEqual(
            self.family_tree.person_nodes[self.person3.person_id]["parents"],
            [self.person1, self.person2],
        )

    def test_add_person_duplicate(self):
        """Test adding a duplicate person to the family tree."""
        self.family_tree.add_person(self.person1)
        with self.assertRaises(ValueError):
            self.family_tree.add_person(self.person1)

    def test_add_person_invalid_parent(self):
        """Test adding a person with an invalid parent to the family tree."""
        with self.assertRaises(ValueError):
            self.family_tree.add_person(self.person3, [self.person1])

    def test_link_persons(self):
        """Test linking two persons in the family tree."""
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        relationship = Relationship(self.person1.person_id, self.person2.person_id, "spouse")
        self.family_tree.link_persons(relationship)
        self.assertIn(relationship, self.person1.relationships.values())
        self.assertIn(relationship, self.person2.relationships.values())

    def test_get_person_by_id(self):
        """Test getting a person by ID."""
        self.family_tree.add_person(self.person1)
        retrieved_person = self.family_tree.get_person_by_id(self.person1.person_id)
        self.assertEqual(retrieved_person, self.person1)

    def test_get_person_by_id_not_found(self):
        """Test getting a non-existent person by ID."""
        retrieved_person = self.family_tree.get_person_by_id("nonexistent")
        self.assertIsNone(retrieved_person)

    def test_check_relationship_consistency(self):
        """Test relationship consistency check."""
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        relationship = Relationship(self.person1.person_id, self.person2.person_id, "spouse")
        self.family_tree.link_persons(relationship)
        self.assertEqual(
            self.family_tree.check_relationship_consistency(self.person1.person_id), []
        )

    def test_check_relationship_consistency_inconsistent(self):
        """Test relationship consistency check with inconsistent data."""
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        relationship = Relationship(self.person1.person_id, self.person2.person_id, "child")

        self.family_tree.link_persons(relationship)
        self.assertNotEqual(
            self.family_tree.check_relationship_consistency(self.person1.person_id), []
        )

    def test_merge_persons(self):
        """Test merging two persons."""
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        self.family_tree.merge_persons(self.person1.person_id, self.person2.person_id)
        self.assertIn(self.person1.person_id, self.family_tree.person_nodes)
        self.assertNotIn(self.person2.person_id, self.family_tree.person_nodes)

    def test_merge_persons_not_found(self):
        """Test merging with a non-existent person."""
        self.family_tree.add_person(self.person1)
        with self.assertRaises(ValueError):
            self.family_tree.merge_persons(self.person1.person_id, "nonexistent")

    def test_find_duplicates(self):
        """Test finding duplicate persons."""
        duplicate = Person(
            "person4", "Name1", "LastName1", "1970-01-01", "Place1", encryption_key="test_key"
        )
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        self.family_tree.add_person(duplicate)
        duplicates = self.family_tree.find_duplicates()
        self.assertIn([self.person1, duplicate], duplicates)

    def test_import_export_json(self):
        """Test importing and exporting data in JSON format."""
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        relationship = Relationship(self.person1.person_id, self.person2.person_id, "spouse")
        self.family_tree.link_persons(relationship)
        self.family_tree.export_json("test.json")
        new_tree = FamilyTree(encryption_key="test_key")
        new_tree.import_json("test.json")
        self.assertIn(self.person1.person_id, new_tree.person_nodes)
        self.assertIn(self.person2.person_id, new_tree.person_nodes)
        self.assertEqual(len(new_tree.person_nodes), 2)
        self.assertIn(relationship, new_tree.get_person_by_id(self.person1.person_id).relationships.values())
        self.assertIn(relationship, new_tree.get_person_by_id(self.person2.person_id).relationships.values())

    def test_search_person(self):
        """Test searching for a person."""
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        results = self.family_tree.search_person("Name1", ["names"])
        self.assertIn(self.person1, results)

    def test_import_json_invalid(self):
        """Test import json with invalid file."""
        with self.assertRaises(ValueError):
            self.family_tree.import_json("invalid.txt")

    def test_import_csv_invalid(self):
        """Test import csv with invalid file."""
        with self.assertRaises(ValueError):
            self.family_tree.import_csv("invalid.txt")

    def test_import_xml_invalid(self):
        """Test import xml with invalid file."""
        with self.assertRaises(ValueError):
            self.family_tree.import_xml("invalid.txt")

    def test_import_gedcom_invalid(self):
        """Test import gedcom with invalid file."""
        with self.assertRaises(ValueError):
            self.family_tree.import_gedcom("invalid.txt")

    def test_check_all_relationship_consistency(self):
        """Test check all relationship consistency method."""
        self.family_tree.add_person(self.person1)
        self.family_tree.add_person(self.person2)
        self.family_tree.add_person(self.person3)
        relationship = Relationship(self.person1.person_id, self.person2.person_id, "spouse")
        self.family_tree.link_persons(relationship)
        self.family_tree.check_all_relationship_consistency()


if __name__ == "__main__":
    unittest.main()