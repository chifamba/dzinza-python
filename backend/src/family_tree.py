# backend/src/family_tree.py
import os
import logging
from typing import Dict, List, Optional, Any # Removed Tuple
# Removed asdict
from datetime import date
import uuid

# Import Person and Relationship from sibling modules
try:
    from .person import Person
    from .relationship import Relationship # Removed get_reciprocal_relationship, VALID_RELATIONSHIP_TYPES
    from .audit_log import log_audit
    from .db_utils import load_data, save_data
except ImportError as e:
    logging.critical(f"Failed to import modules in family_tree: {e}")
    raise


class FamilyTree:
    """
    Manages the collection of people and relationships in a family tree.
    Handles loading from and saving to a JSON file. (Note: This file-based
    approach is likely superseded by the database implementation in app.py/services.py)
    """
    def __init__(self, tree_file_path=None, audit_log_path=None):
        """
        Initializes the FamilyTree.

        Args:
            tree_file_path (str, optional): Path to the JSON file storing tree data.
                                            Defaults to 'backend/data/family_tree.json'.
            audit_log_path (str, optional): Path to the audit log file.
                                            Defaults to 'backend/logs/backend/audit.log'.
        """
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        self.tree_file_path = tree_file_path or os.path.join(backend_dir, 'data', 'family_tree.json')
        self.audit_log_path = audit_log_path or os.path.join(backend_dir, 'logs', 'backend', 'audit.log')

        tree_dir = os.path.dirname(self.tree_file_path)
        log_dir = os.path.dirname(self.audit_log_path)
        if tree_dir: os.makedirs(tree_dir, exist_ok=True)
        if log_dir: os.makedirs(log_dir, exist_ok=True)

        self.people: Dict[str, Person] = {}
        self.relationships: Dict[str, Relationship] = {}
        logging.info(f"FamilyTree initialized. Data file: {self.tree_file_path}, Audit log: {self.audit_log_path}")
        self.load_tree() # Load data on initialization

    # --- Person Management ---

    def add_person(self, first_name: str, last_name: str = "", nickname: Optional[str] = None,
                   dob: Optional[str] = None, dod: Optional[str] = None, gender: Optional[str] = None,
                   pob: Optional[str] = None, pod: Optional[str] = None, notes: Optional[str] = None,
                   added_by: str = "system", **kwargs) -> Optional[Person]:
        """
        Adds a new person to the family tree. (In-memory version)
        """
        try:
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

            person_id = str(uuid.uuid4())
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
                attributes=kwargs
            )
            # Check for duplicate ID before adding
            if person_id in self.people:
                 raise ValueError(f"Person ID {person_id} collision detected.")

            self.people[person_id] = new_person
            self.save_tree()
            log_audit(self.audit_log_path, added_by, 'add_person', f'success - id: {person_id}, name: {new_person.get_full_name()}')
            logging.info(f"Added person: {new_person}")
            return new_person
        except ValueError as ve:
            logging.error(f"Error adding person (Validation): {ve}", exc_info=False)
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: {ve}')
            return None
        except Exception as e:
            logging.error(f"Unexpected error adding person: {e}", exc_info=True)
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - unexpected: {e}')
            return None

    def edit_person(self, person_id: str, updates: Dict[str, Any], edited_by: str = "system") -> bool:
        """
        Edits details of an existing person. (In-memory version)
        """
        person = self.find_person(person_id=person_id)
        if not person:
            logging.warning(f"edit_person: Person with ID {person_id} not found.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - person not found: {person_id}')
            return False

        logging.info(f"Attempting to edit person {person_id} by {edited_by}. Updates: {updates}")
        # Removed unused original_data variable
        updated = False
        validation_errors = {}

        # Validate and apply updates (similar logic as before)
        allowed_fields = list(Person.__annotations__.keys())
        allowed_fields.remove('person_id')

        new_dob_str = updates.get('birth_date', person.birth_date)
        new_dod_str = updates.get('death_date', person.death_date)
        new_dob = None
        new_dod = None

        if 'birth_date' in updates:
            if new_dob_str and not self._is_valid_date(new_dob_str):
                validation_errors['birth_date'] = "Invalid date format (YYYY-MM-DD)."
            elif new_dob_str:
                new_dob = date.fromisoformat(new_dob_str)
        elif person.birth_date: # Get existing date if not updated
            new_dob = date.fromisoformat(person.birth_date)


        if 'death_date' in updates:
            if new_dod_str and not self._is_valid_date(new_dod_str):
                 validation_errors['death_date'] = "Invalid date format (YYYY-MM-DD)."
            elif new_dod_str:
                 new_dod = date.fromisoformat(new_dod_str)
        elif person.death_date: # Get existing date if not updated
             new_dod = date.fromisoformat(person.death_date)

        if new_dob and new_dod and 'birth_date' not in validation_errors and 'death_date' not in validation_errors:
            if new_dod < new_dob:
                validation_errors['date_comparison'] = "Date of Death cannot be before Date of Birth."

        if 'gender' in updates and updates['gender'] and updates['gender'] not in ['Male', 'Female', 'Other']:
             validation_errors['gender'] = "Invalid gender. Use 'Male', 'Female', or 'Other'."

        if validation_errors:
            logging.warning(f"Validation errors editing person {person_id}: {validation_errors}")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: {validation_errors} for {person_id}')
            return False

        # Apply valid updates
        for field, value in updates.items():
            if field in allowed_fields:
                current_value = getattr(person, field)
                new_value = value
                if isinstance(new_value, str):
                    new_value = new_value.strip()
                if field in ['nickname', 'birth_date', 'death_date', 'gender', 'place_of_birth', 'place_of_death', 'notes'] and not new_value:
                    new_value = None

                if current_value != new_value:
                    setattr(person, field, new_value)
                    updated = True
                    logging.debug(f"Updated field '{field}' for person {person_id}")
            elif field == 'attributes' and isinstance(value, dict):
                 if person.attributes != value:
                     person.attributes.update(value)
                     updated = True
                     logging.debug(f"Updated attributes for person {person_id}")
            else:
                 logging.warning(f"edit_person: Ignoring invalid field '{field}' for person {person_id}")

        if updated:
            self.save_tree()
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'success - id: {person_id}')
            logging.info(f"Successfully updated person {person_id}.")
        else:
            logging.info(f"No effective changes made to person {person_id}.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'no change - id: {person_id}')

        return True

    def delete_person(self, person_id: str, deleted_by: str = "system") -> bool:
        """Deletes a person and their relationships. (In-memory version)"""
        if person_id not in self.people:
            logging.warning(f"delete_person: Person with ID {person_id} not found.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'failure - person not found: {person_id}')
            return False

        person_name = self.people[person_id].get_full_name()
        logging.info(f"Attempting to delete person {person_id} ('{person_name}') by {deleted_by}.")

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

        del self.people[person_id]
        self.save_tree()
        log_audit(self.audit_log_path, deleted_by, 'delete_person', f'success - id: {person_id}, name: {person_name}, deleted {deleted_rel_count} relationships')
        logging.info(f"Deleted person {person_id} ('{person_name}') and {deleted_rel_count} relationships.")
        return True

    def find_person(self, person_id: Optional[str] = None, name: Optional[str] = None) -> Optional[Person]:
        """Finds a person by ID or name. (In-memory version)"""
        if person_id:
            return self.people.get(person_id)
        elif name:
            search_name_lower = name.lower()
            for person in self.people.values():
                if (person.first_name and search_name_lower in person.first_name.lower()) or \
                   (person.last_name and search_name_lower in person.last_name.lower()) or \
                   (person.nickname and search_name_lower in person.nickname.lower()):
                    return person
            return None
        else:
            logging.warning("find_person called without person_id or name.")
            return None

    # --- Relationship Management ---

    def add_relationship(self, person1_id: str, person2_id: str, relationship_type: str,
                         attributes: Optional[Dict[str, Any]] = None, added_by: str = "system") -> Optional[Relationship]:
        """Adds a new relationship. (In-memory version)"""
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
        if not relationship_type:
             logging.error("add_relationship: Relationship type cannot be empty.")
             log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - empty relationship type between {person1_id} and {person2_id}')
             return None

        # Check for existing relationship (simple check)
        for rel in self.relationships.values():
            if (rel.person1_id == person1_id and rel.person2_id == person2_id) or \
               (rel.person1_id == person2_id and rel.person2_id == person1_id):
                if rel.rel_type.lower() == relationship_type.lower():
                    logging.warning(f"Relationship '{relationship_type}' already exists between {person1_id} and {person2_id}.")
                    log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - relationship type {relationship_type} already exists between {person1_id} and {person2_id}')
                    return None

        try:
            new_rel = Relationship(
                person1_id=person1_id,
                person2_id=person2_id,
                rel_type=relationship_type,
                attributes=attributes
            )
            # Check for duplicate rel_id before adding
            if new_rel.rel_id in self.relationships:
                raise ValueError(f"Relationship ID {new_rel.rel_id} collision detected.")

            self.relationships[new_rel.rel_id] = new_rel
            self.save_tree()
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'success - id: {new_rel.rel_id}, type: {relationship_type} between {person1_id} and {person2_id}')
            logging.info(f"Added relationship: {new_rel}")
            return new_rel
        except ValueError as ve:
            logging.error(f"Error adding relationship (Validation): {ve}", exc_info=False)
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: {ve}')
            return None
        except Exception as e:
            logging.error(f"Unexpected error adding relationship: {e}", exc_info=True)
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - unexpected: {e}')
            return None

    def edit_relationship(self, relationship_id: str, updates: Dict[str, Any], edited_by: str = "system") -> bool:
        """Edits an existing relationship. (In-memory version)"""
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
        new_attrs = updates.get('attributes')

        if 'rel_type' in updates and (not new_type or not isinstance(new_type, str)):
             validation_errors['rel_type'] = "Relationship type must be a non-empty string."

        if 'person1_id' in updates:
             if not new_p1 or not isinstance(new_p1, str): validation_errors['person1_id'] = "Person 1 ID must be a non-empty string."
             elif new_p1 not in self.people: validation_errors['person1_id'] = f"Person with ID {new_p1} not found."
        if 'person2_id' in updates:
             if not new_p2 or not isinstance(new_p2, str): validation_errors['person2_id'] = "Person 2 ID must be a non-empty string."
             elif new_p2 not in self.people: validation_errors['person2_id'] = f"Person with ID {new_p2} not found."

        if new_p1 == new_p2:
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
            rel.attributes = new_attrs if new_attrs is not None else {}
            updated = True

        if updated:
            self.save_tree()
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'success - id: {relationship_id}')
            logging.info(f"Successfully updated relationship {relationship_id}.")
        else:
            logging.info(f"No effective changes made to relationship {relationship_id}.")
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'no change - id: {relationship_id}')

        return True

    def delete_relationship(self, relationship_id: str, deleted_by: str = "system") -> bool:
        """Deletes a relationship. (In-memory version)"""
        if relationship_id not in self.relationships:
            logging.warning(f"delete_relationship: Relationship with ID {relationship_id} not found.")
            log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'failure - relationship not found: {relationship_id}')
            return False

        rel_info = repr(self.relationships[relationship_id])
        del self.relationships[relationship_id]
        self.save_tree()
        log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'success - id: {relationship_id}, info: {rel_info}')
        logging.info(f"Deleted relationship {relationship_id}.")
        return True

    def find_relationships_for_person(self, person_id: str) -> List[Relationship]:
        """Finds all relationships involving a specific person. (In-memory version)"""
        found_rels = []
        if person_id not in self.people:
            return found_rels # Person doesn't exist
        for rel in self.relationships.values():
            if rel.person1_id == person_id or rel.person2_id == person_id:
                found_rels.append(rel)
        return found_rels

    # --- Data Persistence ---

    def save_tree(self):
        """Saves the current tree state to JSON. (In-memory version)"""
        logging.debug(f"Attempting to save tree to {self.tree_file_path}")
        try:
            tree_data = {
                "people": {pid: person.to_dict() for pid, person in self.people.items()},
                "relationships": {rid: rel.to_dict() for rid, rel in self.relationships.items()}
            }
            save_data(self.tree_file_path, tree_data, is_encrypted=True)
            logging.info(f"Family tree saved successfully to {self.tree_file_path}")
        except Exception as e:
            logging.error(f"Failed to save family tree to {self.tree_file_path}: {e}", exc_info=True)

    def load_tree(self, loaded_by="system"):
        """Loads the tree state from JSON. (In-memory version)"""
        logging.debug(f"Attempting to load tree from {self.tree_file_path}")
        try:
            data = load_data(self.tree_file_path, default=None, is_encrypted=True)

            if data is None or not isinstance(data, dict):
                 logging.warning(f"No valid data loaded from {self.tree_file_path}. Initializing empty tree.")
                 self.people = {}
                 self.relationships = {}
                 return

            loaded_people = {}
            loaded_relationships = {}
            invalid_people_count = 0
            invalid_rel_count = 0

            people_data = data.get("people", {})
            if isinstance(people_data, dict):
                for pid, p_data in people_data.items():
                    try:
                        if isinstance(p_data, dict):
                            loaded_people[pid] = Person.from_dict(p_data)
                        else:
                             logging.warning(f"Invalid data format for person ID {pid}. Skipping.")
                             invalid_people_count += 1
                    except (KeyError, ValueError, TypeError) as e:
                        logging.error(f"Error loading person data for ID {pid}: {e}. Skipping.")
                        invalid_people_count += 1

            relationships_data = data.get("relationships", {})
            if isinstance(relationships_data, dict):
                for rid, r_data in relationships_data.items():
                     try:
                         if isinstance(r_data, dict):
                             p1_id = r_data.get('person1_id')
                             p2_id = r_data.get('person2_id')
                             if p1_id in loaded_people and p2_id in loaded_people:
                                 loaded_relationships[rid] = Relationship.from_dict(r_data)
                             else:
                                 logging.warning(f"Skipping relationship {rid}: Person ID {p1_id or '?'} or {p2_id or '?'} not found/loaded.")
                                 invalid_rel_count += 1
                         else:
                              logging.warning(f"Invalid data format for relationship ID {rid}. Skipping.")
                              invalid_rel_count += 1
                     except (KeyError, ValueError, TypeError) as e:
                         logging.error(f"Error loading relationship data for ID {rid}: {e}. Skipping.")
                         invalid_rel_count += 1

            self.people = loaded_people
            self.relationships = loaded_relationships

            log_msg = f"success - loaded {len(self.people)} people, {len(self.relationships)} relationships."
            if invalid_people_count > 0: log_msg += f" Skipped {invalid_people_count} invalid people entries."
            if invalid_rel_count > 0: log_msg += f" Skipped {invalid_rel_count} invalid relationship entries."
            logging.info(f"Family tree loaded successfully: {len(self.people)} people, {len(self.relationships)} relationships.")
            log_audit(self.audit_log_path, loaded_by, 'load_tree', log_msg)

        except Exception as e:
            log_audit_msg = f'failure: {e}'
            if isinstance(e, RecursionError):
                 logging.error(f"Critical RecursionError loading family tree from {self.tree_file_path}: {e}")
                 log_audit_msg = f'failure: RecursionError - {e}'
            else:
                 logging.error(f"Critical error loading family tree from {self.tree_file_path}: {e}", exc_info=True)

            log_audit(self.audit_log_path, loaded_by, 'load_tree', log_audit_msg)
            self.people = {}
            self.relationships = {}

    # --- Utility Methods ---

    @staticmethod
    def _is_valid_date(date_str: Optional[str]) -> bool:
        """Checks if a string is a valid YYYY-MM-DD date."""
        if not date_str:
            return True
        try:
            date.fromisoformat(date_str)
            return True
        except (ValueError, TypeError):
            return False

    # --- Data for Visualization ---

    def get_nodes_links_data(self, start_node_id: Optional[str] = None, max_depth: Optional[int] = None) -> Dict[str, List[Dict]]:
        """Generates data suitable for graph visualization libraries."""
        nodes_data = []
        links_data = []

        if start_node_id:
             logging.warning("Partial tree loading not fully implemented yet. Returning full tree.")
             people_to_include = self.people
             rels_to_include = self.relationships
        else:
            people_to_include = self.people
            rels_to_include = self.relationships

        # Create nodes
        for person_id, person in people_to_include.items():
            if not isinstance(person, Person): continue
            nodes_data.append({
                "id": person.person_id,
                "type": "personNode",
                "data": {
                    "id": person.person_id,
                    "label": person.get_display_name(),
                    "full_name": person.get_full_name(),
                    "gender": person.gender,
                    "dob": person.birth_date,
                    "dod": person.death_date,
                    "birth_place": person.place_of_birth,
                    "death_place": person.place_of_death,
                    "photoUrl": getattr(person, 'photo_url', None)
                },
                "position": {"x": 0, "y": 0}
            })

        # Create links (edges)
        for rel_id, rel in rels_to_include.items():
            if not isinstance(rel, Relationship): continue
            if rel.person1_id in people_to_include and rel.person2_id in people_to_include:
                links_data.append({
                    "id": rel.rel_id,
                    "source": rel.person1_id,
                    "target": rel.person2_id,
                    "type": "default",
                    "animated": False,
                    "label": rel.rel_type,
                    "data": rel.attributes
                })

        return {"nodes": nodes_data, "links": links_data}

    # --- Deprecated/Internal Helper ---
    @classmethod
    def _from_dict(cls, data: dict, tree_file_path: str, audit_log_path: str) -> 'FamilyTree':
        """(Deprecated) Creates a FamilyTree instance from dictionary data."""
        logging.warning("_from_dict is likely deprecated. Use instance.load_tree() instead.")
        tree = cls(tree_file_path=tree_file_path, audit_log_path=audit_log_path)
        return tree

