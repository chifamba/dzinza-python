# src/family_tree.py
import json
import uuid
import logging
import os
from datetime import datetime, date
from .person import Person
from .relationship import Relationship, VALID_RELATIONSHIP_TYPES
from .db_utils import load_data, save_data
from .audit_log import log_audit

class FamilyTree:
    # --- Keep __init__ ---
    def __init__(self, tree_file_path=None, audit_log_path=None):
        self.people = {}
        self.relationships = {}
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.tree_file_path = tree_file_path if tree_file_path else os.path.join(base_dir, 'family_tree.json')
        self.audit_log_path = audit_log_path if audit_log_path else os.path.join(base_dir, 'audit.log')

        tree_dir = os.path.dirname(tree_file_path)
        if tree_dir: os.makedirs(tree_dir, exist_ok=True)

    # --- Validation Helper ---
    @staticmethod
    def _is_valid_date(self, date_str):
        if not date_str: return True
        try: datetime.strptime(date_str, '%Y-%m-%d'); return True
        except ValueError: return False

    # --- Person Methods ---
    def add_person(self, first_name, last_name, nickname=None, dob=None, dod=None, pob=None, pod=None, gender=None, added_by="system", **kwargs):
        """ Adds person, now includes place of birth (pob) and place of death (pod). """
        if not first_name: logging.error(f"Error in add_person: Validation Error: Person's first name cannot be empty."); log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: empty first name'); return None
        if dob and not self._is_valid_date(dob): logging.error(f"Error in add_person: Validation Error: Invalid DOB format '{dob}'."); log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: invalid dob format'); return None
        if dod and not self._is_valid_date(dod): logging.error(f"Error in add_person: Validation Error: Invalid DOD format '{dod}'."); log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: invalid dod format'); return None
        if dob and dod:
            try:
                if datetime.strptime(dod, '%Y-%m-%d').date() < datetime.strptime(dob, '%Y-%m-%d').date(): logging.error(f"Error in add_person: Validation Error: DOD ({dod}) before DOB ({dob})."); log_audit(self.audit_log_path, added_by, 'add_person', f'failure - validation: dod before dob'); return None
            except ValueError: pass

        person_id = str(uuid.uuid4())
        try:
            person = Person(
                person_id=person_id, first_name=first_name.strip(),
                last_name=last_name.strip() if last_name else "",
                nickname=nickname.strip() if nickname else None,
                birth_date=dob if dob else None, death_date=dod if dod else None,
                place_of_birth=pob.strip() if pob else None, # Add pob
                place_of_death=pod.strip() if pod else None,  # Add pod
                gender=gender if gender else None, attributes=kwargs
            )
        except Exception as e: logging.error(f"Error creating Person object: {e}", exc_info=True); log_audit(self.audit_log_path, added_by, 'add_person', f'failure - error creating person object: {e}'); return None
        self.people[person_id] = person
        display_name = person.get_display_name(); full_name = person.get_full_name()
        logging.info(f"Person added: {display_name} (ID: {person.person_id})")
        log_audit(self.audit_log_path, added_by, 'add_person', f'success - id: {person.person_id}, name: {full_name}')
        self.save_tree(added_by); return person

    def edit_person(self, person_id, updated_data, edited_by="system"):
        """ Edits person, now includes place_of_birth and place_of_death. """
        person = self.find_person(person_id=person_id);        if not person: logging.error(f"Error in edit_person: Person {person_id} not found."); log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - person not found: {person_id}'); return False

        # --- Validation ---
        new_first_name = updated_data.get('first_name', person.first_name)
        new_dob = updated_data.get('birth_date', person.birth_date)
        new_dod = updated_data.get('death_date', person.death_date)
        # pob/pod don't need specific validation here beyond being strings.
        if not new_first_name or not new_first_name.strip(): print(f"Validation Error: First name cannot be empty for {person_id}."); log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: empty first name for id {person_id}'); return False
        if new_dob and not self._is_valid_date(new_dob): logging.error(f"Validation Error: Invalid DOB format '{new_dob}' for {person_id}."); log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: invalid dob format for id {person_id}'); return False
        if new_dod and not self._is_valid_date(new_dod): logging.error(f"Validation Error: Invalid DOD format '{new_dod}' for {person_id}."); log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: invalid dod format for id {person_id}'); return False
        if new_dob and new_dod:
            try:
                if datetime.strptime(new_dod, '%Y-%m-%d').date() < datetime.strptime(new_dob, '%Y-%m-%d').date(): logging.error(f"Validation Error: DOD ({new_dod}) before DOB ({new_dob}) for {person_id}."); log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - validation: dod before dob for id {person_id}'); return False
            except ValueError: pass


        original_display_name = person.get_display_name(); changes_made = False
        for key, value in updated_data.items():
            if hasattr(person, key):
                current_value = getattr(person, key); new_value = value.strip() if isinstance(value, str) else value
                # Handle optional fields correctly
                if key in ['nickname', 'birth_date', 'death_date', 'gender', 'notes', 'place_of_birth', 'place_of_death'] and not new_value: new_value = None
                elif key == 'last_name' and not new_value: new_value = ""
                if current_value != new_value: setattr(person, key, new_value); changes_made = True;                
            else: logging.warning(f"Warning in edit_person: Attempted to update non-existent attribute '{key}' for person {person_id}")
        
        if changes_made: log_audit(self.audit_log_path, edited_by, 'edit_person', f'success - id: {person_id}, name: {original_display_name} -> {person.get_display_name()}'); self.save_tree(edited_by); return True
        else: log_audit(self.audit_log_path, edited_by, 'edit_person', f'no changes made for id: {person_id}'); return False

    # --- Keep delete_person, add_relationship, edit_relationship, delete_relationship ---
    def delete_person(self, person_id, deleted_by="system"):
        # (Keep implementation)
        person = self.find_person(person_id=person_id)
        if person:
            person_display_name = person.get_display_name(); del self.people[person_id]
            rels_to_delete = [rid for rid, rel in self.relationships.items() if rel.person1_id == person_id or rel.person2_id == person_id]
            num_rels_deleted = len(rels_to_delete)
            for rid in rels_to_delete: del self.relationships[rid]
            logging.info(f"Person '{person_display_name}' (ID: {person_id}) and {num_rels_deleted} related relationships deleted.")
            log_audit(self.audit_log_path, deleted_by, 'delete_person', f'success - id: {person_id}, name: {person_display_name}, removed {num_rels_deleted} relationships')
            self.save_tree(deleted_by); return True
        else: logging.error(f"Error in delete_person: Person with ID {person_id} not found for deletion."); log_audit(self.audit_log_path, deleted_by, 'delete_person', f'failure - person not found: {person_id}'); return False

    def add_relationship(self, person1_id, person2_id, relationship_type, added_by="system"):
        if not person1_id or not person2_id: logging.error("Error in add_relationship: Validation Error: Both Person 1 and Person 2 must be selected."); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: missing person id'); return None
        if person1_id == person2_id: logging.error("Error in add_relationship: Validation Error: Cannot add a relationship between a person and themselves."); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: self relationship ({person1_id})'); return None
        if not relationship_type or relationship_type.strip() == "": logging.error("Error in add_relationship: Validation Error: Relationship type cannot be empty."); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: empty relationship type'); return None
        person1 = self.people.get(person1_id); person2 = self.people.get(person2_id)
        if not person1 or not person2:
            missing_ids = [];
            if not person1: missing_ids.append(person1_id)
            if not person2: missing_ids.append(person2_id)
            logging.error(f"Error in add_relationship: One or both persons (ID(s): {', '.join(missing_ids)}) not found."); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - person not found ({", ".join(missing_ids)})'); return None
        for rel in self.relationships.values():
            if (rel.person1_id == person1_id and rel.person2_id == person2_id and rel.rel_type == relationship_type) or \
               (rel.person1_id == person2_id and rel.person2_id == person1_id and rel.rel_type == relationship_type): logging.error(f"Error in add_relationship: Validation Error: Relationship ({relationship_type}) already exists between {person1_id} and {person2_id}."); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - validation: duplicate relationship'); return None
        relationship_id = str(uuid.uuid4())
        try: relationship = Relationship(person1_id=person1_id, person2_id=person2_id, rel_type=relationship_type); self.relationships[relationship_id] = relationship; logging.info(f"Relationship added: {person1.get_display_name()} - {relationship_type} - {person2.get_display_name()}"); log_audit(self.audit_log_path, added_by, 'add_relationship', f'success - id: {relationship_id}, type: {relationship_type}, persons: ({person1_id}, {person2_id})'); self.save_tree(added_by); return relationship
        except Exception as e: logging.error(f"Error in add_relationship: Error creating Relationship object: {e}", exc_info=True); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - error creating relationship object: {e}'); return None

    def edit_relationship(self, relationship_id, updated_data, edited_by="system"):
        # (Keep implementation)
        if relationship_id not in self.relationships: logging.error(f"Error in edit_relationship: Relationship {relationship_id} not found."); log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'failure - relationship not found: {relationship_id}'); return False
        relationship = self.relationships[relationship_id]; original_type = relationship.rel_type; new_type = updated_data.get('rel_type', original_type).strip()
        if not new_type: logging.error(f"Error in edit_relationship: Validation Error: Relationship type cannot be empty for {relationship_id}."); log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'failure - validation: empty type for id {relationship_id}'); return False
        if new_type != original_type:
            relationship.rel_type = new_type
            p1_name = self.people.get(relationship.person1_id, Person(person_id=relationship.person1_id)).get_display_name(); p2_name = self.people.get(relationship.person2_id, Person(person_id=relationship.person2_id)).get_display_name()
            log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'success - id: {relationship_id}, type: {original_type} -> {new_type}, persons: ({p1_name}, {p2_name})'); self.save_tree(edited_by); return True
        else: log_audit(self.audit_log_path, edited_by, 'edit_relationship', f'no changes made for id: {relationship_id}'); return False

    def delete_relationship(self, relationship_id, deleted_by="system"):        if relationship_id in self.relationships:
            relationship = self.relationships[relationship_id]; p1_name = self.people.get(relationship.person1_id, Person(person_id=relationship.person1_id)).get_display_name(); p2_name = self.people.get(relationship.person2_id, Person(person_id=relationship.person2_id)).get_display_name(); rel_type = relationship.rel_type;            del self.relationships[relationship_id]
            logging.info(f"Relationship ({rel_type}) between {p1_name} and {p2_name} deleted.")
            log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'success - id: {relationship_id}, type: {rel_type}, persons: ({p1_name}, {p2_name})')
            self.save_tree(deleted_by); return True;        else: logging.error(f"Error in delete_relationship: Relationship {relationship_id} not found."); log_audit(self.audit_log_path, deleted_by, 'delete_relationship', f'failure - relationship not found: {relationship_id}'); return False

    # --- Keep find_person ---
    def find_person(self, name=None, person_id=None):
        # (Keep implementation)
        if person_id: return self.people.get(person_id)
        if name:
            search_name_lower = name.lower()
            for person in self.people.values():
                if person.get_full_name().lower() == search_name_lower: return person
        return None

    # --- UPDATED Search People Method ---
    def search_people(self, query=None, dob_start=None, dob_end=None, location=None):
        """
        Searches people by name, DOB range, and/or location.

        Args:
            query (str, optional): Search term for name/nickname.
            dob_start (str, optional): Start date YYYY-MM-DD.
            dob_end (str, optional): End date YYYY-MM-DD.
            location (str, optional): Search term for place of birth/death.

        Returns:
            list[Person]: List of matching Person objects.
        """
        results = []
        search_term = query.lower().strip() if query else None
        location_term = location.lower().strip() if location else None

        # Validate and parse date inputs
        start_date_obj, end_date_obj = None, None
        try:
            if dob_start and self._is_valid_date(dob_start): start_date_obj = date.fromisoformat(dob_start)
            elif dob_start: logging.error(f"Error in search_people: Invalid start date format '{dob_start}' ignored.")
            if dob_end and self._is_valid_date(dob_end): end_date_obj = date.fromisoformat(dob_end);
            elif dob_end: logging.error(f"Error in search_people: Invalid end date format '{dob_end}' ignored.")
        except ValueError as e: logging.error(f"Error parsing search dates: {e}", exc_info=True); return []

        for person in self.people.values():
            # --- Match Name ---
            name_match = False
            if search_term:
                if person.first_name and search_term in person.first_name.lower(): name_match = True
                if not name_match and person.last_name and search_term in person.last_name.lower(): name_match = True
                if not name_match and person.nickname and search_term in person.nickname.lower(): name_match = True
            else: name_match = True # No name query means name matches

            # --- Match Date Range ---
            date_match = False
            if start_date_obj or end_date_obj:
                if person.birth_date and self._is_valid_date(person.birth_date):
                    try:
                        person_dob = date.fromisoformat(person.birth_date)
                        dob_in_range = True
                        if start_date_obj and person_dob < start_date_obj: dob_in_range = False
                        if end_date_obj and person_dob > end_date_obj: dob_in_range = False
                        if dob_in_range: date_match = True
                    except ValueError: pass # Ignore person if their DOB is invalid
            else: date_match = True # No date query means date matches

            # --- Match Location ---
            location_match = False
            if location_term:
                if person.place_of_birth and location_term in person.place_of_birth.lower(): location_match = True
                if not location_match and person.place_of_death and location_term in person.place_of_death.lower(): location_match = True
            else: location_match = True # No location query means location matches

            # --- Add if all criteria match ---
            if name_match and date_match and location_match:
                results.append(person)

        results.sort(key=lambda p: p.get_full_name())  # Sort results by full name.
        return results
    # --- End Search People Method ---

    # --- Keep get_summaries, get_nodes_links, _to_dict, _from_dict, save/load ---
    def get_people_summary(self):
        summary_list = []
        for p in self.people.values():
             full_name = p.get_full_name(); display_name = p.get_display_name()
             # Include location in summary if needed by templates
             summary_list.append({"person_id": p.person_id, "name": full_name, "display_name": display_name, "nickname": p.nickname, "dob": p.birth_date, "dod": p.death_date, "gender": p.gender, "pob": p.place_of_birth, "pod": p.place_of_death})
        return sorted(summary_list, key=lambda x: x['name'])

    def get_relationships_summary(self):
        summary = []
        for rel_id, rel in self.relationships.items():
            person1 = self.people.get(rel.person1_id); person2 = self.people.get(rel.person2_id)
            person1_display_name = person1.get_display_name() if person1 else f"Unknown (ID: {rel.person1_id[:8]}...)"
            person2_display_name = person2.get_display_name() if person2 else f"Unknown (ID: {rel.person2_id[:8]}...)"
            person1_sort_name = person1.get_full_name() if person1 else "Unknown"
            summary.append({"relationship_id": rel_id, "person1_id": rel.person1_id, "person1_name": person1_display_name, "person2_id": rel.person2_id, "person2_name": person2_display_name, "relationship_type": rel.rel_type, "_person1_sort_name": person1_sort_name})
        return sorted(summary, key=lambda x: (x['relationship_type'], x['_person1_sort_name']))

    def get_nodes_links_data(self):
        nodes = []; links = []; person_ids = list(self.people.keys())
        for person_id in person_ids:
            person = self.people[person_id]
            nodes.append({"id": person.person_id, "name": person.get_display_name(), "full_name": person.get_full_name(), "gender": person.gender, "dob": person.birth_date, "pob": person.place_of_birth}) # Add pob to node data
            nodes.append({
                "id": person.person_id,
                "name": person.get_display_name(),
                "full_name": person.get_full_name(),
                "gender": person.gender,
                "dob": person.birth_date,
                "birth_place": person.place_of_birth,  # Changed from 'pob' to 'birth_place'
                "photoUrl": person.photo_url if hasattr(person, 'photo_url') and person.photo_url else "https://via.placeholder.com/150"  # Add photoUrl
            })        
            processed_rel_ids = set()
        for rel_id, rel in self.relationships.items():
            if rel_id in processed_rel_ids: continue
            source_id = rel.person1_id; target_id = rel.person2_id; rel_type = rel.rel_type.lower()
            if source_id not in self.people or target_id not in self.people: logging.warning(f"Warning in get_nodes_links_data: Skipping relationship {rel_id} because person {source_id} or {target_id} not found."); continue
            link_data = None;
            if rel_type == 'parent': link_data = {"source": source_id, "target": target_id, "type": "parent_child"}
            elif rel_type == 'child': link_data = {"source": target_id, "target": source_id, "type": "parent_child"}
            elif rel_type == 'spouse' or rel_type == 'partner':
                 link_data = {"source": source_id, "target": target_id, "type": rel_type}
                 reciprocal_rel = next((r_id for r_id, r in self.relationships.items() if r.person1_id == target_id and r.person2_id == source_id and r.rel_type.lower() == rel_type), None)
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
             except Exception as e: logging.warning(f"Warning in _from_dict: Skipping invalid person data for ID {pid} during load: {e}", exc_info=True)
        for rid, rdata in data.get("relationships", {}).items(): # Add pob to node data.
             try: tree.relationships[rid] = Relationship.from_dict(rdata)
             except Exception as e: logging.warning(f"Warning in _from_dict: Skipping invalid relationship data for ID {rid} during load: {e}", exc_info=True)
        return tree  # Add photoUrl
    def save_tree(self, saved_by="system"):
        try: data_to_save = self._to_dict(); save_data(self.tree_file_path, data_to_save)
        except Exception as e: logging.error(f"Error saving tree: {e}", exc_info=True); log_audit(self.audit_log_path, saved_by, 'save_tree', f'failure: {e}')
    def load_tree(self, loaded_by="system"):
        try:
            data = load_data(self.tree_file_path)
            if data: loaded_tree = self._from_dict(data, self.tree_file_path, self.audit_log_path); self.people = loaded_tree.people; self.relationships = loaded_tree.relationships; logging.info(f"Tree loaded: {len(self.people)} people, {len(self.relationships)} relationships.")
            else: logging.info(f"No data found. Starting empty."); self.people = {}; self.relationships = {}
        except FileNotFoundError: logging.info(f"Tree file not found. Starting empty."); self.people = {}; self.relationships = {}
        except Exception as e: logging.error(f"Error loading tree: {e}", exc_info=True); log_audit(self.audit_log_path, loaded_by, 'load_tree', f'failure: {e}'); self.people = {}; self.relationships = {}

