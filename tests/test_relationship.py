# tests/test_relationship.py

import unittest
from src.relationship import Relationship, get_reciprocal_relationship, VALID_RELATIONSHIP_TYPES

class TestRelationship(unittest.TestCase):
    """Unit tests for the Relationship class and related functions."""

    def test_relationship_creation_minimal(self):
        """Test creating a relationship with minimal required data."""
        rel = Relationship("p1", "p2", "spouse")
        self.assertEqual(rel.person1_id, "p1")
        self.assertEqual(rel.person2_id, "p2")
        self.assertEqual(rel.rel_type, "spouse")
        # Default attributes should be an empty dict due to __post_init__
        self.assertEqual(rel.attributes, {})

    def test_relationship_creation_with_attributes(self):
        """Test creating a relationship with additional attributes."""
        attrs = {"start_date": "2000-01-15", "location": "City Hall"}
        rel = Relationship("p1", "p2", "spouse", attributes=attrs)
        self.assertEqual(rel.person1_id, "p1")
        self.assertEqual(rel.person2_id, "p2")
        self.assertEqual(rel.rel_type, "spouse")
        self.assertIsNotNone(rel.attributes) # Should not be None
        self.assertEqual(rel.attributes["start_date"], "2000-01-15")
        self.assertEqual(rel.attributes["location"], "City Hall")

    def test_relationship_creation_invalid_type(self):
        """Test creating a relationship with an invalid type (optional check)."""
        # This depends on whether Relationship enforces type validity itself
        # or relies on FamilyTree to do so. Assuming Relationship allows any string for now.
        rel = Relationship("p1", "p2", "best_friend") # Assuming 'best_friend' is not in VALID_RELATIONSHIP_TYPES
        self.assertEqual(rel.rel_type, "best_friend")
        # Add assertRaises if Relationship validates type against VALID_RELATIONSHIP_TYPES

    def test_relationship_representation(self):
        """Test the string representation (__repr__) of a relationship."""
        rel = Relationship("p1", "p2", "spouse")
        self.assertEqual(repr(rel), "Relationship: p1 -> p2 (spouse)")

        attrs = {"start_date": "2000-01-15"}
        rel_with_attrs = Relationship("p3", "p4", "child", attributes=attrs)
        # Representation might or might not include attributes, adjust as needed
        self.assertEqual(repr(rel_with_attrs), "Relationship: p3 -> p4 (child)") # Basic repr shown

    def test_relationship_equality(self):
        """Test equality comparison between Relationship objects."""
        rel1 = Relationship("p1", "p2", "spouse")
        rel2 = Relationship("p1", "p2", "spouse")
        rel3 = Relationship("p1", "p2", "parent") # Different type
        rel4 = Relationship("p1", "p3", "spouse") # Different person2
        rel5 = Relationship("p3", "p2", "spouse") # Different person1
        rel6 = Relationship("p1", "p2", "spouse", attributes={"date": "2000"}) # Different attributes
        rel7 = Relationship("p1", "p2", "spouse", attributes={"date": "2000"}) # Same attributes as rel6
        rel8 = Relationship("p1", "p2", "spouse", attributes={}) # Explicit empty attributes

        self.assertEqual(rel1, rel2) # Should be equal (both have default empty dict)
        self.assertEqual(rel1, rel8) # Should be equal to explicit empty dict
        self.assertNotEqual(rel1, rel3)
        self.assertNotEqual(rel1, rel4)
        self.assertNotEqual(rel1, rel5)
        self.assertNotEqual(rel1, rel6) # Equality depends on attributes
        self.assertEqual(rel6, rel7)    # Relationships with same attributes should be equal

        # Test comparison with other types
        self.assertNotEqual(rel1, "p1 -> p2 (spouse)")
        self.assertNotEqual(rel1, None)

    def test_relationship_to_dict(self):
        """Test converting a Relationship object to a dictionary."""
        rel_no_attrs = Relationship("p1", "p2", "spouse")
        # Expect attributes to be an empty dict, not None
        expected_dict_no_attrs = {
            "person1_id": "p1",
            "person2_id": "p2",
            "rel_type": "spouse",
            "attributes": {}
        }
        self.assertEqual(rel_no_attrs.to_dict(), expected_dict_no_attrs)

        attrs = {"start_date": "2000-01-15", "notes": "Met online"}
        rel_with_attrs = Relationship("p3", "p4", "sibling", attributes=attrs)
        expected_dict_with_attrs = {
            "person1_id": "p3",
            "person2_id": "p4",
            "rel_type": "sibling",
            "attributes": attrs # Should include the attributes dictionary
        }
        self.assertEqual(rel_with_attrs.to_dict(), expected_dict_with_attrs)

    def test_relationship_from_dict(self):
        """Test creating a Relationship object from a dictionary."""
        rel_data_no_attrs = {
            "person1_id": "p1",
            "person2_id": "p2",
            "rel_type": "spouse",
            # "attributes": None # Optional, from_dict should handle missing key
        }
        rel1 = Relationship.from_dict(rel_data_no_attrs)
        self.assertIsInstance(rel1, Relationship)
        self.assertEqual(rel1.person1_id, "p1")
        self.assertEqual(rel1.person2_id, "p2")
        self.assertEqual(rel1.rel_type, "spouse")
        # Attributes should default to empty dict
        self.assertEqual(rel1.attributes, {})

        rel_data_with_attrs = {
            "person1_id": "p3",
            "person2_id": "p4",
            "rel_type": "sibling",
            "attributes": {"shared_secret": "xyz"}
        }
        rel2 = Relationship.from_dict(rel_data_with_attrs)
        self.assertIsInstance(rel2, Relationship)
        self.assertEqual(rel2.person1_id, "p3")
        self.assertEqual(rel2.person2_id, "p4")
        self.assertEqual(rel2.rel_type, "sibling")
        self.assertIsNotNone(rel2.attributes) # Check it's not None
        self.assertEqual(rel2.attributes["shared_secret"], "xyz")

        # Test creating with explicit null/empty attributes
        rel_data_null_attrs = {
             "person1_id": "p5", "person2_id": "p6", "rel_type": "friend", "attributes": None
        }
        rel3 = Relationship.from_dict(rel_data_null_attrs)
        self.assertEqual(rel3.attributes, {}) # Should be initialized to {}

        rel_data_empty_attrs = {
             "person1_id": "p7", "person2_id": "p8", "rel_type": "cousin", "attributes": {}
        }
        rel4 = Relationship.from_dict(rel_data_empty_attrs)
        self.assertEqual(rel4.attributes, {}) # Should remain {}


    def test_relationship_from_dict_missing_keys(self):
        """Test creating from dict with missing required keys."""
        with self.assertRaises(KeyError):
            Relationship.from_dict({"person1_id": "p1", "person2_id": "p2"}) # Missing rel_type
        with self.assertRaises(KeyError):
            Relationship.from_dict({"person1_id": "p1", "rel_type": "spouse"}) # Missing person2_id
        with self.assertRaises(KeyError):
            Relationship.from_dict({"person2_id": "p2", "rel_type": "spouse"}) # Missing person1_id

    # --- Test get_reciprocal_relationship ---

    def test_get_reciprocal_spouse(self):
        """Test reciprocal of 'spouse'."""
        self.assertEqual(get_reciprocal_relationship("spouse"), "spouse")

    def test_get_reciprocal_parent_child(self):
        """Test reciprocal of 'parent' and 'child'."""
        self.assertEqual(get_reciprocal_relationship("parent"), "child")
        self.assertEqual(get_reciprocal_relationship("child"), "parent")

    def test_get_reciprocal_sibling(self):
        """Test reciprocal of 'sibling'."""
        self.assertEqual(get_reciprocal_relationship("sibling"), "sibling")

    def test_get_reciprocal_custom(self):
        """Test reciprocal of a custom or undefined type."""
        # Use the exact key from the map: "adopted child" (with space)
        self.assertEqual(get_reciprocal_relationship("adopted child"), "adoptive parent")
        # Test value lookup
        self.assertEqual(get_reciprocal_relationship("adoptive parent"), "adopted child")
        # Test undefined type
        self.assertEqual(get_reciprocal_relationship("friend"), "friend")
        self.assertEqual(get_reciprocal_relationship("unknown_type"), "unknown_type")

    def test_get_reciprocal_case_insensitivity(self):
        """Test if reciprocal function handles different cases."""
        self.assertEqual(get_reciprocal_relationship("Parent"), "child")
        self.assertEqual(get_reciprocal_relationship("CHILD"), "parent")
        self.assertEqual(get_reciprocal_relationship("SpOuSe"), "spouse")

    # --- Test Syntax Fix ---
    def test_dictionary_syntax(self):
        """Test that dictionary literals have correct syntax."""
        # This test doesn't run anything specific, but its presence ensures
        # the file parses correctly if the syntax error is fixed.
        rel_data_minimal = {
            "person1_id": "p1",
            "person2_id": "p2",
            "rel_type": "spouse"
        } # Added closing brace
        self.assertIsNotNone(rel_data_minimal) # Simple assertion using the fixed dict

if __name__ == '__main__':
    unittest.main()
