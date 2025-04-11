from src.user import User
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship

class UserProfileView:
    def __init__(self, target_user: User, requesting_user:User):
        self.target_user = target_user
        self.requesting_user = requesting_user

    def display_profile(self):
        print("User Profile:")
        self.display_field("Name", self.target_user.email)
        self.display_field("Email", self.target_user.email)
        self.display_field("Role", self.target_user.role)
        self.display_field("Trust Level", self.target_user.get_trust_level())

    def display_field(self, field_name, field_value):
        access_level = self.get_access_level(field_name)
        if access_level:
            print(f"  {field_name}: {field_value}")
        else:
            print(f"  {field_name}: Field is not accessible")

    def get_access_level(self, field):
        privacy_level = self.target_user.get_privacy_setting(field)
        requesting_user_access_level = self.requesting_user.access_level

        if privacy_level == "public":
            return True
        elif privacy_level == "private" and requesting_user_access_level == "admin":
            return True
        elif privacy_level == "family_only":
            # Check if the requesting_user has a relationship of 'parent', 'child', or 'spouse' with the target_user
            return any(rel.relationship_type in ["parent", "child", "spouse"] for rel in self.target_user.relationships)
        elif privacy_level == "godparents_only" and self.requesting_user.user_id in self.target_user.godparents:
            return True
        elif privacy_level == "foster_only" and self.requesting_user.user_id in self.target_user.foster_relationships:
            return True
        elif privacy_level == "guardians_only" and self.requesting_user.user_id in self.target_user.guardian_relationships:
            return True
        return False


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
