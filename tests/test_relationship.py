# tests/test_relationship.py
import unittest
from datetime import datetime

from src.relationship import Relationship, RELATIONSHIP_TYPES

class TestRelationship(unittest.TestCase):
    """Test suite for the refactored Relationship class."""

    def test_valid_relationship_initialization(self):
        """Test initializing with valid standard types."""
        for rel_type in RELATIONSHIP_TYPES:
            if rel_type == "other": continue # Test 'other' separately if needed
            try:
                rel = Relationship("p1", "p2", rel_type)
                self.assertEqual(rel.person1_id, "p1")
                self.assertEqual(rel.person2_id, "p2")
                self.assertEqual(rel.relationship_type, rel_type)
                self.assertIsNone(rel.start_date)
                self.assertIsNone(rel.end_date)
                self.assertIsNone(rel.description)
            except ValueError:
                self.fail(f"Initialization failed for valid type: {rel_type}")

    def test_non_standard_relationship_type(self):
        """Test initializing with a non-standard type (should warn but succeed)."""
        # Assuming the refactored class allows non-standard types with a warning
        rel_custom = Relationship("p1", "p2", "mentor")
        self.assertEqual(rel_custom.relationship_type, "mentor")
        # Check if warning was printed (requires capturing stdout/stderr, more complex test)

    def test_relationship_with_all_attributes(self):
        """Test initializing with all optional attributes."""
        rel = Relationship(
            "person_a", "person_b", "spouse",
            start_date="2000-01-15",
            end_date="2010-12-31",
            description="First marriage"
        )
        self.assertEqual(rel.person1_id, "person_a")
        self.assertEqual(rel.person2_id, "person_b")
        self.assertEqual(rel.relationship_type, "spouse")
        self.assertIsInstance(rel.start_date, datetime)
        self.assertEqual(rel.start_date.year, 2000)
        self.assertEqual(rel.start_date.day, 15)
        self.assertIsInstance(rel.end_date, datetime)
        self.assertEqual(rel.end_date.year, 2010)
        self.assertEqual(rel.description, "First marriage")

    def test_invalid_date_format(self):
        """Test initialization with invalid date strings (should result in None)."""
        rel = Relationship("p1", "p2", "friend", start_date="invalid-date")
        self.assertIsNone(rel.start_date)
        # Check if warning was printed (requires capturing stdout/stderr)

    def test_relationship_to_self_error(self):
        """Test that creating a relationship to oneself raises ValueError."""
        with self.assertRaisesRegex(ValueError, "Cannot create a relationship between a person and themselves"):
            Relationship("p1", "p1", "sibling")

    def test_equality_asymmetric(self):
        """Test equality for asymmetric relationships (e.g., parent/child)."""
        rel1 = Relationship("p1", "p2", "parent", start_date="1990-01-01")
        rel2 = Relationship("p1", "p2", "parent", start_date="1990-01-01") # Identical
        rel3 = Relationship("p2", "p1", "parent", start_date="1990-01-01") # Reversed persons
        rel4 = Relationship("p1", "p2", "child", start_date="1990-01-01")  # Different type
        rel5 = Relationship("p1", "p2", "parent", start_date="1991-01-01")  # Different date

        self.assertEqual(rel1, rel2)
        self.assertNotEqual(rel1, rel3) # Order matters for parent/child
        self.assertNotEqual(rel1, rel4)
        self.assertNotEqual(rel1, rel5)
        self.assertNotEqual(rel1, "not a relationship")

    def test_equality_symmetric(self):
        """Test equality for symmetric relationships (e.g., spouse, sibling)."""
        rel1 = Relationship("p1", "p2", "spouse", start_date="2000-01-01")
        rel2 = Relationship("p1", "p2", "spouse", start_date="2000-01-01") # Identical
        rel3 = Relationship("p2", "p1", "spouse", start_date="2000-01-01") # Reversed persons
        rel4 = Relationship("p1", "p2", "sibling", start_date="2000-01-01") # Different type
        rel5 = Relationship("p1", "p2", "spouse", start_date="2001-01-01") # Different date

        self.assertEqual(rel1, rel2)
        self.assertEqual(rel1, rel3) # Order does NOT matter for spouse
        self.assertNotEqual(rel1, rel4)
        self.assertNotEqual(rel1, rel5)

    def test_hash_consistency(self):
        """Test that hash is consistent with equality."""
        # Asymmetric
        rel1_parent = Relationship("p1", "p2", "parent")
        rel2_parent = Relationship("p1", "p2", "parent")
        rel3_parent_rev = Relationship("p2", "p1", "parent")
        self.assertEqual(hash(rel1_parent), hash(rel2_parent))
        self.assertNotEqual(hash(rel1_parent), hash(rel3_parent_rev))

        # Symmetric
        rel1_spouse = Relationship("p1", "p2", "spouse")
        rel2_spouse = Relationship("p1", "p2", "spouse")
        rel3_spouse_rev = Relationship("p2", "p1", "spouse")
        self.assertEqual(hash(rel1_spouse), hash(rel2_spouse))
        self.assertEqual(hash(rel1_spouse), hash(rel3_spouse_rev)) # Hashes must be equal if objects are equal

        # Different types or attributes should have different hashes
        rel4_sibling = Relationship("p1", "p2", "sibling")
        rel5_spouse_date = Relationship("p1", "p2", "spouse", start_date="2000-01-01")
        self.assertNotEqual(hash(rel1_spouse), hash(rel4_sibling))
        self.assertNotEqual(hash(rel1_spouse), hash(rel5_spouse_date))


    def test_involves_person(self):
        """Test the involves_person method."""
        rel = Relationship("p1", "p2", "friend")
        self.assertTrue(rel.involves_person("p1"))
        self.assertTrue(rel.involves_person("p2"))
        self.assertFalse(rel.involves_person("p3"))

    def test_get_other_person(self):
        """Test the get_other_person method."""
        rel = Relationship("p1", "p2", "friend")
        self.assertEqual(rel.get_other_person("p1"), "p2")
        self.assertEqual(rel.get_other_person("p2"), "p1")
        self.assertIsNone(rel.get_other_person("p3")) # Person not involved

    def test_to_dict(self):
        """Test converting the relationship to a dictionary."""
        rel = Relationship(
            "person_a", "person_b", "sibling",
            start_date="1995-01-01", description="Full siblings"
        )
        expected_dict = {
            "person1_id": "person_a",
            "person2_id": "person_b",
            "relationship_type": "sibling",
            "start_date": "1995-01-01T00:00:00", # ISO format
            "end_date": None,
            "description": "Full siblings",
        }
        self.assertEqual(rel.to_dict(), expected_dict)

        rel_no_optional = Relationship("c1", "p1", "child")
        expected_dict_no_optional = {
            "person1_id": "c1",
            "person2_id": "p1",
            "relationship_type": "child",
            "start_date": None,
            "end_date": None,
            "description": None,
        }
        self.assertEqual(rel_no_optional.to_dict(), expected_dict_no_optional)

    def test_from_dict(self):
        """Test creating a relationship from a dictionary."""
        rel_data = {
            "person1_id": "person_a",
            "person2_id": "person_b",
            "relationship_type": "sibling",
            "start_date": "1995-01-01T00:00:00",
            "description": "Full siblings",
        }
        rel = Relationship.from_dict(rel_data)
        self.assertEqual(rel.person1_id, "person_a")
        self.assertEqual(rel.relationship_type, "sibling")
        self.assertIsInstance(rel.start_date, datetime)
        self.assertEqual(rel.start_date.year, 1995)
        self.assertIsNone(rel.end_date)
        self.assertEqual(rel.description, "Full siblings")

        # Test with missing optional fields
        rel_data_minimal = {
            "person1_id": "c1",
            "person2_id": "p1",
            "relationship_type": "child",
        }
        rel_minimal = Relationship.from_dict(rel_data_minimal)
        self.assertEqual(rel_minimal.relationship_type, "child")
        self.assertIsNone(rel_minimal.start_date)
        self.assertIsNone(rel_minimal.description)


    def test_string_representation(self):
        """Test __str__ and __repr__ methods."""
        rel_spouse = Relationship("p1", "p2", "spouse", start_date="2000-01-01", end_date="2010-12-31", description="Married")
        self.assertIn("p1 <-> p2", str(rel_spouse))
        self.assertIn("(spouse)", str(rel_spouse))
        self.assertIn("from 2000-01-01", str(rel_spouse))
        self.assertIn("to 2010-12-31", str(rel_spouse))
        self.assertIn("(Married)", str(rel_spouse))

        rel_child = Relationship("c1", "p1", "child")
        self.assertIn("c1 <-> p1", str(rel_child))
        self.assertIn("(child)", str(rel_child))
        self.assertNotIn("from", str(rel_child))
        self.assertNotIn("to", str(rel_child))
        self.assertNotIn("()", str(rel_child).replace("(child)","")) # Check no empty parens for description

        # Check repr includes class name and attributes
        self.assertTrue(repr(rel_spouse).startswith("Relationship("))
        self.assertIn("person1_id='p1'", repr(rel_spouse))
        self.assertIn("relationship_type='spouse'", repr(rel_spouse))


if __name__ == "__main__":
    unittest.main()

