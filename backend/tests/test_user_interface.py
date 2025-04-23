# tests/test_user_interface.py
import unittest
from unittest.mock import MagicMock, patch, call # Import call for checking print args
from io import StringIO # To capture print output

# Import refactored classes
from src.user_interface import UserProfileView, FamilyGroupView, PersonDetailView, RelationshipView
from src.user import User
from src.person import Person
from src.family_tree import FamilyTree
from src.relationship import Relationship

class TestUserProfileView(unittest.TestCase):
    """Test suite for the refactored UserProfileView."""

    def setUp(self):
        self.target_user = User("target1", "target@example.com", "hash1", role="trusted")
        self.target_user.add_trust_points(150) # Trust level 2
        self.requesting_user_self = self.target_user # Viewing own profile
        self.requesting_user_other = User("other1", "other@example.com", "hash2")
        self.requesting_user_admin = User("admin1", "admin@example.com", "hash3", role="administrator")

    @patch('sys.stdout', new_callable=StringIO) # Capture print output
    def test_display_profile_self(self, mock_stdout):
        """Test displaying own profile (should show most fields)."""
        view = UserProfileView(self.target_user, self.requesting_user_self)
        view.display_profile()
        output = mock_stdout.getvalue()
        self.assertIn("User ID: target1", output)
        self.assertIn("Email: target@example.com", output)
        self.assertIn("Role: trusted", output)
        self.assertIn("Trust Points: 150", output)
        self.assertIn("Trust Level: 2", output) # Check calculated level

    @patch('sys.stdout', new_callable=StringIO)
    def test_display_profile_other_user(self, mock_stdout):
        """Test displaying another user's profile (limited view)."""
        view = UserProfileView(self.target_user, self.requesting_user_other)
        view.display_profile()
        output = mock_stdout.getvalue()
        # Assuming default restricted view for basic users
        self.assertIn("User ID: target1", output)
        self.assertIn("Role: trusted", output)
        # Should NOT show sensitive info by default
        self.assertNotIn("Email:", output)
        self.assertNotIn("Trust Points:", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_display_profile_admin_view(self, mock_stdout):
        """Test displaying profile as admin (should show most fields)."""
        view = UserProfileView(self.target_user, self.requesting_user_admin)
        view.display_profile()
        output = mock_stdout.getvalue()
        self.assertIn("User ID: target1", output)
        self.assertIn("Email: target@example.com", output) # Admin can see email
        self.assertIn("Role: trusted", output)
        self.assertIn("Trust Points: 150", output) # Admin can see points


class TestFamilyGroupView(unittest.TestCase):
    """Test suite for the refactored FamilyGroupView."""

    def setUp(self):
        self.family_tree = FamilyTree() # Use real FamilyTree
        self.p1 = Person("user", "Alice", "A", person_id="p1", date_of_birth="1980-01-01")
        self.p2 = Person("user", "Bob", "B", person_id="p2", date_of_birth="1982-02-02")
        self.p3 = Person("user", "Charlie", "C", person_id="p3", date_of_birth="2005-03-03")
        self.family_tree.add_person(self.p1)
        self.family_tree.add_person(self.p2)
        self.family_tree.add_person(self.p3)
        # Link p1 and p2 as spouses
        self.rel_spouse = Relationship(self.p1.person_id, self.p2.person_id, "spouse")
        self.family_tree.link_persons(self.rel_spouse)
        # Link p3 as child of p1
        self.rel_child = Relationship(self.p3.person_id, self.p1.person_id, "child")
        self.rel_parent = Relationship(self.p1.person_id, self.p3.person_id, "parent")
        self.family_tree.link_persons(self.rel_child)
        self.family_tree.link_persons(self.rel_parent)

        self.view = FamilyGroupView(self.family_tree)

    @patch('sys.stdout', new_callable=StringIO)
    def test_display_family_group(self, mock_stdout):
        """Test displaying a valid family group."""
        group_ids = [self.p1.person_id, self.p2.person_id, self.p3.person_id]
        self.view.display_family_group(group_ids)
        output = mock_stdout.getvalue()

        # Check persons are listed
        self.assertIn("Alice A", output)
        self.assertIn("Bob B", output)
        self.assertIn("Charlie C", output)
        # Check relationships within the group are listed
        self.assertIn("Relationships within Group:", output)
        self.assertIn(f"{self.rel_spouse}", output) # Check spouse relationship string
        self.assertIn(f"{self.rel_child}", output) # Check child relationship string (p3 -> p1)
        # Parent relationship (p1 -> p3) might also be printed depending on iteration order
        self.assertIn(f"{self.rel_parent}", output)


    @patch('sys.stdout', new_callable=StringIO)
    def test_display_family_group_no_relationships(self, mock_stdout):
        """Test displaying group with no relationships between members."""
        p4 = Person("user", "Diana", "D", person_id="p4")
        self.family_tree.add_person(p4)
        group_ids = [self.p1.person_id, p4.person_id] # No direct link
        self.view.display_family_group(group_ids)
        output = mock_stdout.getvalue()
        self.assertIn("Alice A", output)
        self.assertIn("Diana D", output)
        self.assertIn("(No relationships found exclusively within this group)", output)


    def test_display_family_group_invalid_person_id(self):
        """Test displaying group with an invalid person ID raises ValueError."""
        group_ids = [self.p1.person_id, "invalid_id"]
        with self.assertRaisesRegex(ValueError, "Person with ID invalid_id not found"):
            self.view.display_family_group(group_ids)


class TestPersonDetailView(unittest.TestCase):
    """Test suite for the refactored PersonDetailView."""

    def setUp(self):
        self.person = Person("user", "Detailed", "Person", person_id="pd1", date_of_birth="1999-12-31")
        self.person.biography = "Test bio."
        self.person.add_document("doc1.pdf")
        self.view = PersonDetailView(self.person)

    @patch('sys.stdout', new_callable=StringIO)
    def test_display_person_details(self, mock_stdout):
        """Test displaying person details."""
        self.view.display_person_details()
        output = mock_stdout.getvalue()

        self.assertIn("Person Details: Detailed Person", output)
        self.assertIn("Person Id: pd1", output) # Check formatted key
        self.assertIn("Creator User Id: user", output)
        self.assertIn("Date Of Birth: 1999-12-31T00:00:00", output) # ISO format from get_person_info
        self.assertIn("Biography: Test bio.", output)
        self.assertIn("Documents: doc1.pdf", output)
        self.assertIn("Relationships:", output) # Should show relationships section
        self.assertIn("(None recorded)", output) # No relationships added in setUp


class TestRelationshipView(unittest.TestCase):
    """Test suite for the refactored RelationshipView."""

    def setUp(self):
        self.family_tree = FamilyTree() # Need tree to resolve names
        self.p1 = Person("user", "Rel", "One", person_id="r1")
        self.p2 = Person("user", "Rel", "Two", person_id="r2")
        self.family_tree.add_person(self.p1)
        self.family_tree.add_person(self.p2)

        self.relationship = Relationship(self.p1.person_id, self.p2.person_id, "friend", description="Close friends")
        self.view = RelationshipView(self.relationship, self.family_tree) # Pass tree

    @patch('sys.stdout', new_callable=StringIO)
    def test_display_relationship(self, mock_stdout):
        """Test displaying relationship details."""
        self.view.display_relationship()
        output = mock_stdout.getvalue()

        self.assertIn("Relationship Details", output)
        self.assertIn(f"Person 1: Rel One ({self.p1.person_id[:6]}...)", output) # Check name lookup
        self.assertIn(f"Person 2: Rel Two ({self.p2.person_id[:6]}...)", output)
        self.assertIn("Type: Friend", output) # Check formatted type
        self.assertIn("Duration: Unknown - Present", output) # Default dates
        self.assertIn("Description: Close friends", output)


if __name__ == '__main__':
    unittest.main()
