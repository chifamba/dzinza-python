# tests/test_person.py
import unittest
import uuid
from datetime import datetime
from unittest.mock import MagicMock # Used for mocking FamilyTree if needed

# Corrected Imports: Use absolute path from project root perspective
try:
    from backend.src.person import Person
    from backend.src.relationship import Relationship
    # from backend.src.family_tree import FamilyTree # Avoid direct import if mocking
except ImportError as e:
    print(f"Error importing test dependencies: {e}")
    # Define dummy classes if needed for tests to run structurally
    class Person: pass
    class Relationship: pass

class TestPerson(unittest.TestCase):
    """Test suite for the refactored Person class."""

    def setUp(self):
        """Set up a Person object for testing."""
        self.creator_user_id = "user_test_123"
        self.person = Person(
            creator_user_id=self.creator_user_id,
            first_name="Test",
            last_name="Person",
            date_of_birth="1990-01-01",
            place_of_birth="Test Place",
            gender="M"
        )
        # Mock the family tree if needed for relationship tests (like get_siblings)
        self.mock_family_tree = MagicMock()
        self.person.family_tree = self.mock_family_tree


    def test_person_initialization(self):
        """Test basic attributes after initialization."""
        self.assertIsInstance(self.person.person_id, str)
        self.assertEqual(self.person.creator_user_id, self.creator_user_id)
        self.assertEqual(len(self.person.names), 2)
        self.assertEqual(self.person.get_full_name(), "Test Person")
        self.assertEqual(self.person.gender, "M")
        self.assertIsInstance(self.person.date_of_birth, datetime)
        self.assertEqual(self.person.date_of_birth.year, 1990)
        self.assertEqual(self.person.place_of_birth, "Test Place")
        self.assertIsNone(self.person.date_of_death)
        self.assertEqual(self.person.relationships, []) # Relationships list starts empty

    def test_add_remove_get_names(self):
        """Test adding, removing, and getting names."""
        self.person.add_name(name="Middle", type="middle", culture="default")
        self.assertEqual(len(self.person.names), 3)
        self.assertEqual(len(self.person.get_names(name_type="middle")), 1)

        # Test adding duplicate (should be ignored with warning, not raise error based on refactored code)
        # self.person.add_name(name="Test", type="first", culture="default") # No error expected
        # self.assertEqual(len(self.person.names), 3) # Length shouldn't change

        self.person.remove_name(name="Middle", type="middle", culture="default")
        self.assertEqual(len(self.person.names), 2)

        with self.assertRaises(ValueError):
            self.person.remove_name(name="Nonexistent", type="first", culture="test")

        self.assertEqual(len(self.person.get_names(culture="default")), 2)

    def test_add_remove_get_religious_affiliation(self):
        """Test religious affiliation management."""
        self.person.add_religious_affiliation("Test Religion")
        self.assertEqual(self.person.get_religious_affiliations(), ["Test Religion"])
        with self.assertRaises(ValueError): # Should raise error on duplicate add
            self.person.add_religious_affiliation("Test Religion")

        self.person.remove_religious_affiliation("Test Religion")
        self.assertEqual(self.person.get_religious_affiliations(), [])
        with self.assertRaises(ValueError):
            self.person.remove_religious_affiliation("Nonexistent Religion")

    def test_add_remove_relationship(self):
        """Test adding and removing relationships from the person's list."""
        person2_id = str(uuid.uuid4())
        rel = Relationship(self.person.person_id, person2_id, "spouse")
        self.person.add_relationship(rel)
        self.assertIn(rel, self.person.relationships)
        self.assertEqual(len(self.person.relationships), 1)

        # Adding same relationship again should not change the list
        self.person.add_relationship(rel)
        self.assertEqual(len(self.person.relationships), 1)

        # Test removing
        self.person.remove_relationship(rel)
        self.assertEqual(len(self.person.relationships), 0)

        # Test removing non-existent relationship
        with self.assertRaises(ValueError):
            self.person.remove_relationship(rel)

        # Test adding relationship not involving this person
        rel_invalid = Relationship("other_id_1", "other_id_2", "friend")
        with self.assertRaises(ValueError):
             self.person.add_relationship(rel_invalid)


    def test_get_related_person_ids_by_type(self):
        """Test getting related person IDs based on relationship type."""
        p_spouse_id = str(uuid.uuid4())
        p_child_id = str(uuid.uuid4()) # This person is parent of p_child_id
        p_parent_id = str(uuid.uuid4()) # This person is child of p_parent_id

        rel_spouse = Relationship(self.person.person_id, p_spouse_id, "spouse")
        rel_parent = Relationship(self.person.person_id, p_child_id, "parent") # Person is P1 (parent)
        rel_child = Relationship(self.person.person_id, p_parent_id, "child") # Person is P1 (child)

        self.person.add_relationship(rel_spouse)
        self.person.add_relationship(rel_parent)
        self.person.add_relationship(rel_child)

        # Test spouse (symmetric)
        self.assertCountEqual(self.person.get_related_person_ids("spouse"), [p_spouse_id])

        # Test parent (asymmetric, Person is P1) - should return P2 (child)
        self.assertCountEqual(self.person.get_related_person_ids("parent"), [p_child_id])

        # Test child (asymmetric, Person is P1) - should return P2 (parent)
        self.assertCountEqual(self.person.get_related_person_ids("child"), [p_parent_id])


    def test_get_parents_children_spouses(self):
        """Test getting specific relationship types (parents, children, spouses)."""
        p_spouse_id = str(uuid.uuid4())
        p_child_id = str(uuid.uuid4())
        p_parent_id = str(uuid.uuid4())

        # Person is spouse of p_spouse_id
        rel_spouse = Relationship(self.person.person_id, p_spouse_id, "spouse")
        # Person is child of p_parent_id (Person is P1)
        rel_child = Relationship(self.person.person_id, p_parent_id, "child")
        # Person is parent of p_child_id (Person is P1)
        rel_parent = Relationship(self.person.person_id, p_child_id, "parent")

        self.person.add_relationship(rel_spouse)
        self.person.add_relationship(rel_child)
        self.person.add_relationship(rel_parent)

        self.assertEqual(self.person.get_spouses(), [p_spouse_id])
        self.assertEqual(self.person.get_parents(), [p_parent_id]) # Found via 'child' relationship
        self.assertEqual(self.person.get_children(), [p_child_id]) # Found via 'parent' relationship

    def test_get_siblings(self):
        """Test getting siblings (requires mocking family tree)."""
        p_parent1_id = "parent1"
        p_parent2_id = "parent2"
        p_sibling1_id = "sibling1" # Full sibling
        p_sibling2_id = "sibling2" # Half sibling (shares parent1)
        p_unrelated_child_id = "unrelated_child" # Child of parent1 only

        # Setup relationships for self (child of parent1 and parent2)
        rel_self_parent1 = Relationship(self.person.person_id, p_parent1_id, "child")
        rel_self_parent2 = Relationship(self.person.person_id, p_parent2_id, "child")
        self.person.add_relationship(rel_self_parent1)
        self.person.add_relationship(rel_self_parent2)

        # Setup mock persons and their relationships
        mock_parent1 = Person("user", "Parent", "One", person_id=p_parent1_id)
        mock_parent2 = Person("user", "Parent", "Two", person_id=p_parent2_id)
        mock_sibling1 = Person("user", "Sibling", "One", person_id=p_sibling1_id)
        mock_sibling2 = Person("user", "Sibling", "Two", person_id=p_sibling2_id)
        mock_unrelated_child = Person("user", "Unrelated", "Child", person_id=p_unrelated_child_id)

        # Sibling 1 relationships (child of parent1 and parent2)
        mock_sibling1.add_relationship(Relationship(p_sibling1_id, p_parent1_id, "child"))
        mock_sibling1.add_relationship(Relationship(p_sibling1_id, p_parent2_id, "child"))
        # Sibling 2 relationships (child of parent1 only)
        mock_sibling2.add_relationship(Relationship(p_sibling2_id, p_parent1_id, "child"))
        # Unrelated child relationships (child of parent1 only) - Should be identified as sibling
        mock_unrelated_child.add_relationship(Relationship(p_unrelated_child_id, p_parent1_id, "child"))

        # Parent relationships (needed for parent's get_children call)
        # Parent 1 is parent of self, sibling1, sibling2, unrelated_child
        mock_parent1.add_relationship(Relationship(p_parent1_id, self.person.person_id, "parent"))
        mock_parent1.add_relationship(Relationship(p_parent1_id, p_sibling1_id, "parent"))
        mock_parent1.add_relationship(Relationship(p_parent1_id, p_sibling2_id, "parent"))
        mock_parent1.add_relationship(Relationship(p_parent1_id, p_unrelated_child_id, "parent"))
        # Parent 2 is parent of self, sibling1
        mock_parent2.add_relationship(Relationship(p_parent2_id, self.person.person_id, "parent"))
        mock_parent2.add_relationship(Relationship(p_parent2_id, p_sibling1_id, "parent"))

        # Configure mock family tree lookup
        def mock_get_person(person_id):
            if person_id == p_parent1_id: return mock_parent1
            if person_id == p_parent2_id: return mock_parent2
            # No need to return siblings/children, only parents are looked up by get_siblings
            return None
        self.mock_family_tree.get_person_by_id.side_effect = mock_get_person

        # Assign family tree to mock parents too for get_children call within get_siblings
        mock_parent1.family_tree = self.mock_family_tree
        mock_parent2.family_tree = self.mock_family_tree

        # Get siblings for the test person
        siblings = self.person.get_siblings()

        # Expected siblings are those who share at least one parent (p1 or p2)
        # self -> p1, p2
        # sibling1 -> p1, p2 (shares p1 and p2 -> full sibling)
        # sibling2 -> p1 (shares p1 -> half sibling)
        # unrelated_child -> p1 (shares p1 -> half sibling)
        expected_siblings = [p_sibling1_id, p_sibling2_id, p_unrelated_child_id]
        self.assertCountEqual(siblings, expected_siblings) # Use assertCountEqual for lists where order doesn't matter


    def test_privacy_settings(self):
        """Test setting and getting privacy settings."""
        self.person.set_privacy_setting("date_of_birth", "private")
        self.person.set_privacy_setting("place_of_birth", "family_only")

        self.assertEqual(self.person.get_privacy_setting("date_of_birth"), "private")
        self.assertEqual(self.person.get_privacy_setting("place_of_birth"), "family_only")
        self.assertEqual(self.person.get_privacy_setting("non_existent_field"), "private") # Test default

        with self.assertRaises(ValueError):
            self.person.set_privacy_setting("gender", "invalid_level")

    def test_add_remove_get_documents(self):
        """Test document management."""
        doc1 = "http://example.com/doc1.pdf"
        doc2 = "/local/path/doc2.txt"
        self.person.add_document(doc1)
        self.person.add_document(doc2)
        self.assertCountEqual(self.person.get_documents(), [doc1, doc2])

        # Adding duplicate should not change list
        self.person.add_document(doc1)
        self.assertEqual(len(self.person.get_documents()), 2)

        self.person.remove_document(doc1)
        self.assertEqual(self.person.get_documents(), [doc2])
        with self.assertRaises(ValueError):
            self.person.remove_document("non_existent_doc")

    def test_add_remove_get_godparents(self):
        """Test godparent ID list management."""
        gp1_id = "godparent_1"
        gp2_id = "godparent_2"
        self.person.add_godparent(gp1_id)
        self.person.add_godparent(gp2_id)
        self.assertCountEqual(self.person.get_godparents(), [gp1_id, gp2_id])

        with self.assertRaises(ValueError): # Duplicate add
            self.person.add_godparent(gp1_id)

        self.person.remove_godparent(gp1_id)
        self.assertEqual(self.person.get_godparents(), [gp2_id])
        with self.assertRaises(ValueError): # Remove non-existent
            self.person.remove_godparent("non_existent_gp")

    def test_add_remove_get_cultural_relationships(self):
        """Test cultural relationship dictionary management."""
        rel_type = "clan_member"
        p1_id = "person_clan_1"
        p2_id = "person_clan_2"
        self.person.add_cultural_relationship(rel_type, p1_id)
        self.person.add_cultural_relationship(rel_type, p2_id)
        self.assertCountEqual(self.person.get_cultural_relationships()[rel_type], [p1_id, p2_id])

        with self.assertRaises(ValueError): # Duplicate add
            self.person.add_cultural_relationship(rel_type, p1_id)

        self.person.remove_cultural_relationship(rel_type, p1_id)
        self.assertEqual(self.person.get_cultural_relationships()[rel_type], [p2_id])

        # Remove last person for the type, should remove the key
        self.person.remove_cultural_relationship(rel_type, p2_id)
        self.assertNotIn(rel_type, self.person.get_cultural_relationships())

        with self.assertRaises(ValueError): # Remove non-existent person
             self.person.remove_cultural_relationship(rel_type, p1_id)
        with self.assertRaises(ValueError): # Remove non-existent type
             self.person.remove_cultural_relationship("non_existent_type", p1_id)


    def test_get_person_info(self):
        """Test the dictionary representation of the person."""
        self.person.add_name("Middle", "middle", "default")
        self.person.biography = "A test biography."
        self.person.add_document("doc1")
        rel = Relationship(self.person.person_id, "p2", "spouse")
        self.person.add_relationship(rel)

        info = self.person.get_person_info()

        self.assertEqual(info["person_id"], self.person.person_id)
        self.assertEqual(info["creator_user_id"], self.creator_user_id)
        self.assertEqual(len(info["names"]), 3)
        self.assertEqual(info["gender"], "M")
        self.assertEqual(info["date_of_birth"], "1990-01-01T00:00:00") # ISO format
        self.assertEqual(info["biography"], "A test biography.") # Assumes no encryption for test
        self.assertEqual(info["documents"], ["doc1"])
        # Relationships are not included directly in get_person_info in refactored version
        self.assertNotIn("relationships", info)

    def test_string_representation(self):
        """Test __str__ and __repr__ methods."""
        dob_str = self.person.date_of_birth.strftime('%Y-%m-%d')
        self.assertTrue(self.person.person_id in str(self.person))
        self.assertTrue("Test Person" in str(self.person))
        self.assertTrue(dob_str in str(self.person))

        self.assertTrue(self.person.person_id in repr(self.person))
        self.assertTrue("Test Person" in repr(self.person))

    def test_equality_and_hash(self):
        """Test equality and hashing based on person_id."""
        person_copy = Person(
            creator_user_id=self.creator_user_id,
            first_name="Test",
            last_name="Person",
            person_id=self.person.person_id # Same ID
        )
        person_different_id = Person(
            creator_user_id=self.creator_user_id,
            first_name="Test",
            last_name="Person"
            # Different ID (auto-generated)
        )
        person_different_name = Person(
            creator_user_id=self.creator_user_id,
            first_name="Different",
            last_name="Name",
            person_id=self.person.person_id # Same ID
        )

        self.assertEqual(self.person, person_copy)
        self.assertEqual(hash(self.person), hash(person_copy))

        self.assertNotEqual(self.person, person_different_id)
        self.assertNotEqual(hash(self.person), hash(person_different_id))

        # Equality only depends on ID, not other attributes
        self.assertEqual(self.person, person_different_name)
        self.assertEqual(hash(self.person), hash(person_different_name))

        self.assertNotEqual(self.person, "not a person")


if __name__ == "__main__":
    unittest.main()
