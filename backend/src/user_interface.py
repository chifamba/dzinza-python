# src/user_interface.py
import logging

from typing import List, Optional

# Import necessary classes (use forward references if needed in a real app structure)
from src.user import User
from src.person import Person
from src.family_tree import FamilyTree
from src.relationship import Relationship

class UserProfileView:
    """Displays user profile information, considering privacy."""
    def __init__(self, target_user: User, requesting_user: User):
        """
        Args:
            target_user (User): The user whose profile is being viewed.
            requesting_user (User): The user making the request (for permission checks).
        """
        self.target_user = target_user
        self.requesting_user = requesting_user

    def _can_view_field(self, field_name: str) -> bool:
        """Checks if the requesting user has permission to view a field."""
        # Basic permission logic (can be expanded significantly)
        if self.requesting_user.user_id == self.target_user.user_id:
            return True # User can always view their own profile
        if self.requesting_user.role == 'administrator':
            return True # Admins can view everything

        # Add more complex rules based on roles, relationships, privacy settings
        # Example: Check target_user's privacy settings for the field
        # privacy_level = self.target_user.get_privacy_setting(field_name) # Needs implementation in User
        # if privacy_level == 'public': return True
        # if privacy_level == 'private': return False # Only self/admin
        # ... other levels ...

        # Default to restricted view for others
        return field_name in ["user_id", "role"] # Only allow viewing ID and role by default


    def display_profile(self):
        """Prints the user's profile details to the console."""
        logging.info(f"\n--- User Profile: {self.target_user.user_id} ---")
        # Display fields based on permissions
        if self._can_view_field("user_id"):
            logging.info(f"  User ID: {self.target_user.user_id}")
        if self._can_view_field("email"):
            logging.info(f"  Email: {self.target_user.email}")
        if self._can_view_field("role"):
            logging.info(f"  Role: {self.target_user.role}")
        if self._can_view_field("trust_points"):
             logging.info(f"  Trust Points: {self.target_user.trust_points}")
             logging.info(f"  Trust Level: {self.target_user.get_trust_level()}") # Display calculated level
        if self._can_view_field("last_login"):
             logging.info(f"  Last Login: {self.target_user.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.target_user.last_login else 'Never'}")
        if self._can_view_field("created_at"):
             logging.info(f"  Member Since: {self.target_user.created_at.strftime('%Y-%m-%d') if self.target_user.created_at else 'Unknown'}")
        if self._can_view_field("family_group_spaces"):
             groups = ', '.join(self.target_user.family_group_spaces) if self.target_user.family_group_spaces else "None"
             logging.info(f"  Family Groups: {groups}")

        logging.info("------------------------------------")


class FamilyGroupView:
    """Displays information about a group of related persons."""
    def __init__(self, family_tree: FamilyTree):
        """
        Args:
            family_tree (FamilyTree): The family tree containing the persons.
        """
        self.family_tree = family_tree

    def display_family_group(self, person_ids: List[str]):
        """
        Prints details for a list of persons and their direct relationships within the group.

        Args:
            person_ids (List[str]): The IDs of the persons in the group.

        Raises:
            ValueError: If any person ID in the list is not found in the tree.
        """
        logging.info("\n--- Family Group View ---")
        persons_in_group: List[Person] = []
        group_id_set = set(person_ids) # For quick lookups

        # Fetch and validate all persons first
        for person_id in person_ids:
            person = self.family_tree.get_person_by_id(person_id)
            if person is None:
                logging.error(f"Person with ID {person_id} not found in the family tree.")
                raise ValueError(f"Person with ID {person_id} not found in the family tree.")            
            persons_in_group.append(person)

        if not persons_in_group:
            logging.info("No valid persons found for this group.")
            return

        logging.info("Persons in Group:")
        for person in persons_in_group:
            dob = person.date_of_birth.strftime('%Y-%m-%d') if person.date_of_birth else "?"
            logging.info(f"  - {person.get_full_name()} (ID: {person.person_id[:6]}..., DOB: {dob})")

        logging.info("\nRelationships within Group:")
        displayed_rels = set() # Avoid printing relationships twice
        for person in persons_in_group:
            for rel in person.relationships:
                 rel_hash = hash(rel)
                 # Check if the other person is also in the group and relationship not already printed
                 other_person_id = rel.get_other_person(person.person_id)
                 if other_person_id in group_id_set and rel_hash not in displayed_rels:    
                    logging.info(f"  - {rel}") # Use Relationship's __str__ method
                    displayed_rels.add(rel_hash)

        if not displayed_rels:
            logging.info("  (No relationships found exclusively within this group)")

        logging.info("--------------------------")


class PersonDetailView:
    """Displays detailed information for a single person."""
    def __init__(self, person: Person):
        """
        Args:
            person (Person): The person whose details are to be displayed.
        """
        self.person = person

    def display_person_details(self):
        """Prints the person's details to the console."""
        logging.info(f"\n--- Person Details: {self.person.get_full_name()} (ID: {self.person.person_id}) ---")
        # Use the get_person_info method which handles formatting and decryption placeholders
        person_info = self.person.get_person_info()
        for key, value in person_info.items():
            # Skip empty/null values for cleaner output
            if value is None or (isinstance(value, (list, dict)) and not value):
                continue

            # Format nicely
            key_title = key.replace('_', ' ').title()
            value_str = ""
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                 # List of dictionaries (like names)
                 value_str = "\n" + "\n".join(f"    - {item}" for item in value)
            elif isinstance(value, list):
                 value_str = ", ".join(map(str, value))
            elif isinstance(value, dict):
                 value_str = "\n" + "\n".join(f"    - {k}: {v}" for k, v in value.items())
            else:
                 value_str = str(value)

            logging.info(f"  {key_title}: {value_str}")

        # Explicitly display relationships
        logging.info("\n  Relationships:")
        if self.person.relationships:
            for rel in self.person.relationships:
                 other_person_id = rel.get_other_person(self.person.person_id)
                 other_person_name = "Unknown"
                 if self.person.family_tree:
                      other_person = self.person.family_tree.get_person_by_id(other_person_id)
                      if other_person: other_person_name = other_person.get_full_name()    
                 logging.info(f"    - {rel.relationship_type.title()} with {other_person_name} ({other_person_id[:6]}...) [{rel.start_date.strftime('%Y-%m-%d') if rel.start_date else '?'}-{rel.end_date.strftime('%Y-%m-%d') if rel.end_date else '?'}]")
        else:
            logging.info("    (None recorded)")

        logging.info("-----------------------------------------------------")


class RelationshipView:
    """Displays details for a single relationship."""
    def __init__(self, relationship: Relationship, family_tree: Optional[FamilyTree] = None):
        """
        Args:
            relationship (Relationship): The relationship to display.
            family_tree (Optional[FamilyTree]): Needed to look up person names.
        """
        self.relationship = relationship
        self.family_tree = family_tree # Store reference to lookup names

    def _get_person_name(self, person_id: str) -> str:
        """Helper to get person name from the tree, or return ID if not found."""
        if self.family_tree:
            person = self.family_tree.get_person_by_id(person_id)
            if person:
                return f"{person.get_full_name()} ({person_id[:6]}...)"
        return f"ID: {person_id}"


    def display_relationship(self):
        """Prints the relationship details to the console."""
        logging.info("\n--- Relationship Details ---")
        p1_name = self._get_person_name(self.relationship.person1_id)
        p2_name = self._get_person_name(self.relationship.person2_id)

        logging.info(f"  Person 1: {p1_name}")
        logging.info(f"  Person 2: {p2_name}")
        logging.info(f"  Type: {self.relationship.relationship_type.title()}")
        start = self.relationship.start_date.strftime('%Y-%m-%d') if self.relationship.start_date else "Unknown"
        end = self.relationship.end_date.strftime('%Y-%m-%d') if self.relationship.end_date else "Present"
        logging.info(f"  Duration: {start} - {end}")
        if self.relationship.description:
            logging.info(f"  Description: {self.relationship.description}")
        logging.info("----------------------------")

