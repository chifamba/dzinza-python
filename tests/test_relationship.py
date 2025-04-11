import unittest
from src.relationship import Relationship


class TestRelationship(unittest.TestCase):
    """
    Test suite for the Relationship class.
    """

    def test_valid_relationship_types(self):
        """
        Test that valid relationship types are accepted.
        """
        relationship_parent = Relationship("person1", "person2", "parent")
        self.assertEqual(relationship_parent.relationship_type, "parent")

        relationship_child = Relationship("person1", "person2", "child")
        self.assertEqual(relationship_child.relationship_type, "child")

        relationship_spouse = Relationship("person1", "person2", "spouse")
        self.assertEqual(relationship_spouse.relationship_type, "spouse")

        relationship_sibling = Relationship("person1", "person2", "sibling")
        self.assertEqual(relationship_sibling.relationship_type, "sibling")

        relationship_other = Relationship("person1", "person2", "other")
        self.assertEqual(relationship_other.relationship_type, "other")

    def test_invalid_relationship_type(self):
        """
        Test that an invalid relationship type raises a ValueError.
        """
        with self.assertRaises(ValueError):
            Relationship("person1", "person2", "invalid")

    def test_relationship_attributes(self):
        """
        Test that the relationship attributes are correctly set.
        """
        relationship = Relationship(
            "person1",
            "person2",
            "spouse",
            start_date="2000-01-01",
            end_date="2010-01-01",
            description="Married",
        )
        self.assertEqual(relationship.person1_id, "person1")
        self.assertEqual(relationship.person2_id, "person2")
        self.assertEqual(relationship.relationship_type, "spouse")
        self.assertEqual(relationship.start_date, "2000-01-01")
        self.assertEqual(relationship.end_date, "2010-01-01")
        self.assertEqual(relationship.description, "Married")

    def test_relationship_equality(self):
        """
        Test that two relationships are equal if they have the same attributes.
        """
        relationship1 = Relationship("person1", "person2", "parent")
        relationship2 = Relationship("person1", "person2", "parent")
        self.assertEqual(relationship1, relationship2)

    def test_relationship_inequality(self):
        """
        Test that two relationships are not equal if they have different attributes.
        """
        relationship1 = Relationship("person1", "person2", "parent")
        relationship2 = Relationship("person2", "person1", "child")
        self.assertNotEqual(relationship1, relationship2)

    def test_relationship_hash(self):
        """
        Test that the hash of two equal relationships is the same.
        """
        relationship1 = Relationship("person1", "person2", "parent")
        relationship2 = Relationship("person1", "person2", "parent")
        self.assertEqual(hash(relationship1), hash(relationship2))

    def test_relationship_different_hash(self):
        """
        Test that the hash of two different relationships is different.
        """
        relationship1 = Relationship("person1", "person2", "parent")
        relationship2 = Relationship("person2", "person1", "child")
        self.assertNotEqual(hash(relationship1), hash(relationship2))


if __name__ == "__main__":
    unittest.main()