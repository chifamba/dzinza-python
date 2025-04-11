import unittest
from unittest.mock import MagicMock
from src.user_interface import UserProfileView, FamilyGroupView, PersonDetailView, RelationshipView
from src.user_management import User, UserManager
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship

class TestUserProfileView(unittest.TestCase):

    def setUp(self):
        # Create a user for testing
        self.user_manager = UserManager()
        self.user = self.user_manager.create_user("testuser", "test@example.com", "password")
        self.user_profile_view = UserProfileView(self.user,self.user)

    def test_display_profile(self):
        # Mock the print function to capture the output
        with unittest.mock.patch('builtins.print') as mock_print:
            self.user_profile_view.display_profile()
        # Check that the output is correct
        mock_print.assert_called()

class TestFamilyGroupView(unittest.TestCase):

    def setUp(self):
        # Create a FamilyTree and add some persons for testing
        self.family_tree = FamilyTree()
        self.person1 = Person("person1", "Name1", "LastName1", "1900-01-01", "Place1", "Place1")
        self.person2 = Person("person2", "Name2", "LastName2", "1975-05-10", "Place2", "Place2")
        self.family_tree.add_person(self.person1)
        self.person3 = Person("person3", "Name3", "LastName3", "1995-01-01", "Place3", "Place3")
        self.family_tree.add_person(self.person3)

        #create the relationships
        relationship1 = Relationship(self.person1.person_id, self.person2.person_id, "spouse")
        relationship2 = Relationship(self.person3.person_id, self.person1.person_id, "child")
        self.family_tree.link_persons(relationship1)
        self.family_tree.link_persons(relationship2)


        self.family_group_view = FamilyGroupView(self.family_tree)

    def test_display_family_group(self):
        # Mock the print function to capture the output
        with unittest.mock.patch('builtins.print') as mock_print:
            self.family_group_view.display_family_group([self.person1.person_id, self.person2.person_id, self.person3.person_id])
        # Check that the output is correct
        mock_print.assert_called()

    def test_display_family_group_invalid_person(self):
        # Test if a ValueError is raised when an invalid person ID is provided
        with self.assertRaises(ValueError):
            self.family_group_view.display_family_group(["invalid_person_id"])

class TestPersonDetailView(unittest.TestCase):

    def setUp(self):
        # Create a Person for testing
        self.person = Person("person1", "Name1", "LastName1", "1970-01-01", "Place1", "Place1")
        self.person_detail_view = PersonDetailView(self.person)

    def test_display_person_details(self):
        # Mock the print function to capture the output
        with unittest.mock.patch('builtins.print') as mock_print:
            self.person_detail_view.display_person_details()
        # Check that the output is correct
        mock_print.assert_called()


class TestRelationshipView(unittest.TestCase):

    def setUp(self):
        # Create a Relationship for testing
        self.person1 = Person("person1", "Name1", "LastName1", "1970-01-01", "Place1", "Place1")
        self.person2 = Person("person2", "Name2", "LastName2", "1975-05-10", "Place2", "Place2")
        self.relationship = Relationship(self.person1.person_id, self.person2.person_id, "spouse")
        self.relationship_view = RelationshipView(self.relationship)

    def test_display_relationship(self):
        # Mock the print function to capture the output
        with unittest.mock.patch('builtins.print') as mock_print:
            self.relationship_view.display_relationship()
        # Check that the output is correct
        mock_print.assert_called()

if __name__ == '__main__':
    unittest.main()