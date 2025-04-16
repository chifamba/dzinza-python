# src/family_tree.py
import json
import uuid
import os
from datetime import datetime # Import datetime for date validation
from .person import Person
# Import Relationship class and VALID_RELATIONSHIP_TYPES
from .relationship import Relationship, VALID_RELATIONSHIP_TYPES
from .db_utils import load_data, save_data
from .audit_log import log_audit

class FamilyTree:
    def __init__(self, tree_file_path='data/family_tree.json', audit_log_path='data/audit.log'):
        self.people = {}
        self.relationships = {} # Stores relationships by unique ID: {rel_id: Relationship}
        self.tree_file_path = tree_file_path
        self.audit_log_path = audit_log_path
        tree_dir = os.path.dirname(tree_file_path)
        if tree_dir:
             os.makedirs(tree_dir, exist_ok=True)

    # --- Validation Helper ---
    def _is_valid_date(self, date_str):
        """Checks if a string is a valid YYYY-MM-DD date."""
        if not date_str:
            return True # Allow empty dates (optional)
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    # --- Person Methods ---
    def add_person(self, first_name, last_name, nickname=None, dob=None, dod=None, gender=None, added_by="system", **kwargs):
        # --- Validation ---
        if not first_name:
            print("Validation Error: Person's first name cannot be empty.")
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: empty first name')
            return None
        if dob and not self._is_valid_date(dob):
            print(f"Validation Error: Invalid Date of Birth format '{dob}'. Use YYYY-MM-DD.")
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: invalid dob format')
            return None
        if dod and not self._is_valid_date(dod):
            print(f"Validation Error: Invalid Date of Death format '{dod}'. Use YYYY-MM-DD.")
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: invalid dod format')
            return None
        if dob and dod:
            try:
                birth_date = datetime.strptime(dob, '%Y-%m-%d').date()
                death_date = datetime.strptime(dod, '%Y-%m-%d').date()
                if death_date < birth_date:
                    print(f"Validation Error: Date of Death ({dod}) cannot be before Date of Birth ({dob}).")
                    log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: dod before dob')
                    return None
            except ValueError: # Should be caught by _is_valid_date, but belt-and-suspenders
                 pass
        # --- End Validation ---

        person_id = str(uuid.uuid4())
        try:
            person = Person(
                person_id=person_id, first_name=first_name.strip(),
                last_name=last_name.strip() if last_name else "",
                nickname=nickname.strip() if nickname else None,
                birth_date=dob if dob else None, death_date=dod if dod else None,
                gender=gender if gender else None, attributes=kwargs
            )
        except Exception as e: print(f"Error creating Person object: {e}"); log_audit(self.audit_log_path, added_by, 'add_person', f'failure - error creating person object: {e}'); return None
        self.people[person_id] = person
        display_name = person.get_display_name(); full_name = person.get_full_name()
        print(f"Person added: {display_name} (ID: {person.person_id})")
        log_audit(self.audit_log_path, added_by, 'add_person', f'success - id: {person.person_id}, name: {full_name}')
        self.save_tree(added_by); return person

    def edit_person(self, person_id, updated_data, edited_by="system"):
        person = self.find_person(person_id=person_id)
        if not person:
             print(f"Error: Person with ID {person_id} not found for editing.")
             log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - person not found: {person_id}'); return False

        # --- Validation ---
        new_first_name = updated_data.get('first_name', person.first_name)
        new_dob = updated_data.get('birth_date', person.birth_date)
        new_dod = updated_data.get('death_date', person.death_date)

        if not new_first_name or not new_first_name.strip(): # Check if None or empty after stripping
             print(f"Validation Error: First name cannot be empty for person {person_id}.")
             log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: empty first name for id {person_id}')
             return False # Indicate failure
        if new_dob and not self._is_valid_date(new_dob):
            print(f"Validation Error: Invalid Date of Birth format '{new_dob}' for person {person_id}.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: invalid dob format for id {person_id}')
            return False
        if new_dod and not self._is_valid_date(new_dod):
             print(f"Validation Error: Invalid Date of Death format '{new_dod}' for person {person_id}.")
             log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: invalid dod format for id {person_id}')
             return False
        if new_dob and new_dod:
            try:
                birth_date = datetime.strptime(new_dob, '%Y-%m-%d').date()
                death_date = datetime.strptime(new_dod, '%Y-%m-%d').date()
                if death_date < birth_date:
                    print(f"Validation Error: Date of Death ({new_dod}) cannot be before Date of Birth ({new_dob}) for person {person_id}.")
                    log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: dod before dob for id {person_id}')
                    return False
            except ValueError: pass
        # --- End Validation ---

        original_display_name = person.get_display_name(); changes_made = False
        for key, value in updated_data.items():
            if hasattr(person, key):
                current_value = getattr(person, key); new_value = value.strip() if isinstance(value, str) else value
                if key in ['nickname', 'birth_date', 'death_date', 'gender', 'notes'] and not new_value: new_value = None
                elif key == 'last_name' and not new_value: new_value = "" # Allow empty last name
                # Don't allow empty first name (already validated above)
                if current_value != new_value: setattr(person, key, new_value); changes_made = True
            else: print(f"Warning: Attempted to update non-existent attribute '{key}' for person {person_id}")

        if changes_made: log_audit(self.audit_log_path, edited_by, 'edit_person', f'success - id: {person_id}, name: {original_display_name} -> {person.get_display_name()}'); self.save_tree(edited_by); return True
        else: log_audit(self.audit_log_path, edited_by, 'edit_person', f'no changes made for id: {person_id}'); return False


    def delete_person(self, person_id, deleted_by="system"):
        # (Keep implementation from family_tree_py_init_fix)
        person = self.find_person(person_id=person_id)
        if person:
            person_display_name = person.get_display_name(); del self.people[person_id]
            rels_to_delete = [rid for rid, rel in self.relationships.items() if rel.person1_id == person_id or rel.person2_id == person_id]
            num_rels_deleted = len(rels_to_delete)
            for rid in rels_to_delete: del self.relationships[rid]
            print(f"Person '{person_display_name}' (ID: {person_id}) and {num_rels_deleted} related relationships deleted.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'success - id: {person_id}, name: {person_display_name}, removed {num_rels_deleted} relationships')
            self.save_tree(deleted_by); return True
        else: print(f"Error: Person with ID {person_id} not found for deletion."); log_audit(self.audit_log_path, deleted_by, 'delete_person', f'failure - person not found: {person_id}'); return False

    # --- Relationship Methods ---
    def add_relationship(self, person1_id, person2_id, relationship_type, added_by="system"):
        # --- Validation ---
        if not person1_id or not person2_id:
             print("Validation Error: Both Person 1 and Person 2 must be selected.")
             log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: missing person id')
             return None
        if person1_id == person2_id:
            print("Validation Error: Cannot add a relationship between a person and themselves.")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: self relationship ({person1_id})')
            return None
        if not relationship_type or relationship_type.strip() == "":
             print("Validation Error: Relationship type cannot be empty.")
             log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: empty relationship type')
             return None
        # Optional: Validate against known types
        # if relationship_type not in VALID_RELATIONSHIP_TYPES:
        #     print(f"Validation Warning: Unknown relationship type '{relationship_type}'.")
        #     # Decide whether to allow or reject unknown types
        person1 = self.people.get(person1_id)
        person2 = self.people.get(person2_id)
        if not person1 or not person2:
            missing_ids = []
            if not person1: missing_ids.append(person1_id)
            if not person2: missing_ids.append(person2_id)
            print(f"Error: One or both persons (ID(s): {', '.join(missing_ids)}) not found.")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - person not found ({", ".join(missing_ids)})'); return None
        # Check for duplicate relationship (same people, same type)
        for rel in self.relationships.values():
            if (rel.person1_id == person1_id and rel.person2_id == person2_id and rel.rel_type == relationship_type) or \
               (rel.person1_id == person2_id and rel.person2_id == person1_id and rel.rel_type == relationship_type): # Check reciprocal too for symmetric types like spouse
                print(f"Validation Error: Relationship ({relationship_type}) already exists between {person1_id} and {person2_id}.")
                log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: duplicate relationship')
                return None
        # --- End Validation ---

        relationship_id = str(uuid.uuid4())
        try:
            relationship = Relationship(person1_id=person1_id, person2_id=person2_id, rel_type=relationship_type)
            self.relationships[relationship_id] = relationship
            print(f"Relationship added: {person1.get_display_name()} - {relationship_type} - {person2.get_display_name()}")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'success - id: {relationship_id}, type: {relationship_type}, persons: ({person1_id}, {person2_id})')
            self.save_tree(added_by); return relationship
        except Exception as e: print(f"Error creating Relationship object: {e}"); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - error creating relationship object: {e}'); return None

    # --- NEW: Edit Relationship Method ---
    def edit_relationship(self, relationship_id, updated_data, edited_by="system"):
        """
        Edits an existing relationship. Currently only supports changing the type.

        Args:
            relationship_id (str): The unique ID of the relationship to edit.
            updated_data (dict): Dictionary containing updates (e.g., {'rel_type': 'new_type'}).
            edited_by (str): Username of the user performing the edit.

        Returns:
            bool: True if successful, False otherwise.
        """
        if relationship_id not in self.relationships:
            print(f"Error: Relationship with ID {relationship_id} not found for editing.")
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'failure - relationship not found: {relationship_id}')
            return False

        relationship = self.relationships[relationship_id]
        original_type = relationship.rel_type
        new_type = updated_data.get('rel_type', original_type).strip()

        # --- Validation ---
        if not new_type:
            print(f"Validation Error: Relationship type cannot be empty for {relationship_id}.")
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'failure - validation: empty type for id {relationship_id}')
            return False
        # Optional: Validate new_type against VALID_RELATIONSHIP_TYPES
        # if new_type not in VALID_RELATIONSHIP_TYPES:
        #     print(f"Validation Warning: Unknown relationship type '{new_type}' for {relationship_id}.")
        # --- End Validation ---

        if new_type != original_type:
            relationship.rel_type = new_type
            # TODO: Handle reciprocal relationship updates if necessary (e.g., if changing parent to something else)
            # This requires more complex logic based on relationship types.
            p1_name = self.people.get(relationship.person1_id, Person(person_id=relationship.person1_id)).get_display_name()
            p2_name = self.people.get(relationship.person2_id, Person(person_id=relationship.person2_id)).get_display_name()
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'success - id: {relationship_id}, type: {original_type} -> {new_type}, persons: ({p1_name}, {p2_name})')
            self.save_tree(edited_by)
            return True
        else:
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'no changes made for id: {relationship_id}')
            return False # No changes made

    # --- NEW: Delete Relationship Method ---
    def delete_relationship(self, relationship_id, deleted_by="system"):
        """
        Deletes a relationship by its unique ID.

        Args:
            relationship_id (str): The unique ID of the relationship to delete.
            deleted_by (str): Username of the user performing the deletion.

        Returns:
            bool: True if successful, False otherwise.
        """
        if relationship_id in self.relationships:
            relationship = self.relationships[relationship_id]
            p1_name = self.people.get(relationship.person1_id, Person(person_id=relationship.person1_id)).get_display_name()
            p2_name = self.people.get(relationship.person2_id, Person(person_id=relationship.person2_id)).get_display_name()
            rel_type = relationship.rel_type

            del self.relationships[relationship_id]
            # TODO: Handle reciprocal relationship deletion if necessary.

            print(f"Relationship ({rel_type}) between {p1_name} and {p2_name} deleted.")
            log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'success - id: {relationship_id}, type: {rel_type}, persons: ({p1_name}, {p2_name})')
            self.save_tree(deleted_by)
            return True
        else:
            print(f"Error: Relationship with ID {relationship_id} not found for deletion.")
            log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'failure - relationship not found: {relationship_id}')
            return False

    # --- Keep find_person, search_people, get_summaries, get_nodes_links, _to_dict, _from_dict, save/load ---
    def find_person(self, name=None, person_id=None):
        # (Keep implementation)
        if person_id: return self.people.get(person_id)
        if name:
            search_name_lower = name.lower()
            for person in self.people.values():
                if person.get_full_name().lower() == search_name_lower: return person
        return None

    def search_people(self, query):
        # (Keep implementation)
        if not query: return []
        results = []; search_term = query.lower().strip()
        for person in self.people.values():
            match = False
            if person.first_name and search_term in person.first_name.lower(): match = True
            if not match and person.last_name and search_term in person.last_name.lower(): match = True
            if not match and person.nickname and search_term in person.nickname.lower(): match = True
            if match: results.append(person)
        results.sort(key=lambda p: p.get_full_name()); return results

    def get_people_summary(self):
        # (Keep implementation)
        summary_list = []
        for p in self.people.values():
             full_name = p.get_full_name(); display_name = p.get_display_name()
             summary_list.append({"person_id": p.person_id, "name": full_name, "display_name": display_name, "nickname": p.nickname, "dob": p.birth_date, "dod": p.death_date, "gender": p.gender})
        return sorted(summary_list, key=lambda x: x['name'])

    def get_relationships_summary(self):
        # (Keep implementation)
        summary = []
        for rel_id, rel in self.relationships.items():
            person1 = self.people.get(rel.person1_id); person2 = self.people.get(rel.person2_id)
            person1_display_name = person1.get_display_name() if person1 else f"Unknown (ID: {rel.person1_id[:8]}...)"
            person2_display_name = person2.get_display_name() if person2 else f"Unknown (ID: {rel.person2_id[:8]}...)"
            person1_sort_name = person1.get_full_name() if person1 else "Unknown"
            summary.append({"relationship_id": rel_id, "person1_id": rel.person1_id, "person1_name": person1_display_name, "person2_id": rel.person2_id, "person2_name": person2_display_name, "relationship_type": rel.rel_type, "_person1_sort_name": person1_sort_name})
        return sorted(summary, key=lambda x: (x['relationship_type'], x['_person1_sort_name']))

    def get_nodes_links_data(self):
        # (Keep implementation)
        nodes = []; links = []; person_ids = list(self.people.keys())
        for person_id in person_ids:
            person = self.people[person_id]
            nodes.append({"id": person.person_id, "name": person.get_display_name(), "full_name": person.get_full_name(), "gender": person.gender, "dob": person.birth_date})
        processed_rel_ids = set()
        for rel_id, rel in self.relationships.items():
            if rel_id in processed_rel_ids: continue
            source_id = rel.person1_id; target_id = rel.person2_id; rel_type = rel.rel_type.lower()
            if source_id not in self.people or target_id not in self.people: print(f"Warning: Skipping relationship {rel_id} because person {source_id} or {target_id} not found."); continue
            link_data = None
            if rel_type == 'parent': link_data = {"source": source_id, "target": target_id, "type": "parent_child"}
            elif rel_type == 'child': link_data = {"source": target_id, "target": source_id, "type": "parent_child"}
            elif rel_type == 'spouse' or rel_type == 'partner':
                 link_data = {"source": source_id, "target": target_id, "type": rel_type}
                 reciprocal_rel = next((r_id for r_id, r in self.relationships.items() if r.person1_id == target_id and r.person2_id == source_id and r.rel_type.lower() == rel_type), None) # Get ID
                 if reciprocal_rel: processed_rel_ids.add(reciprocal_rel)
            else: link_data = {"source": source_id, "target": target_id, "type": rel_type}
            if link_data: links.append(link_data)
            processed_rel_ids.add(rel_id)
        return {"nodes": nodes, "links": links}

    def _to_dict(self):
        return {"people": {pid: person.to_dict() for pid, person in self.people.items()}, "relationships": {rid: rel.to_dict() for rid, rel in self.relationships.items()}}
    @classmethod
    def _from_dict(cls, data, tree_file_path, audit_log_path):
        tree = cls(tree_file_path, audit_log_path); tree.people = {}; tree.relationships = {}
        for pid, pdata in data.get("people", {}).items():
             try: tree.people[pid] = Person.from_dict(pdata)
             except Exception as e: print(f"Warning: Skipping invalid person data for ID {pid} during load: {e}")
        for rid, rdata in data.get("relationships", {}).items():
             try: tree.relationships[rid] = Relationship.from_dict(rdata)
             except Exception as e: print(f"Warning: Skipping invalid relationship data for ID {rid} during load: {e}")
        return tree
    def save_tree(self, saved_by="system"):
        try: data_to_save = self._to_dict(); save_data(self.tree_file_path, data_to_save); # print(f"Family tree saved successfully to {self.tree_file_path}") # Reduce noise
        except Exception as e: print(f"Error saving family tree to {self.tree_file_path}: {e}"); log_audit(self.audit_log_path, saved_by, 'save_tree', f'failure: {e}')
    def load_tree(self, loaded_by="system"):
        try:
            data = load_data(self.tree_file_path)
            if data: loaded_tree = self._from_dict(data, self.tree_file_path, self.audit_log_path); self.people = loaded_tree.people; self.relationships = loaded_tree.relationships; print(f"Family tree loaded successfully from {self.tree_file_path}. Found {len(self.people)} people and {len(self.relationships)} relationships.")
            else: print(f"No existing data found or error loading from {self.tree_file_path}. Starting with an empty tree."); self.people = {}; self.relationships = {}
        except FileNotFoundError: print(f"Tree file {self.tree_file_path} not found. Starting with an empty tree."); self.people = {}; self.relationships = {}
        except Exception as e: print(f"An unexpected error occurred loading the tree from {self.tree_file_path}: {e}"); log_audit(self.audit_log_path, loaded_by, 'load_tree', f'failure: {e}'); self.people = {}; self.relationships = {}

