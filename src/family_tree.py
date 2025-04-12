import json
import uuid
import os # Import os for path joining
from .person import Person
from .relationship import Relationship
from .db_utils import load_data, save_data # Use db_utils
from .audit_log import log_audit # Import audit log function

class FamilyTree:
    """
    Manages the collection of people and relationships in a family tree.
    Handles loading, saving, and modification of the tree data.
    """
    def __init__(self, tree_file_path='data/family_tree.json', audit_log_path='data/audit.log'):
        """
        Initializes the FamilyTree.

        Args:
            tree_file_path (str): The path to the JSON file storing family tree data.
            audit_log_path (str): The path to the audit log file.
        """
        self.people = {}  # Dictionary to store Person objects {person_id: Person}
        self.relationships = {}  # Dictionary to store Relationship objects {relationship_id: Relationship}
        self.tree_file_path = tree_file_path
        self.audit_log_path = audit_log_path
        # Ensure the directory for the tree file exists
        os.makedirs(os.path.dirname(tree_file_path), exist_ok=True)


    def add_person(self, name, dob=None, dod=None, gender=None, added_by="system", **kwargs):
        """
        Adds a new person to the family tree.

        Args:
            name (str): The full name of the person.
            dob (str, optional): Date of birth (YYYY-MM-DD). Defaults to None.
            dod (str, optional): Date of death (YYYY-MM-DD). Defaults to None.
            gender (str, optional): Gender of the person. Defaults to None.
            added_by (str): Username of the user adding the person. Defaults to "system".
            **kwargs: Additional attributes for the person.

        Returns:
            Person: The newly created Person object, or None if creation failed (e.g., invalid data).
        """
        if not name: # Basic validation
            print("Error: Person's name cannot be empty.")
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - empty name')
            return None

        person_id = str(uuid.uuid4()) # Generate a unique ID
        person = Person(person_id, name, dob, dod, gender=gender, **kwargs)
        self.people[person_id] = person
        print(f"Person added: {person.name} (ID: {person.person_id})")
        log_audit(self.audit_log_path, added_by, 'add_person', f'success - id: {person.person_id}, name: {person.name}')
        self.save_tree(added_by) # Save after adding
        return person

    def add_relationship(self, person1_id, person2_id, relationship_type, added_by="system"):
        """
        Adds a relationship between two people in the tree.

        Args:
            person1_id (str): The ID of the first person.
            person2_id (str): The ID of the second person.
            relationship_type (str): The type of relationship (e.g., 'parent-child', 'spouse').
            added_by (str): Username of the user adding the relationship. Defaults to "system".


        Returns:
            Relationship: The newly created Relationship object, or None if creation failed.
        """
        # Validate that both persons exist
        if person1_id not in self.people or person2_id not in self.people:
            print(f"Error: One or both persons (ID: {person1_id}, {person2_id}) not found.")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - person not found ({person1_id} or {person2_id})')
            return None

        # Optional: Add validation for relationship_type if needed
        # Example: allowed_types = ['parent-child', 'spouse', 'sibling']
        # if relationship_type not in allowed_types:
        #     print(f"Error: Invalid relationship type '{relationship_type}'.")
        #     log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - invalid type: {relationship_type}')
        #     return None

        relationship_id = str(uuid.uuid4())
        relationship = Relationship(relationship_id, person1_id, person2_id, relationship_type)
        self.relationships[relationship_id] = relationship
        print(f"Relationship added: {self.people[person1_id].name} - {relationship_type} - {self.people[person2_id].name}")
        log_audit(self.audit_log_path, added_by, 'add_relationship', f'success - id: {relationship_id}, type: {relationship_type}, persons: ({person1_id}, {person2_id})')
        self.save_tree(added_by) # Save after adding
        return relationship

    def find_person(self, name=None, person_id=None):
        """
        Finds a person by name or ID.

        Args:
            name (str, optional): The name of the person to find.
            person_id (str, optional): The ID of the person to find.

        Returns:
            Person: The found Person object, or None if not found.
                 If name is provided and multiple matches exist, returns the first match.
        """
        if person_id:
            return self.people.get(person_id)
        if name:
            for person in self.people.values():
                if person.name.lower() == name.lower():
                    return person
        return None

    def get_people_summary(self):
        """
        Returns a list of basic information for all people in the tree.
        Useful for populating dropdowns or simple lists in the UI.

        Returns:
            list[dict]: A list of dictionaries, each containing 'person_id' and 'name'.
                        Returns dictionaries instead of Person objects for easier JSON serialization
                        if needed elsewhere, and to avoid sending full objects to templates unnecessarily.
                        Also includes dob and dod for display.
        """
        return sorted(
            [
                {
                    "person_id": p.person_id,
                    "name": p.name,
                    "dob": p.dob,
                    "dod": p.dod,
                    "gender": p.gender
                 } for p in self.people.values()
             ],
            key=lambda x: x['name'] # Sort alphabetically by name
        )


    def _to_dict(self):
        """Converts the family tree data to a dictionary suitable for JSON serialization."""
        return {
            "people": {pid: person.to_dict() for pid, person in self.people.items()},
            "relationships": {rid: rel.to_dict() for rid, rel in self.relationships.items()}
        }

    @classmethod
    def _from_dict(cls, data, tree_file_path, audit_log_path):
        """Creates a FamilyTree instance from a dictionary (e.g., loaded from JSON)."""
        tree = cls(tree_file_path, audit_log_path) # Pass paths during reconstruction
        tree.people = {pid: Person.from_dict(pdata) for pid, pdata in data.get("people", {}).items()}
        tree.relationships = {rid: Relationship.from_dict(rdata) for rid, rdata in data.get("relationships", {}).items()}
        return tree

    def save_tree(self, saved_by="system"):
        """Saves the current state of the family tree to the JSON file."""
        try:
            data_to_save = self._to_dict()
            save_data(self.tree_file_path, data_to_save)
            print(f"Family tree saved successfully to {self.tree_file_path}")
            # Avoid logging save on every minor change if it's too noisy
            # log_audit(self.audit_log_path, saved_by, 'save_tree', 'success')
        except Exception as e:
            print(f"Error saving family tree to {self.tree_file_path}: {e}")
            log_audit(self.audit_log_path, saved_by, 'save_tree', f'failure: {e}')


    def load_tree(self, loaded_by="system"):
        """Loads the family tree data from the JSON file."""
        try:
            data = load_data(self.tree_file_path)
            if data:
                loaded_tree = self._from_dict(data, self.tree_file_path, self.audit_log_path)
                self.people = loaded_tree.people
                self.relationships = loaded_tree.relationships
                print(f"Family tree loaded successfully from {self.tree_file_path}")
                # log_audit(self.audit_log_path, loaded_by, 'load_tree', 'success') # Can be noisy on startup
            else:
                 print(f"No existing data found or error loading from {self.tree_file_path}. Starting with an empty tree.")
                 # Initialize empty structure if file didn't exist or was empty/invalid
                 self.people = {}
                 self.relationships = {}
                 # Optionally save an empty structure immediately
                 # self.save_tree()

        except FileNotFoundError:
            print(f"Tree file {self.tree_file_path} not found. Starting with an empty tree.")
            self.people = {}
            self.relationships = {}
            # Optionally save an empty structure immediately
            # self.save_tree()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {self.tree_file_path}: {e}. Starting with an empty tree.")
            self.people = {}
            self.relationships = {}
        except Exception as e:
            print(f"An unexpected error occurred loading the tree from {self.tree_file_path}: {e}")
            log_audit(self.audit_log_path, loaded_by, 'load_tree', f'failure: {e}')
            # Decide if you want to start fresh or halt
            self.people = {}
            self.relationships = {}

    # --- Methods for modification (placeholders for future implementation) ---

    def edit_person(self, person_id, updated_data, edited_by="system"):
        """Edits an existing person's details."""
        person = self.find_person(person_id=person_id)
        if person:
            original_name = person.name # For logging
            updated = person.update_details(updated_data)
            if updated:
                log_audit(self.audit_log_path, edited_by, 'edit_person', f'success - id: {person_id}, name: {original_name} -> {person.name}')
                self.save_tree(edited_by)
                return True
            else:
                 log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - no changes for id: {person_id}')
                 return False # No changes were made
        else:
            print(f"Error: Person with ID {person_id} not found for editing.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - person not found: {person_id}')
            return False

    def delete_person(self, person_id, deleted_by="system"):
        """Deletes a person and their related relationships."""
        person = self.find_person(person_id=person_id)
        if person:
            person_name = person.name # For logging
            # Remove the person
            del self.people[person_id]

            # Find and remove relationships involving this person
            rels_to_delete = [rid for rid, rel in self.relationships.items() if rel.person1_id == person_id or rel.person2_id == person_id]
            for rid in rels_to_delete:
                del self.relationships[rid]

            print(f"Person '{person_name}' (ID: {person_id}) and related relationships deleted.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'success - id: {person_id}, name: {person_name}, removed {len(rels_to_delete)} relationships')
            self.save_tree(deleted_by)
            return True
        else:
            print(f"Error: Person with ID {person_id} not found for deletion.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'failure - person not found: {person_id}')
            return False

