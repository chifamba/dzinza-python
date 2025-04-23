# backend/src/family_tree.py
import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
from datetime import date
import uuid # Ensure uuid is imported

# Import Person and Relationship from sibling modules
from .person import Person
from .relationship import Relationship, get_reciprocal_relationship, VALID_RELATIONSHIP_TYPES
from .audit_log import log_audit
from .db_utils import load_data, save_data


class FamilyTree:
    """
    Manages the collection of people and relationships in a family tree.
    Handles loading from and saving to a JSON file.
    """
    def __init__(self, tree_file_path=None, audit_log_path=None):
        """
        Initializes the FamilyTree.

        Args:
            tree_file_path (str, optional): Path to the JSON file storing tree data.
                                            Defaults to 'backend/data/family_tree.json'.
            audit_log_path (str, optional): Path to the audit log file.
                                            Defaults to 'backend/logs/audit.log'.
        """
        # Determine base directory relative to this file's location
        backend_dir = os.path.dirname(os.path.dirname(__file__)) # Go up two directories

        # Set default paths relative to the backend directory
        self.tree_file_path = tree_file_path or os.path.join(backend_dir, 'data', 'family_tree.json')
        self.audit_log_path = audit_log_path or os.path.join(backend_dir, 'logs', 'backend', 'audit.log') # Corrected default path

        # Ensure directories exist
        tree_dir = os.path.dirname(self.tree_file_path)
        log_dir = os.path.dirname(self.audit_log_path)
        if tree_dir: os.makedirs(tree_dir, exist_ok=True)
        if log_dir: os.makedirs(log_dir, exist_ok=True)

        self.people: Dict[str, Person] = {}
        self.relationships: Dict[str, Relationship] = {}
        logging.info(f"FamilyTree initialized. Data file: {self.tree_file_path}, Audit log: {self.audit_log_path}")
        self.load_tree()

    # --- Person Management ---

    def add_person(self, first_name: str, last_name: str = "", nickname: Optional[str] = None,
                   dob: Optional[str] = None, dod: Optional[str] = None, gender: Optional[str] = None,
                   pob: Optional[str] = None, pod: Optional[str] = None, notes: Optional[str] = None,
                   added_by: str = "system", **kwargs) -> Optional[Person]:
        """
        Adds a new person to the family tree.

        Args:
            first_name (str): The person's first name.
            last_name (str, optional): The person's last name. Defaults to "".
            nickname (Optional[str], optional): The person's nickname. Defaults to None.
            dob (Optional[str], optional): Date of birth (YYYY-MM-DD). Defaults to None.
            dod (Optional[str], optional): Date of death (YYYY-MM-DD). Defaults to None.
            gender (Optional[str], optional): Gender ('Male', 'Female', 'Other'). Defaults to None.
            pob (Optional[str], optional): Place of birth. Defaults to None.
            pod (Optional[str], optional): Place of death. Defaults to None.
            notes (Optional[str], optional): Additional notes. Defaults to None.
            added_by (str, optional): Username of the user adding the person. Defaults to "system".
            **kwargs: Additional attributes to store in the person's attributes dictionary.

        Returns:
            Optional[Person]: The newly created Person object, or None if creation failed.
        """
        try:
            # Basic validation
            if not first_name or not isinstance(first_name, str):
                raise ValueError("First name is required and must be a string.")
            if dob and not self._is_valid_date(dob):
                raise ValueError("Invalid date format for Date of Birth (YYYY-MM-DD).")
            if dod and not self._is_valid_date(dod):
                raise ValueError("Invalid date format for Date of Death (YYYY-MM-DD).")
            if dob and dod and date.fromisoformat(dod) < date.fromisoformat(dob):
                raise ValueError("Date of Death cannot be before Date of Birth.")
            if gender and gender not in ['Male', 'Female', 'Other']:
                raise ValueError("Invalid gender. Use 'Male', 'Female', or 'Other'.")

            person_id = str(uuid.uuid4()) # Generate a unique ID
            new_person = Person(
                person_id=person_id,
                first_name=first_name.strip(),
                last_name=last_name.strip() if last_name else "",
                nickname=nickname.strip() if nickname else None,
                birth_date=dob,
                death_date=dod,
                gender=gender,
                place_of_birth=pob.strip() if pob else None,
                place_of_death=pod.strip() if pod else None,
                notes=notes.strip() if notes else None,
                attributes=kwargs # Store any extra attributes
            )
            self.people[person_id] = new_person
            self.save_tree()
            log_audit(self.audit_log_path, added_by, 'add_person', f'success - id: {person_id}, name: {new_person.get_full_name()}')
            logging.info(f"Added person: {new_person}")
            return new_person
        except ValueError as ve:
            logging.error(f"Error adding person (Validation): {ve}", exc_info=False) # No need for traceback on validation
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: {ve}')
            return None
        except Exception as e:
            logging.error(f"Unexpected error adding person: {e}", exc_info=True)
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - unexpected: {e}')
            return None

    def edit_person(self, person_id: str, updates: Dict[str, Any], edited_by: str = "system") -> bool:
        """
        Edits details of an existing person.

        Args:
            person_id (str): The ID of the person to edit.
            updates (Dict[str, Any]): Dictionary containing fields to update and their new values.
                                      Allowed keys match Person attributes.
            edited_by (str, optional): Username of the user editing the person. Defaults to "system".

        Returns:
            bool: True if the person was found and updated (even if no effective change), False otherwise.
        """
        person = self.find_person(person_id=person_id)
        if not person:
            logging.warning(f"edit_person: Person with ID {person_id} not found.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - person not found: {person_id}')
            return False

        logging.info(f"Attempting to edit person {person_id} by {edited_by}. Updates: {updates}")
        original_data = person.to_dict() # For comparison/logging if needed
        updated = False
        validation_errors = {}

        # Validate and apply updates
        allowed_fields = list(Person.__annotations__.keys()) # Get fields from dataclass definition
        allowed_fields.remove('person_id') # ID cannot be changed

        # Validate dates first
        new_dob = updates.get('birth_date', person.birth_date)
        new_dod = updates.get('death_date', person.death_date)
        if 'birth_date' in updates and new_dob and not self._is_valid_date(new_dob):
            validation_errors['birth_date'] = "Invalid date format (YYYY-MM-DD)."
        if 'death_date' in updates and new_dod and not self._is_valid_date(new_dod):
            validation_errors['death_date'] = "Invalid date format (YYYY-MM-DD)."
        if new_dob and new_dod and 'birth_date' not in validation_errors and 'death_date' not in validation_errors:
            try:
                if date.fromisoformat(new_dod) < date.fromisoformat(new_dob):
                    validation_errors['death_date'] = "Date of Death cannot be before Date of Birth."
            except (ValueError, TypeError):
                 validation_errors['date_comparison'] = "Invalid date format for comparison." # Should have been caught above, but check again

        # Validate gender if present
        if 'gender' in updates and updates['gender'] and updates['gender'] not in ['Male', 'Female', 'Other']:
             validation_errors['gender'] = "Invalid gender. Use 'Male', 'Female', or 'Other'."

        if validation_errors:
            logging.warning(f"Validation errors editing person {person_id}: {validation_errors}")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: {validation_errors} for {person_id}')
            # Optionally raise an exception or return a specific code/message
            # For now, just return False as update didn't proceed
            return False

        # Apply valid updates
        for field, value in updates.items():
            if field in allowed_fields:
                # Strip strings, handle None for optional fields
                current_value = getattr(person, field)
                new_value = value
                if isinstance(new_value, str):
                    new_value = new_value.strip()
                if field in ['nickname', 'birth_date', 'death_date', 'gender', 'place_of_birth', 'place_of_death', 'notes'] and not new_value:
                    new_value = None # Set optional fields to None if update value is empty

                if current_value != new_value:
                    setattr(person, field, new_value)
                    updated = True
                    logging.debug(f"Updated field '{field}' for person {person_id}")
            elif field == 'attributes' and isinstance(value, dict):
                 # Special handling for attributes dictionary (merge or replace?)
                 # Let's merge for now
                 if person.attributes != value: # Check if attributes actually changed
                     person.attributes.update(value) # Or person.attributes = value for replacement
                     updated = True
                     logging.debug(f"Updated attributes for person {person_id}")
            else:
                 logging.warning(f"edit_person: Ignoring invalid or disallowed field '{field}' for person {person_id}")


        if updated:
            self.save_tree()
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'success - id: {person_id}')
            logging.info(f"Successfully updated person {person_id}.")
        else:
            logging.info(f"No effective changes made to person {person_id}.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'no change - id: {person_id}')

        return True # Return True even if no changes, as the person was found

    def delete_person(self, person_id: str, deleted_by: str = "system") -> bool:
        """
        Deletes a person and all their associated relationships.

        Args:
            person_id (str): The ID of the person to delete.
            deleted_by (str, optional): Username of the user deleting the person. Defaults to "system".

        Returns:
            bool: True if the person was found and deleted, False otherwise.
        """
        if person_id not in self.people:
            logging.warning(f"delete_person: Person with ID {person_id} not found.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'failure - person not found: {person_id}')
            return False

        person_name = self.people[person_id].get_full_name()
        logging.info(f"Attempting to delete person {person_id} ('{person_name}') by {deleted_by}.")

        # Find and delete relationships involving this person
        rels_to_delete = [
            rel_id for rel_id, rel in self.relationships.items()
            if rel.person1_id == person_id or rel.person2_id == person_id
        ]
        deleted_rel_count = 0
        for rel_id in rels_to_delete:
            if rel_id in self.relationships:
                del self.relationships[rel_id]
                deleted_rel_count += 1
                logging.debug(f"Deleted associated relationship {rel_id} for person {person_id}.")

        # Delete the person
        del self.people[person_id]
        self.save_tree()
        log_audit(self.audit_log_path, deleted_by, 'delete_person', f'success - id: {person_id}, name: {person_name}, deleted {deleted_rel_count} relationships')
        logging.info(f"Deleted person {person_id} ('{person_name}') and {deleted_rel_count} relationships.")
        return True

    def find_person(self, person_id: Optional[str] = None, name: Optional[str] = None) -> Optional[Person]:
        """
        Finds a person by ID or name (case-insensitive partial match on full name).

        Args:
            person_id (Optional[str]): The exact ID of the person.
            name (Optional[str]): A name (or part of a name) to search for.

        Returns:
            Optional[Person]: The found Person object, or None if not found.
                              If searching by name and multiple matches occur, returns the first match.
        """
        if person_id:
            return self.people.get(person_id)
        elif name:
            search_name_lower = name.lower()
            for person in self.people.values():
                # Simple search: check if search term is in first or last name
                if (person.first_name and search_name_lower in person.first_name.lower()) or \
                   (person.last_name and search_name_lower in person.last_name.lower()) or \
                   (person.nickname and search_name_lower in person.nickname.lower()):
                    return person
            return None # Not found by name
        else:
            logging.warning("find_person called without person_id or name.")
            return None

    # --- Relationship Management ---

    def add_relationship(self, person1_id: str, person2_id: str, relationship_type: str,
                         attributes: Optional[Dict[str, Any]] = None, added_by: str = "system") -> Optional[Relationship]:
        """
        Adds a new relationship between two people.

        Args:
            person1_id (str): ID of the first person.
            person2_id (str): ID of the second person.
            relationship_type (str): The type of relationship (e.g., 'spouse', 'parent').
            attributes (Optional[Dict[str, Any]], optional): Custom attributes. Defaults to None.
            added_by (str, optional): Username of the user adding the relationship. Defaults to "system".

        Returns:
            Optional[Relationship]: The newly created Relationship object, or None if creation failed.
        """
        # Validate inputs
        if person1_id not in self.people:
            logging.error(f"add_relationship: Person 1 with ID {person1_id} not found.")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - person1 not found: {person1_id}')
            return None
        if person2_id not in self.people:
            logging.error(f"add_relationship: Person 2 with ID {person2_id} not found.")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - person2 not found: {person2_id}')
            return None
        if person1_id == person2_id:
            logging.error("add_relationship: Cannot add relationship between a person and themselves.")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - self-relationship attempt: {person1_id}')
            return None
        if not relationship_type: # Check for empty string
             logging.error("add_relationship: Relationship type cannot be empty.")
             log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - empty relationship type between {person1_id} and {person2_id}')
             return None
        # Optional: Stricter validation against VALID_RELATIONSHIP_TYPES
        # if relationship_type.lower() not in VALID_RELATIONSHIP_TYPES:
        #    logging.warning(f"Adding relationship with potentially invalid type: '{relationship_type}'")
        #    # Decide whether to reject or allow

        # Check if relationship already exists (consider directionality if needed)
        # Simple check: Does *any* relationship exist between these two?
        # More complex: Does this specific type exist? (e.g., prevent adding 'spouse' twice)
        for rel in self.relationships.values():
            if (rel.person1_id == person1_id and rel.person2_id == person2_id) or \
               (rel.person1_id == person2_id and rel.person2_id == person1_id):
                # Found an existing relationship between these two people.
                # Check if it's the same type we're trying to add.
                if rel.rel_type.lower() == relationship_type.lower():
                    logging.warning(f"Relationship '{relationship_type}' already exists between {person1_id} and {person2_id}.")
                    log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - relationship type {relationship_type} already exists between {person1_id} and {person2_id}')
                    return None # Or return the existing relationship?

        try:
            new_rel = Relationship(
                person1_id=person1_id,
                person2_id=person2_id,
                rel_type=relationship_type,
                attributes=attributes # Handled by __post_init__
            )
            self.relationships[new_rel.rel_id] = new_rel
            self.save_tree()
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'success - id: {new_rel.rel_id}, type: {relationship_type} between {person1_id} and {person2_id}')
            logging.info(f"Added relationship: {new_rel}")
            return new_rel
        except ValueError as ve: # Catch validation errors from Relationship.__post_init__
            logging.error(f"Error adding relationship (Validation): {ve}", exc_info=False)
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: {ve}')
            return None
        except Exception as e:
            logging.error(f"Unexpected error adding relationship: {e}", exc_info=True)
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - unexpected: {e}')
            return None

    def edit_relationship(self, relationship_id: str, updates: Dict[str, Any], edited_by: str = "system") -> bool:
        """
        Edits details of an existing relationship.

        Args:
            relationship_id (str): The ID of the relationship to edit.
            updates (Dict[str, Any]): Dictionary containing fields to update.
                                      Allowed keys: 'rel_type', 'attributes', 'person1_id', 'person2_id'.
            edited_by (str, optional): Username of the user editing. Defaults to "system".

        Returns:
            bool: True if the relationship was found and updated, False otherwise.
        """
        rel = self.relationships.get(relationship_id)
        if not rel:
            logging.warning(f"edit_relationship: Relationship with ID {relationship_id} not found.")
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'failure - relationship not found: {relationship_id}')
            return False

        logging.info(f"Attempting to edit relationship {relationship_id} by {edited_by}. Updates: {updates}")
        updated = False
        validation_errors = {}

        # Validate potential updates
        new_type = updates.get('rel_type', rel.rel_type)
        new_p1 = updates.get('person1_id', rel.person1_id)
        new_p2 = updates.get('person2_id', rel.person2_id)
        new_attrs = updates.get('attributes') # Check type later

        if 'rel_type' in updates and (not new_type or not isinstance(new_type, str)):
             validation_errors['rel_type'] = "Relationship type must be a non-empty string."
        # elif 'rel_type' in updates and new_type.lower() not in VALID_RELATIONSHIP_TYPES:
        #      logging.warning(f"Editing relationship {relationship_id} to potentially invalid type: '{new_type}'")
             # Decide if this is an error

        if 'person1_id' in updates:
             if not new_p1 or not isinstance(new_p1, str): validation_errors['person1_id'] = "Person 1 ID must be a non-empty string."
             elif new_p1 not in self.people: validation_errors['person1_id'] = f"Person with ID {new_p1} not found."
        if 'person2_id' in updates:
             if not new_p2 or not isinstance(new_p2, str): validation_errors['person2_id'] = "Person 2 ID must be a non-empty string."
             elif new_p2 not in self.people: validation_errors['person2_id'] = f"Person with ID {new_p2} not found."

        if new_p1 == new_p2: # Check if update would result in self-relationship
             validation_errors['person_ids'] = "Person 1 and Person 2 cannot be the same."

        if 'attributes' in updates and not isinstance(new_attrs, dict):
             validation_errors['attributes'] = "Attributes must be a dictionary."

        if validation_errors:
            logging.warning(f"Validation errors editing relationship {relationship_id}: {validation_errors}")
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'failure - validation: {validation_errors} for {relationship_id}')
            return False

        # Apply valid updates
        if 'rel_type' in updates and rel.rel_type != new_type:
            rel.rel_type = new_type
            updated = True
        if 'person1_id' in updates and rel.person1_id != new_p1:
            rel.person1_id = new_p1
            updated = True
        if 'person2_id' in updates and rel.person2_id != new_p2:
            rel.person2_id = new_p2
            updated = True
        if 'attributes' in updates and rel.attributes != new_attrs:
            rel.attributes = new_attrs if new_attrs is not None else {} # Ensure it's a dict
            updated = True

        if updated:
            self.save_tree()
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'success - id: {relationship_id}')
            logging.info(f"Successfully updated relationship {relationship_id}.")
        else:
            logging.info(f"No effective changes made to relationship {relationship_id}.")
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'no change - id: {relationship_id}')

        return True # Return True even if no changes, as relationship was found

    def delete_relationship(self, relationship_id: str, deleted_by: str = "system") -> bool:
        """
        Deletes a specific relationship by its ID.

        Args:
            relationship_id (str): The ID of the relationship to delete.
            deleted_by (str, optional): Username of the user deleting. Defaults to "system".

        Returns:
            bool: True if the relationship was found and deleted, False otherwise.
        """
        if relationship_id not in self.relationships:
            logging.warning(f"delete_relationship: Relationship with ID {relationship_id} not found.")
            log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'failure - relationship not found: {relationship_id}')
            return False

        rel_info = repr(self.relationships[relationship_id]) # Get info before deleting
        del self.relationships[relationship_id]
        self.save_tree()
        log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'success - id: {relationship_id}, info: {rel_info}')
        logging.info(f"Deleted relationship {relationship_id}.")
        return True

    # --- Data Persistence ---

    def save_tree(self):
        """Saves the current state of the family tree (people and relationships) to the JSON file."""
        logging.debug(f"Attempting to save tree to {self.tree_file_path}")
        try:
            tree_data = {
                "people": {pid: person.to_dict() for pid, person in self.people.items()},
                "relationships": {rid: rel.to_dict() for rid, rel in self.relationships.items()}
            }
            # Use db_utils to handle saving and encryption
            save_data(self.tree_file_path, tree_data, is_encrypted=True)
            logging.info(f"Family tree saved successfully to {self.tree_file_path}")
        except Exception as e:
            logging.error(f"Failed to save family tree to {self.tree_file_path}: {e}", exc_info=True)
            # Avoid audit log for routine saves unless specifically needed
            # log_audit(self.audit_log_path, "system", "save_tree", f"failure: {e}")

    def load_tree(self, loaded_by="system"):
        """Loads the family tree state from the JSON file."""
        logging.debug(f"Attempting to load tree from {self.tree_file_path}")
        try:
            # Use db_utils to handle loading and decryption
            data = load_data(self.tree_file_path, default=None, is_encrypted=True)

            if data is None or not isinstance(data, dict):
                 # This case handles file not found, decryption failure, or invalid format from load_data
                 logging.warning(f"No valid data loaded from {self.tree_file_path}. Initializing empty tree.")
                 self.people = {}
                 self.relationships = {}
                 # Optionally save an empty encrypted file immediately if one didn't exist
                 # if not os.path.exists(self.tree_file_path):
                 #     self.save_tree()
                 return

            # If data is loaded, process it
            loaded_people = {}
            loaded_relationships = {}
            invalid_people_count = 0
            invalid_rel_count = 0

            # Load people
            people_data = data.get("people", {})
            if isinstance(people_data, dict):
                for pid, p_data in people_data.items():
                    try:
                        if isinstance(p_data, dict):
                            loaded_people[pid] = Person.from_dict(p_data)
                        else:
                             logging.warning(f"Invalid data format for person ID {pid} in {self.tree_file_path}. Skipping.")
                             invalid_people_count += 1
                    except (KeyError, ValueError, TypeError) as e:
                        logging.error(f"Error loading person data for ID {pid} from {self.tree_file_path}: {e}. Skipping.")
                        invalid_people_count += 1

            # Load relationships
            relationships_data = data.get("relationships", {})
            if isinstance(relationships_data, dict):
                for rid, r_data in relationships_data.items():
                     try:
                         if isinstance(r_data, dict):
                             # Ensure persons exist before adding relationship
                             p1_id = r_data.get('person1_id')
                             p2_id = r_data.get('person2_id')
                             if p1_id in loaded_people and p2_id in loaded_people:
                                 loaded_relationships[rid] = Relationship.from_dict(r_data)
                             else:
                                 logging.warning(f"Skipping relationship {rid}: Person ID {p1_id or '??'} or {p2_id or '??'} not found/loaded.")
                                 invalid_rel_count += 1
                         else:
                              logging.warning(f"Invalid data format for relationship ID {rid} in {self.tree_file_path}. Skipping.")
                              invalid_rel_count += 1
                     except (KeyError, ValueError, TypeError) as e:
                         logging.error(f"Error loading relationship data for ID {rid} from {self.tree_file_path}: {e}. Skipping.")
                         invalid_rel_count += 1

            self.people = loaded_people
            self.relationships = loaded_relationships

            log_msg = f"success - loaded {len(self.people)} people, {len(self.relationships)} relationships."
            if invalid_people_count > 0: log_msg += f" Skipped {invalid_people_count} invalid people entries."
            if invalid_rel_count > 0: log_msg += f" Skipped {invalid_rel_count} invalid relationship entries."
            logging.info(f"Family tree loaded successfully: {len(self.people)} people, {len(self.relationships)} relationships.")
            log_audit(self.audit_log_path, loaded_by, 'load_tree', log_msg)

        # --- MODIFIED EXCEPTION LOGGING ---
        except Exception as e:
            log_audit_msg = f'failure: {e}'
            # Check if it's a RecursionError to avoid deep traceback logging
            if isinstance(e, RecursionError):
                 logging.error(f"Critical RecursionError loading family tree from {self.tree_file_path}: {e}")
                 log_audit_msg = f'failure: RecursionError - {e}'
            else:
                 # Log other exceptions with full traceback
                 logging.error(f"Critical error loading family tree from {self.tree_file_path}: {e}", exc_info=True)

            log_audit(self.audit_log_path, loaded_by, 'load_tree', log_audit_msg)
            # Reset to empty state on critical load failure
            self.people = {}
            self.relationships = {}
        # --- END MODIFIED EXCEPTION LOGGING ---

    # --- Utility Methods ---

    @staticmethod
    def _is_valid_date(date_str: Optional[str]) -> bool:
        """Checks if a string is a valid YYYY-MM-DD date."""
        if not date_str:
            return True # Allow empty/None dates
        try:
            date.fromisoformat(date_str)
            return True
        except (ValueError, TypeError):
            return False

    # --- Data for Visualization ---

    def get_nodes_links_data(self, start_node_id: Optional[str] = None, max_depth: Optional[int] = None) -> Dict[str, List[Dict]]:
        """
        Generates data suitable for graph visualization libraries (like React Flow).

        Args:
            start_node_id (Optional[str]): The ID of the person to start the traversal from.
                                           If None, returns the full tree.
            max_depth (Optional[int]): The maximum depth to traverse from the start node.
                                       Ignored if start_node_id is None.

        Returns:
            Dict[str, List[Dict]]: A dictionary containing 'nodes' and 'links' (or 'edges').
        """
        nodes_data = []
        links_data = []

        if start_node_id:
            # Implement BFS or DFS traversal if needed for partial loading
             logging.warning("Partial tree loading (start_node/depth) not fully implemented yet. Returning full tree.")
             # For now, return full tree regardless of start_node/depth
             people_to_include = self.people
             rels_to_include = self.relationships
        else:
            # Full tree
            people_to_include = self.people
            rels_to_include = self.relationships


        # Create nodes
        for person_id, person in people_to_include.items():
            if not isinstance(person, Person): continue # Skip invalid entries
            nodes_data.append({
                "id": person.person_id, # Ensure consistency
                "type": "personNode", # Node type for React Flow
                "data": {
                    "id": person.person_id, # Pass ID for editing
                    "label": person.get_display_name(),
                    "full_name": person.get_full_name(),
                    "gender": person.gender,
                    "dob": person.birth_date,
                    "dod": person.death_date,
                    "birth_place": person.place_of_birth,
                    "death_place": person.place_of_death,
                    # Add photo URL later if implemented
                    "photoUrl": getattr(person, 'photo_url', None) # Example if photo added
                },
                "position": {"x": 0, "y": 0} # Placeholder, layout engine will set this
            })

        # Create links (edges)
        for rel_id, rel in rels_to_include.items():
            if not isinstance(rel, Relationship): continue # Skip invalid entries
            # Ensure both source and target nodes exist in our included people
            if rel.person1_id in people_to_include and rel.person2_id in people_to_include:
                links_data.append({
                    "id": rel.rel_id,
                    "source": rel.person1_id,
                    "target": rel.person2_id,
                    "type": "default", # Or use custom edge types
                    "animated": False, # Or True
                    "label": rel.rel_type, # Display relationship type
                    "data": rel.attributes # Pass attributes if needed by frontend
                })

        return {"nodes": nodes_data, "links": links_data} # Use 'links' or 'edges' based on frontend expectation


    # --- Internal Helper for Loading ---
    # This method might be redundant if load_tree handles everything
    @classmethod
    def _from_dict(cls, data: dict, tree_file_path: str, audit_log_path: str) -> 'FamilyTree':
        """
        (Deprecated/Internal) Creates a FamilyTree instance from dictionary data.
        Prefer using load_tree directly on an instance.
        """
        logging.warning("_from_dict is likely deprecated. Use instance.load_tree() instead.")
        tree = cls(tree_file_path=tree_file_path, audit_log_path=audit_log_path) # Creates instance, which calls load_tree

        # The logic below is now mostly handled within load_tree itself
        # people_data = data.get("people", {})
        # relationships_data = data.get("relationships", {})

        # for pid, p_data in people_data.items():
        #     try:
        #         tree.people[pid] = Person.from_dict(p_data)
        #     except Exception as e:
        #         logging.error(f"Error loading person {pid} in _from_dict: {e}")

        # for rid, r_data in relationships_data.items():
        #     try:
        #         # Ensure persons exist before adding relationship
        #         p1_id = r_data.get('person1_id')
        #         p2_id = r_data.get('person2_id')
        #         if p1_id in tree.people and p2_id in tree.people:
        #              tree.relationships[rid] = Relationship.from_dict(r_data)
        #         else:
        #              logging.warning(f"Skipping relationship {rid} in _from_dict: Person {p1_id} or {p2_id} not loaded.")
        #     except Exception as e:
        #         logging.error(f"Error loading relationship {rid} in _from_dict: {e}")

        return tree

