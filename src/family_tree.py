# src/family_tree.py
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
        tree_dir = os.path.dirname(tree_file_path)
        if tree_dir:
             os.makedirs(tree_dir, exist_ok=True)


    def add_person(self, first_name, last_name, nickname=None, dob=None, dod=None, gender=None, added_by="system", **kwargs):
        """
        Adds a new person to the family tree using separate name fields.

        Args:
            first_name (str): The first name of the person.
            last_name (str): The last name of the person.
            nickname (str, optional): A nickname for the person. Defaults to None.
            dob (str, optional): Date of birth (YYYY-MM-DD). Defaults to None.
            dod (str, optional): Date of death (YYYY-MM-DD). Defaults to None.
            gender (str, optional): Gender of the person. Defaults to None.
            added_by (str): Username of the user adding the person. Defaults to "system".
            **kwargs: Additional attributes for the person.

        Returns:
            Person: The newly created Person object, or None if creation failed (e.g., invalid data).
        """
        # Basic validation for required names
        if not first_name:
            print("Error: Person's first name cannot be empty.")
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - empty first name')
            return None
        # Allow empty last name, but maybe log a warning?

        person_id = str(uuid.uuid4()) # Generate a unique ID

        # Instantiate Person correctly using separate name fields
        try:
            person = Person(
                person_id=person_id,
                first_name=first_name.strip(), # Strip whitespace
                last_name=last_name.strip() if last_name else "", # Strip or set empty
                nickname=nickname.strip() if nickname else None, # Strip or set None
                birth_date=dob if dob else None, # Ensure empty strings become None
                death_date=dod if dod else None, # Ensure empty strings become None
                gender=gender if gender else None, # Ensure empty strings become None
                attributes=kwargs # Pass any other attributes
            )
        except Exception as e:
            print(f"Error creating Person object: {e}")
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - error creating person object: {e}')
            return None

        self.people[person_id] = person

        # Use get_display_name() which includes nickname for printing
        # Use get_full_name() for logging the base name
        display_name = person.get_display_name()
        full_name = person.get_full_name()
        print(f"Person added: {display_name} (ID: {person.person_id})")
        log_audit(self.audit_log_path, added_by, 'add_person', f'success - id: {person.person_id}, name: {full_name}')

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
        person1 = self.people.get(person1_id)
        person2 = self.people.get(person2_id)

        if not person1 or not person2:
            missing_ids = []
            if not person1: missing_ids.append(person1_id)
            if not person2: missing_ids.append(person2_id)
            print(f"Error: One or both persons (ID(s): {', '.join(missing_ids)}) not found.")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - person not found ({", ".join(missing_ids)})')
            return None

        # Optional: Add validation for relationship_type if needed

        relationship_id = str(uuid.uuid4())
        # Assuming Relationship class takes id, p1_id, p2_id, type
        # Update if Relationship class definition is different
        try:
            # Use Relationship from relationship.py which expects p1_id, p2_id, rel_type
            relationship = Relationship(person1_id=person1_id, person2_id=person2_id, rel_type=relationship_type)
            # Add relationship to internal storage (if your design requires it)
            # This example assumes relationships are primarily managed via Person objects
            # or a separate lookup. If self.relationships is the primary store:
            self.relationships[relationship_id] = relationship # Store relationship itself if needed

            # Optionally, link relationship to Person objects if Person stores relationships
            # person1.add_relationship(relationship) # Requires Person.add_relationship method
            # person2.add_relationship(relationship) # Requires Person.add_relationship method

            # Use display names for print statement
            print(f"Relationship added: {person1.get_display_name()} - {relationship_type} - {person2.get_display_name()}")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'success - type: {relationship_type}, persons: ({person1_id}, {person2_id})')
            self.save_tree(added_by) # Save after adding
            return relationship
        except Exception as e:
            print(f"Error creating Relationship object: {e}")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - error creating relationship object: {e}')
            return None


    def find_person(self, name=None, person_id=None):
        """
        Finds a person by name or ID. Name search is case-insensitive and checks full name.

        Args:
            name (str, optional): The name of the person to find (case-insensitive).
            person_id (str, optional): The ID of the person to find.

        Returns:
            Person: The found Person object, or None if not found.
                 If name is provided and multiple matches exist, returns the first match.
        """
        if person_id:
            return self.people.get(person_id)
        if name:
            search_name_lower = name.lower()
            # Find first match by name (case-insensitive)
            for person in self.people.values():
                # Use get_full_name for comparison
                if person.get_full_name().lower() == search_name_lower:
                    return person
        return None

    def get_people_summary(self):
        """
        Returns a list of basic information for all people in the tree.
        Includes full name, display name (with nickname), and nickname separately.

        Returns:
            list[dict]: A list of dictionaries, each containing person details.
                        Sorted alphabetically by full name.
        """
        summary_list = []
        for p in self.people.values():
             full_name = p.get_full_name()
             display_name = p.get_display_name() # Includes nickname
             summary_list.append({
                 "person_id": p.person_id,
                 "name": full_name, # Full name (first last) for sorting/internal use
                 "display_name": display_name, # Name including nickname for display
                 "nickname": p.nickname, # Include nickname separately if needed
                 "dob": p.birth_date, # Use correct attribute name
                 "dod": p.death_date, # Use correct attribute name
                 "gender": p.gender
             })

        # Sort alphabetically by the full name
        return sorted(summary_list, key=lambda x: x['name'])


    def get_relationships_summary(self):
        """
        Returns a list of detailed information for all relationships in the tree.
        Includes display names (with nicknames) of the people involved.

        Returns:
            list[dict]: A list of dictionaries, each containing relationship details.
                        Sorted by relationship type, then person1 full name.
        """
        summary = []
        # Iterate through the relationships stored in self.relationships
        for rel_id, rel in self.relationships.items():
            person1 = self.people.get(rel.person1_id)
            person2 = self.people.get(rel.person2_id)

            # Handle cases where a person might be missing from the people dict (data integrity issue)
            person1_display_name = person1.get_display_name() if person1 else f"Unknown (ID: {rel.person1_id[:8]}...)"
            person2_display_name = person2.get_display_name() if person2 else f"Unknown (ID: {rel.person2_id[:8]}...)"
            # Keep person1_name for sorting if needed, using full name
            person1_sort_name = person1.get_full_name() if person1 else "Unknown"


            summary.append({
                "relationship_id": rel_id, # Use the key from the dictionary as ID
                "person1_id": rel.person1_id,
                "person1_name": person1_display_name, # Use display name
                "person2_id": rel.person2_id,
                "person2_name": person2_display_name, # Use display name
                "relationship_type": rel.rel_type, # Use correct attribute name from Relationship class
                "_person1_sort_name": person1_sort_name # Internal key for sorting by full name
            })

        # Sort the summary list, e.g., by type then by the first person's full name
        return sorted(summary, key=lambda x: (x['relationship_type'], x['_person1_sort_name']))


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
        # Load people
        tree.people = {}
        for pid, pdata in data.get("people", {}).items():
             try:
                 tree.people[pid] = Person.from_dict(pdata)
             except (KeyError, ValueError, TypeError) as e:
                 print(f"Warning: Skipping invalid person data for ID {pid} during load: {e}")
                 # Optionally log this warning
        # Load relationships
        tree.relationships = {}
        for rid, rdata in data.get("relationships", {}).items():
             try:
                 tree.relationships[rid] = Relationship.from_dict(rdata)
             except (KeyError, ValueError, TypeError) as e:
                 print(f"Warning: Skipping invalid relationship data for ID {rid} during load: {e}")
                 # Optionally log this warning
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
                # Use _from_dict which handles potential errors during object creation
                loaded_tree = self._from_dict(data, self.tree_file_path, self.audit_log_path)
                self.people = loaded_tree.people
                self.relationships = loaded_tree.relationships
                print(f"Family tree loaded successfully from {self.tree_file_path}. Found {len(self.people)} people and {len(self.relationships)} relationships.")
                # log_audit(self.audit_log_path, loaded_by, 'load_tree', 'success') # Can be noisy on startup
            else:
                 print(f"No existing data found or error loading from {self.tree_file_path}. Starting with an empty tree.")
                 # Initialize empty structure if file didn't exist or was empty/invalid
                 self.people = {}
                 self.relationships = {}

        except FileNotFoundError:
            print(f"Tree file {self.tree_file_path} not found. Starting with an empty tree.")
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
        """
        Edits an existing person's details.
        'updated_data' should be a dictionary with keys matching Person attributes
        (e.g., 'first_name', 'last_name', 'nickname', 'birth_date').
        """
        person = self.find_person(person_id=person_id)
        if person:
            original_display_name = person.get_display_name() # For logging
            changes_made = False
            for key, value in updated_data.items():
                # Ensure the key is a valid attribute of Person before setting
                if hasattr(person, key):
                    current_value = getattr(person, key)
                    # Strip whitespace for string values
                    new_value = value.strip() if isinstance(value, str) else value

                    # Handle empty strings for optional fields -> None
                    # Make sure 'first_name' and 'last_name' don't become None if empty
                    if key in ['nickname', 'birth_date', 'death_date', 'gender', 'notes'] and not new_value:
                        new_value = None
                    elif key in ['first_name', 'last_name'] and not new_value:
                         # Keep last_name as empty string if provided empty, ensure first_name isn't empty?
                         if key == 'first_name':
                              print(f"Warning: Attempted to set empty first_name for person {person_id}. Keeping original.")
                              continue # Skip setting empty first name
                         else: # last_name can be empty
                              new_value = ""


                    if current_value != new_value:
                        setattr(person, key, new_value)
                        changes_made = True
                else:
                     print(f"Warning: Attempted to update non-existent attribute '{key}' for person {person_id}")


            if changes_made:
                # Log using display name
                log_audit(self.audit_log_path, edited_by, 'edit_person', f'success - id: {person_id}, name: {original_display_name} -> {person.get_display_name()}')
                self.save_tree(edited_by)
                return True
            else:
                 log_audit(self.audit_log_path, edited_by, 'edit_person', f'no changes made for id: {person_id}')
                 return False # No changes were made
        else:
            print(f"Error: Person with ID {person_id} not found for editing.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - person not found: {person_id}')
            return False

    def delete_person(self, person_id, deleted_by="system"):
        """Deletes a person and their related relationships."""
        person = self.find_person(person_id=person_id)
        if person:
            person_display_name = person.get_display_name() # For logging
            # Remove the person
            del self.people[person_id]

            # Find and remove relationships involving this person from self.relationships
            rels_to_delete = [rid for rid, rel in self.relationships.items() if rel.person1_id == person_id or rel.person2_id == person_id]
            num_rels_deleted = len(rels_to_delete)
            for rid in rels_to_delete:
                del self.relationships[rid]

            # Log using display name
            print(f"Person '{person_display_name}' (ID: {person_id}) and {num_rels_deleted} related relationships deleted.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'success - id: {person_id}, name: {person_display_name}, removed {num_rels_deleted} relationships')
            self.save_tree(deleted_by)
            return True
        else:
            print(f"Error: Person with ID {person_id} not found for deletion.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'failure - person not found: {person_id}')
            return False

