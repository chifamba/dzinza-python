from src.user import User
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship

class UserProfileView:
    def __init__(self, user: User):
        self.user = user

    def display_profile(self):
        print("User Profile:")
        print(f"  Name: {self.user.email}")
        print(f"  Email: {self.user.email}")
        print(f"  Role: {self.user.role}")
        print(f"  Trust Level: {self.user.get_trust_level()}")


class FamilyGroupView:
    def __init__(self, family_tree: FamilyTree):
        self.family_tree = family_tree

    def display_family_group(self, person_ids):
        print("Family Group:")
        for person_id in person_ids:
            person = self.family_tree.get_person_by_id(person_id)
            if person is None:
                raise ValueError(f"Person with ID {person_id} not found in the family tree")
            print(f"  ID: {person.user_id}, Name: {person.get_names()}")

        print("\nRelationships:")
        for person_id in person_ids:
            person = self.family_tree.get_person_by_id(person_id)
            print(f"  {person.user_id}: {person.relationships}")

class PersonDetailView:
    def __init__(self, person: Person):
        self.person = person
    
    def display_person_details(self):
        print("Person Details:")
        person_info = self.person.get_person_info()
        for key, value in person_info.items():
            print(f"  {key}: {value}")

class RelationshipView:
    def __init__(self, relationship: Relationship):
        self.relationship = relationship

    def display_relationship(self):
        print("Relationship Details:")
        print(f"  Person 1 ID: {self.relationship.person1_id}")
        print(f"  Person 2 ID: {self.relationship.person2_id}")
        print(f"  Relationship Type: {self.relationship.relationship_type}")
        print(f"  Start Date: {self.relationship.start_date}, End Date: {self.relationship.end_date}, Description: {self.relationship.description}")
