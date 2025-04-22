# backend/src/family_tree.py
import json
import uuid
import logging
import os
from datetime import datetime, date
from collections import deque # Needed for BFS

from .person import Person
from .relationship import Relationship, VALID_RELATIONSHIP_TYPES
from .db_utils import load_data, save_data
from .audit_log import log_audit
from .photo_utils import generate_default_person_photo

class FamilyTree:
    """
    Manages the collection of Person and Relationship objects,
    handling loading, saving, and basic operations.
    """
    def __init__(self, tree_file_path=None, audit_log_path=None):
        """
        Initializes the FamilyTree.

        Args:
            tree_file_path (str, optional): Path to the family tree data file.
                                            Defaults to 'data/family_tree.json' in the backend directory.
            audit_log_path (str, optional): Path to the audit log file.
                                            Defaults to 'audit.log' in the backend directory.
        """
        self.people: dict[str, Person] = {}
        self.relationships: dict[str, Relationship] = {}
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        default_tree_file = os.path.join(backend_dir, 'data', 'family_tree.json')
        default_audit_log = os.path.join(backend_dir, 'audit.log') # Keep audit log path simple for now

        self.tree_file_path = tree_file_path if tree_file_path else default_tree_file
        self.audit_log_path = audit_log_path if audit_log_path else default_audit_log

        tree_dir = os.path.dirname(self.tree_file_path)
        if tree_dir:
            os.makedirs(tree_dir, exist_ok=True)
        logging.info(f"FamilyTree initialized. Data file: {self.tree_file_path}, Audit log: {self.audit_log_path}")
        # Load tree on initialization
        self.load_tree()

    # --- Validation Helper ---
    @staticmethod
    def _is_valid_date(date_str):
        """Checks if a string is a valid YYYY-MM-DD date."""
        if not date_str:
            return True # Allow empty dates
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except (ValueError, TypeError):
            return False

    # --- Person Methods (add_person, edit_person, delete_person remain the same) ---
    def add_person(self, first_name, last_name, nickname=None, dob=None, dod=None, pob=None, pod=None, gender=None, notes=None, added_by="system", **kwargs):
        """Adds a new person to the family tree."""
        # --- Validation ---
        if not first_name or not str(first_name).strip():
            logging.error("add_person validation failed: First name cannot be empty.")
            log_audit(self.audit_log_path, added_by, 'add_person', 'failure - validation: empty first name')
            return None
        if dob and not self._is_valid_date(dob):
            logging.error(f"add_person validation failed: Invalid DOB format '{dob}'. Use YYYY-MM-DD.")
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: invalid dob format ({dob})')
            return None
        if dod and not self._is_valid_date(dod):
            logging.error(f"add_person validation failed: Invalid DOD format '{dod}'. Use YYYY-MM-DD.")
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: invalid dod format ({dod})')
            return None
        if dob and dod:
            try:
                if date.fromisoformat(dod) < date.fromisoformat(dob):
                    logging.error(f"add_person validation failed: DOD ({dod}) cannot be before DOB ({dob}).")
                    log_audit(self.audit_log_path, added_by, 'add_person', 'failure - validation: dod before dob')
                    return None
            except (ValueError, TypeError):
                logging.warning(f"Could not compare DOB/DOD for validation: {dob}, {dod}", exc_info=True)
        if gender and gender not in ['Male', 'Female', 'Other']:
            logging.warning(f"add_person: Invalid gender '{gender}' provided. Setting to None.")
            gender = None

        person_id = str(uuid.uuid4())
        try:
            person = Person(
                person_id=person_id, first_name=str(first_name).strip(),
                last_name=str(last_name).strip() if last_name else "",
                nickname=str(nickname).strip() if nickname else None,
                birth_date=dob if dob else None, death_date=dod if dod else None,
                place_of_birth=str(pob).strip() if pob else None,
                place_of_death=str(pod).strip() if pod else None,
                gender=gender, notes=str(notes).strip() if notes else None, attributes=kwargs
            )
            person.photo_url = generate_default_person_photo(person.person_id)
        except Exception as e:
            logging.error(f"Error creating Person object: {e}", exc_info=True)
            log_audit(self.audit_log_path, added_by, 'add_person', f'failure - error creating person object: {e}')
            return None

        self.people[person_id] = person
        display_name = person.get_display_name(); full_name = person.get_full_name()
        logging.info(f"Person added: {display_name} (ID: {person.person_id})")
        log_audit(self.audit_log_path, added_by, 'add_person', f'success - id: {person.person_id}, name: {full_name}')
        self.save_tree(added_by); return person

    def edit_person(self, person_id, updated_data, edited_by="system"):
        """Edits an existing person's details."""
        person = self.find_person(person_id=person_id)
        if not person:
            logging.error(f"edit_person failed: Person {person_id} not found.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - person not found: {person_id}')
            return False

        # --- Validation (as before) ---
        new_first_name = updated_data.get('first_name', person.first_name)
        new_dob = updated_data.get('birth_date', person.birth_date)
        new_dod = updated_data.get('death_date', person.death_date)
        new_gender = updated_data.get('gender', person.gender)
        if 'first_name' in updated_data and (not new_first_name or not str(new_first_name).strip()):
            logging.error(f"edit_person validation failed for {person_id}: First name cannot be empty.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: empty first name for id {person_id}')
            return False
        if 'birth_date' in updated_data and new_dob and not self._is_valid_date(new_dob):
            logging.error(f"edit_person validation failed for {person_id}: Invalid DOB format '{new_dob}'.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: invalid dob format ({new_dob}) for id {person_id}')
            return False
        if 'death_date' in updated_data and new_dod and not self._is_valid_date(new_dod):
            logging.error(f"edit_person validation failed for {person_id}: Invalid DOD format '{new_dod}'.")
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: invalid dod format ({new_dod}) for id {person_id}')
            return False
        current_dob_for_check = new_dob if 'birth_date' in updated_data else person.birth_date
        current_dod_for_check = new_dod if 'death_date' in updated_data else person.death_date
        if current_dob_for_check and current_dod_for_check:
            try:
                if date.fromisoformat(current_dod_for_check) < date.fromisoformat(current_dob_for_check):
                    logging.error(f"edit_person validation failed for {person_id}: DOD ({current_dod_for_check}) cannot be before DOB ({current_dob_for_check}).")
                    log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: dod before dob for id {person_id}')
                    return False
            except (ValueError, TypeError):
                 logging.warning(f"Could not compare DOB/DOD during edit validation: {current_dob_for_check}, {current_dod_for_check}", exc_info=True)
        if 'gender' in updated_data and new_gender and new_gender not in ['Male', 'Female', 'Other']:
             logging.warning(f"edit_person: Invalid gender '{new_gender}' provided for {person_id}. Ignoring gender update.")
             updated_data.pop('gender', None)

        # --- Apply Changes (as before) ---
        original_display_name = person.get_display_name(); changes_made = False
        allowed_fields = ['first_name', 'last_name', 'nickname', 'birth_date', 'death_date', 'gender', 'place_of_birth', 'place_of_death', 'notes']
        for key, value in updated_data.items():
            if key in allowed_fields:
                current_value = getattr(person, key)
                if isinstance(value, str): new_value = value.strip()
                else: new_value = value
                if key != 'last_name' and new_value == '': new_value = None
                elif key == 'last_name' and new_value is None: new_value = ""
                if current_value != new_value: setattr(person, key, new_value); changes_made = True; logging.debug(f"Updated {key} for {person_id} from '{current_value}' to '{new_value}'")
            elif key == 'attributes' and isinstance(value, dict): person.attributes.update(value); changes_made = True; logging.debug(f"Updated attributes for {person_id}")
            else: logging.warning(f"edit_person: Attempted to update disallowed or unknown attribute '{key}' for person {person_id}. Ignoring.")

        if changes_made:
            person.photo_url = generate_default_person_photo(person.person_id)
            log_audit(self.audit_log_path, edited_by, 'edit_person', f'success - id: {person_id}, name: {original_display_name} -> {person.get_display_name()}')
            self.save_tree(edited_by); return True
        else: log_audit(self.audit_log_path, edited_by, 'edit_person', f'no changes detected for id: {person_id}'); return False

    def delete_person(self, person_id, deleted_by="system"):
        """Deletes a person and all their associated relationships."""
        person = self.find_person(person_id=person_id)
        if person:
            person_display_name = person.get_display_name(); del self.people[person_id]
            rels_to_delete = [rid for rid, rel in self.relationships.items() if rel.person1_id == person_id or rel.person2_id == person_id]
            num_rels_deleted = len(rels_to_delete)
            for rid in rels_to_delete: del self.relationships[rid]
            logging.info(f"Person '{person_display_name}' (ID: {person_id}) and {num_rels_deleted} related relationships deleted.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'success - id: {person_id}, name: {person_display_name}, removed {num_rels_deleted} relationships')
            self.save_tree(deleted_by); return True
        else: logging.error(f"delete_person failed: Person with ID {person_id} not found."); log_audit(self.audit_log_path, deleted_by, 'delete_person', f'failure - person not found: {person_id}'); return False

    # --- Relationship Methods (add_relationship, edit_relationship, delete_relationship remain the same) ---
    def add_relationship(self, person1_id, person2_id, relationship_type, added_by="system", attributes=None):
        """Adds a new relationship between two people."""
        # --- Validation ---
        if not person1_id or not person2_id: logging.error("add_relationship validation failed: Both Person 1 and Person 2 IDs are required."); log_audit(self.audit_log_path, added_by, 'add_relationship', 'failure - validation: missing person id'); return None
        if person1_id == person2_id: logging.error("add_relationship validation failed: Cannot add a relationship between a person and themselves."); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: self relationship ({person1_id})'); return None
        if not relationship_type or not str(relationship_type).strip(): logging.error("add_relationship validation failed: Relationship type cannot be empty."); log_audit(self.audit_log_path, added_by, 'add_relationship', 'failure - validation: empty relationship type'); return None
        if relationship_type not in VALID_RELATIONSHIP_TYPES: logging.warning(f"add_relationship: Adding relationship with potentially invalid type: '{relationship_type}'. Valid types: {VALID_RELATIONSHIP_TYPES}")
        person1 = self.people.get(person1_id); person2 = self.people.get(person2_id)
        if not person1 or not person2:
            missing_ids = [];
            if not person1: missing_ids.append(person1_id)
            if not person2: missing_ids.append(person2_id)
            logging.error(f"add_relationship failed: One or both persons (ID(s): {', '.join(missing_ids)}) not found."); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - person not found ({", ".join(missing_ids)})'); return None
        for rel in self.relationships.values():
            match1 = (rel.person1_id == person1_id and rel.person2_id == person2_id and rel.rel_type == relationship_type)
            match2 = (rel.person1_id == person2_id and rel.person2_id == person1_id and rel.rel_type == relationship_type)
            if match1 or match2: logging.error(f"add_relationship validation failed: Relationship ({relationship_type}) already exists between {person1_id} and {person2_id}."); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: duplicate relationship ({relationship_type}) between {person1_id}, {person2_id}'); return None

        relationship_id = str(uuid.uuid4())
        try:
            relationship = Relationship( rel_id=relationship_id, person1_id=person1_id, person2_id=person2_id, rel_type=str(relationship_type).strip(), attributes=attributes if attributes else {})
            self.relationships[relationship_id] = relationship
            p1_name = person1.get_display_name(); p2_name = person2.get_display_name()
            logging.info(f"Relationship added: {p1_name} - {relationship_type} - {p2_name} (ID: {relationship_id})")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'success - id: {relationship_id}, type: {relationship_type}, persons: ({person1_id}, {person2_id})')
            self.save_tree(added_by); return relationship
        except Exception as e: logging.error(f"Error creating Relationship object: {e}", exc_info=True); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - error creating relationship object: {e}'); return None

    def edit_relationship(self, relationship_id, updated_data, edited_by="system"):
        """Edits an existing relationship's type or attributes."""
        if relationship_id not in self.relationships: logging.error(f"edit_relationship failed: Relationship {relationship_id} not found."); log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'failure - relationship not found: {relationship_id}'); return False
        relationship = self.relationships[relationship_id]; original_type = relationship.rel_type; original_attributes = relationship.attributes.copy(); changes_made = False
        if 'rel_type' in updated_data:
            new_type = updated_data['rel_type']
            if not new_type or not str(new_type).strip(): logging.error(f"edit_relationship validation failed for {relationship_id}: Relationship type cannot be empty."); log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'failure - validation: empty type for id {relationship_id}'); return False
            if new_type not in VALID_RELATIONSHIP_TYPES: logging.warning(f"edit_relationship: Attempting to set potentially invalid relationship type '{new_type}' for {relationship_id}.")
            if relationship.rel_type != new_type: relationship.rel_type = str(new_type).strip(); changes_made = True
        if 'attributes' in updated_data and isinstance(updated_data['attributes'], dict):
            relationship.attributes.update(updated_data['attributes'])
            if original_attributes != relationship.attributes: changes_made = True
        if changes_made:
            p1 = self.people.get(relationship.person1_id); p2 = self.people.get(relationship.person2_id)
            p1_name = p1.get_display_name() if p1 else f"ID:{relationship.person1_id}"; p2_name = p2.get_display_name() if p2 else f"ID:{relationship.person2_id}"
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'success - id: {relationship_id}, type: {original_type} -> {relationship.rel_type}, persons: ({p1_name}, {p2_name}), attrs changed: {original_attributes != relationship.attributes}')
            self.save_tree(edited_by); return True
        else: log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'no changes detected for id: {relationship_id}'); return False

    def delete_relationship(self, relationship_id, deleted_by="system"):
        """Deletes a relationship by its ID."""
        if relationship_id in self.relationships:
            relationship = self.relationships[relationship_id]
            p1 = self.people.get(relationship.person1_id); p2 = self.people.get(relationship.person2_id)
            p1_name = p1.get_display_name() if p1 else f"ID:{relationship.person1_id}"; p2_name = p2.get_display_name() if p2 else f"ID:{relationship.person2_id}"
            rel_type = relationship.rel_type; del self.relationships[relationship_id]
            logging.info(f"Relationship (ID: {relationship_id}, Type: {rel_type}) between {p1_name} and {p2_name} deleted.")
            log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'success - id: {relationship_id}, type: {rel_type}, persons: ({p1_name}, {p2_name})')
            self.save_tree(deleted_by); return True
        else: logging.error(f"delete_relationship failed: Relationship {relationship_id} not found."); log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'failure - relationship not found: {relationship_id}'); return False

    # --- Search and Retrieval Methods (find_person, search_people, find_relationships_for_person, find_parents, find_children, find_siblings remain the same) ---
    def find_person(self, name=None, person_id=None):
        """Finds a person by ID or exact full name match."""
        if person_id: return self.people.get(person_id)
        if name:
            search_name_lower = name.lower().strip()
            for person in self.people.values():
                if person.get_full_name().lower() == search_name_lower: return person
        return None

    def search_people(self, query=None, dob_start=None, dob_end=None, location=None):
        """Searches people by name/nickname, DOB range, and/or location (birth/death place)."""
        results = []; search_term = query.lower().strip() if query else None; location_term = location.lower().strip() if location else None
        start_date_obj, end_date_obj = None, None
        try:
            if dob_start and self._is_valid_date(dob_start): start_date_obj = date.fromisoformat(dob_start)
            elif dob_start: logging.warning(f"search_people: Invalid start date format '{dob_start}' ignored.")
            if dob_end and self._is_valid_date(dob_end): end_date_obj = date.fromisoformat(dob_end);
            elif dob_end: logging.warning(f"search_people: Invalid end date format '{dob_end}' ignored.")
        except ValueError as e: logging.error(f"Error parsing search dates: {e}", exc_info=True); return []

        for person in self.people.values():
            match = True
            if search_term:
                name_match = False
                if person.first_name and search_term in person.first_name.lower(): name_match = True
                if not name_match and person.last_name and search_term in person.last_name.lower(): name_match = True
                if not name_match and person.nickname and search_term in person.nickname.lower(): name_match = True
                if not name_match: match = False
            if match and (start_date_obj or end_date_obj):
                date_match = False
                if person.birth_date and self._is_valid_date(person.birth_date):
                    try:
                        person_dob = date.fromisoformat(person.birth_date); dob_in_range = True
                        if start_date_obj and person_dob < start_date_obj: dob_in_range = False
                        if end_date_obj and person_dob > end_date_obj: dob_in_range = False
                        if dob_in_range: date_match = True
                    except ValueError: pass
                if not date_match: match = False
            if match and location_term:
                location_match = False
                if person.place_of_birth and location_term in person.place_of_birth.lower(): location_match = True
                if not location_match and person.place_of_death and location_term in person.place_of_death.lower(): location_match = True
                if not location_match: match = False
            if match: results.append(person)
        results.sort(key=lambda p: p.get_full_name()); logging.info(f"Search found {len(results)} people for query='{query}', dob='{dob_start}-{dob_end}', location='{location}'"); return results

    def find_relationships_for_person(self, person_id):
        """Finds all relationships involving a specific person."""
        return [rel for rel in self.relationships.values() if rel.person1_id == person_id or rel.person2_id == person_id]

    def find_parents(self, person_id):
        """Finds the parent(s) of a given person."""
        parent_ids = []
        for rel in self.relationships.values():
            if rel.person1_id == person_id and rel.rel_type.lower() == 'child': parent_ids.append(rel.person2_id)
            elif rel.person2_id == person_id and rel.rel_type.lower() == 'parent': parent_ids.append(rel.person1_id)
        return parent_ids

    def find_children(self, person_id):
        """Finds the children of a given person."""
        child_ids = []
        for rel in self.relationships.values():
            if rel.person1_id == person_id and rel.rel_type.lower() == 'parent': child_ids.append(rel.person2_id)
            elif rel.person2_id == person_id and rel.rel_type.lower() == 'child': child_ids.append(rel.person1_id)
        return child_ids

    def find_siblings(self, person_id):
        """Finds the siblings of a given person (sharing at least one parent)."""
        if person_id not in self.people: return []
        parent_ids = self.find_parents(person_id);
        if not parent_ids: return []
        siblings = set()
        for parent_id in parent_ids:
            children_of_parent = self.find_children(parent_id)
            for child_id in children_of_parent:
                if child_id != person_id: siblings.add(child_id)
        return list(siblings)

    # --- Data Summaries & Export (get_people_summary, get_relationships_summary remain the same) ---
    def get_people_summary(self):
        """Returns a list of dictionaries summarizing each person."""
        summary_list = []
        for p in self.people.values():
            summary_list.append({
                "person_id": p.person_id, "name": p.get_full_name(), "display_name": p.get_display_name(),
                "nickname": p.nickname, "dob": p.birth_date, "dod": p.death_date, "gender": p.gender,
                "pob": p.place_of_birth, "pod": p.place_of_death,
                "photo_url": getattr(p, 'photo_url', generate_default_person_photo(p.person_id))
            })
        return sorted(summary_list, key=lambda x: x.get('name', ''))

    def get_relationships_summary(self):
        """Returns a list of dictionaries summarizing each relationship."""
        summary = []
        for rel_id, rel in self.relationships.items():
            person1 = self.people.get(rel.person1_id); person2 = self.people.get(rel.person2_id)
            person1_display_name = person1.get_display_name() if person1 else f"Unknown (ID: {rel.person1_id[:8]}...)"
            person2_display_name = person2.get_display_name() if person2 else f"Unknown (ID: {rel.person2_id[:8]}...)"
            person1_sort_name = person1.get_full_name() if person1 else "Unknown"
            summary.append({
                "relationship_id": rel_id, "person1_id": rel.person1_id, "person1_name": person1_display_name,
                "person2_id": rel.person2_id, "person2_name": person2_display_name,
                "relationship_type": rel.rel_type, "attributes": rel.attributes, "_person1_sort_name": person1_sort_name
            })
        return sorted(summary, key=lambda x: (x.get('relationship_type', ''), x.get('_person1_sort_name', '')))


    # --- UPDATED Tree Visualization Data Method ---
    def get_nodes_links_data(self, start_node_id=None, max_depth=None):
        """
        Generates data suitable for graph visualization libraries like React Flow.
        Can optionally return a subset of the tree starting from a specific node up to a max depth.

        Args:
            start_node_id (str, optional): The ID of the person to start the traversal from.
                                           If None, returns the full tree. Defaults to None.
            max_depth (int, optional): The maximum depth to traverse from the start node.
                                       Depth 0 is the start node itself. Ignored if start_node_id is None.
                                       Defaults to None (no depth limit).

        Returns:
            dict: A dictionary containing 'nodes' and 'links' lists.
        """
        nodes = []
        links = []
        included_node_ids = set()

        if start_node_id and start_node_id in self.people:
            # --- BFS for Lazy Loading ---
            logging.info(f"Generating tree subset: start_node={start_node_id}, max_depth={max_depth}")
            queue = deque([(start_node_id, 0)]) # Store (node_id, depth)
            visited = {start_node_id} # Keep track of visited nodes to prevent cycles/redundancy

            while queue:
                current_id, current_depth = queue.popleft()

                # Check depth limit
                if max_depth is not None and current_depth > max_depth:
                    continue

                # Add current node to results
                included_node_ids.add(current_id)

                # Find neighbors (parents, children, spouses/partners)
                neighbors = set()
                # Find relationships involving the current person
                related_rels = self.find_relationships_for_person(current_id)
                for rel in related_rels:
                    other_id = None
                    if rel.person1_id == current_id:
                        other_id = rel.person2_id
                    else:
                        other_id = rel.person1_id

                    # Ensure the other person exists in the main people dict
                    if other_id and other_id in self.people:
                         neighbors.add(other_id)

                # Add unvisited neighbors to the queue for the next level
                if max_depth is None or current_depth < max_depth:
                    for neighbor_id in neighbors:
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            queue.append((neighbor_id, current_depth + 1))
            # --- End BFS ---

        else:
            # If no start node or start node invalid, include all people
            if start_node_id:
                 logging.warning(f"get_nodes_links_data: start_node_id '{start_node_id}' not found. Returning full tree.")
            included_node_ids = set(self.people.keys())

        # --- Generate Node Data for Included Nodes ---
        for person_id in included_node_ids:
            person = self.people[person_id]
            photo_url = getattr(person, 'photo_url', generate_default_person_photo(person_id))
            nodes.append({
                "id": person.person_id,
                "type": "personNode",
                "data": {
                    "label": person.get_display_name(),
                    "full_name": person.get_full_name(),
                    "gender": person.gender,
                    "dob": person.birth_date,
                    "dod": person.death_date,
                    "birth_place": person.place_of_birth,
                    "death_place": person.place_of_death,
                    "photoUrl": photo_url
                },
                "position": {"x": 0, "y": 0}
            })

        # --- Generate Link Data for Relationships Between Included Nodes ---
        processed_rel_ids = set()
        for rel_id, rel in self.relationships.items():
            # Skip if already processed (for symmetric types) or if persons aren't included
            if rel_id in processed_rel_ids or \
               rel.person1_id not in included_node_ids or \
               rel.person2_id not in included_node_ids:
                continue

            source_id = rel.person1_id
            target_id = rel.person2_id
            rel_type = rel.rel_type.lower() if rel.rel_type else 'unknown'

            link_data = { "id": rel_id, "source": source_id, "target": target_id, "type": "default", "animated": False, "label": rel.rel_type, "data": rel.attributes }

            # Adjust source/target and style based on type for clearer visualization
            if rel_type == 'parent':
                 link_data["source"] = source_id; link_data["target"] = target_id
            elif rel_type == 'child':
                 link_data["source"] = target_id; link_data["target"] = source_id # Reverse for Parent->Child flow
                 link_data["label"] = "Parent" # Label edge from parent's perspective
            elif rel_type == 'spouse' or rel_type == 'partner':
                 link_data["type"] = "smoothstep"; link_data["label"] = "" # Hide label for spouse edge
                 # Mark reciprocal as processed
                 reciprocal_rel = next((r_id for r_id, r in self.relationships.items() if r.person1_id == target_id and r.person2_id == source_id and r.rel_type.lower() == rel_type), None)
                 if reciprocal_rel: processed_rel_ids.add(reciprocal_rel)

            links.append(link_data)
            processed_rel_ids.add(rel_id)

        logging.info(f"Generated node/link data: {len(nodes)} nodes, {len(links)} links.")
        return {"nodes": nodes, "links": links}


    # --- Persistence (_to_dict, _from_dict, save_tree, load_tree remain the same) ---
    def _to_dict(self):
        """Converts the entire tree (people and relationships) to a dictionary."""
        return { "people": {pid: person.to_dict() for pid, person in self.people.items()}, "relationships": {rid: rel.to_dict() for rid, rel in self.relationships.items()} }

    @classmethod
    def _from_dict(cls, data, tree_file_path, audit_log_path):
        """Creates a FamilyTree instance from a dictionary."""
        tree = cls(tree_file_path=tree_file_path, audit_log_path=audit_log_path)
        tree.people = {}; tree.relationships = {}
        for pid, pdata in data.get("people", {}).items():
            try:
                person = Person.from_dict(pdata)
                person.photo_url = getattr(person, 'photo_url', generate_default_person_photo(person.person_id))
                tree.people[pid] = person
            except (KeyError, ValueError, TypeError) as e: logging.warning(f"_from_dict: Skipping invalid person data for ID {pid} during load: {e}", exc_info=True)
        for rid, rdata in data.get("relationships", {}).items():
            try:
                rdata.setdefault('rel_id', rid); relationship = Relationship.from_dict(rdata)
                final_rid = relationship.rel_id if hasattr(relationship, 'rel_id') and relationship.rel_id else rid
                tree.relationships[final_rid] = relationship
            except (KeyError, ValueError, TypeError) as e: logging.warning(f"_from_dict: Skipping invalid relationship data for ID {rid} during load: {e}", exc_info=True)
        return tree

    def save_tree(self, saved_by="system"):
        """Saves the current state of the tree to the JSON file (encrypted)."""
        try: data_to_save = self._to_dict(); save_data(self.tree_file_path, data_to_save, is_encrypted=True)
        except Exception as e: logging.error(f"Error saving family tree to {self.tree_file_path}: {e}", exc_info=True); log_audit(self.audit_log_path, saved_by, 'save_tree', f'failure: {e}')

    def load_tree(self, loaded_by="system"):
        """Loads the tree state from the JSON file (encrypted)."""
        try:
            data = load_data(self.tree_file_path, default={}, is_encrypted=True)
            if data:
                loaded_tree = self._from_dict(data, self.tree_file_path, self.audit_log_path)
                self.people = loaded_tree.people; self.relationships = loaded_tree.relationships
                logging.info(f"Family tree loaded successfully: {len(self.people)} people, {len(self.relationships)} relationships.")
            else: logging.warning(f"No valid data found in {self.tree_file_path}. Starting with an empty tree."); self.people = {}; self.relationships = {}
        except FileNotFoundError: logging.info(f"Tree file {self.tree_file_path} not found. Starting with an empty tree."); self.people = {}; self.relationships = {}
        except Exception as e: logging.error(f"Critical error loading family tree from {self.tree_file_path}: {e}", exc_info=True); log_audit(self.audit_log_path, loaded_by, 'load_tree', f'failure: {e}'); self.people = {}; self.relationships = {}

