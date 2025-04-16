# src/family_tree.py
import json
import uuid
import os
from .person import Person
from .relationship import Relationship
from .db_utils import load_data, save_data
from .audit_log import log_audit

class FamilyTree:
    # --- Keep __init__ and other methods ---
    def __init__(self, tree_file_path='data/family_tree.json', audit_log_path='data/audit.log'):
        self.people = {}
        self.relationships = {}
        self.tree_file_path = tree_file_path
        self.audit_log_path = audit_log_path
        tree_dir = os.path.dirname(tree_file_path)
        if tree_dir:
             os.makedirs(tree_dir, exist_ok=True)

    # --- Keep add_person, add_relationship, find_person ---
    def add_person(self, first_name, last_name, nickname=None, dob=None, dod=None, gender=None, added_by="system", **kwargs):
        # (Keep implementation from family_tree_py_init_fix)
        if not first_name: print("Error: Person's first name cannot be empty."); log_audit(self.audit_log_path, added_by, 'add_person', f'failure - empty first name'); return None
        person_id = str(uuid.uuid4())
        try:
            person = Person(person_id=person_id, first_name=first_name.strip(), last_name=last_name.strip() if last_name else "", nickname=nickname.strip() if nickname else None, birth_date=dob if dob else None, death_date=dod if dod else None, gender=gender if gender else None, attributes=kwargs)
        except Exception as e: print(f"Error creating Person object: {e}"); log_audit(self.audit_log_path, added_by, 'add_person', f'failure - error creating person object: {e}'); return None
        self.people[person_id] = person
        display_name = person.get_display_name(); full_name = person.get_full_name()
        print(f"Person added: {display_name} (ID: {person.person_id})")
        log_audit(self.audit_log_path, added_by, 'add_person', f'success - id: {person.person_id}, name: {full_name}')
        self.save_tree(added_by); return person

    def add_relationship(self, person1_id, person2_id, relationship_type, added_by="system"):
        # (Keep implementation from family_tree_py_init_fix)
        person1 = self.people.get(person1_id); person2 = self.people.get(person2_id)
        if not person1 or not person2:
            missing_ids = []
            if not person1: missing_ids.append(person1_id)
            if not person2: missing_ids.append(person2_id)
            print(f"Error: One or both persons (ID(s): {', '.join(missing_ids)}) not found.")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - person not found ({", ".join(missing_ids)})'); return None
        relationship_id = str(uuid.uuid4())
        try:
            relationship = Relationship(person1_id=person1_id, person2_id=person2_id, rel_type=relationship_type)
            self.relationships[relationship_id] = relationship
            print(f"Relationship added: {person1.get_display_name()} - {relationship_type} - {person2.get_display_name()}")
            log_audit(self.audit_log_path, added_by, 'add_relationship', f'success - type: {relationship_type}, persons: ({person1_id}, {person2_id})')
            self.save_tree(added_by); return relationship
        except Exception as e: print(f"Error creating Relationship object: {e}"); log_audit(self.audit_log_path, added_by, 'add_relationship', f'failure - error creating relationship object: {e}'); return None

    def find_person(self, name=None, person_id=None):
        # (Keep implementation from family_tree_py_init_fix - finds first exact match)
        if person_id: return self.people.get(person_id)
        if name:
            search_name_lower = name.lower()
            for person in self.people.values():
                if person.get_full_name().lower() == search_name_lower: return person
        return None

    # --- NEW: Search People Method ---
    def search_people(self, query):
        """
        Searches for people by a query string in first name, last name, or nickname.
        Performs a case-insensitive substring search.

        Args:
            query (str): The search term.

        Returns:
            list[Person]: A list of Person objects matching the query.
                          Returns an empty list if query is empty or no matches found.
        """
        if not query:
            return [] # Return empty list if query is empty

        results = []
        search_term = query.lower().strip()

        for person in self.people.values():
            match = False
            # Check first name
            if person.first_name and search_term in person.first_name.lower():
                match = True
            # Check last name (if not already matched)
            if not match and person.last_name and search_term in person.last_name.lower():
                match = True
            # Check nickname (if not already matched and nickname exists)
            if not match and person.nickname and search_term in person.nickname.lower():
                match = True

            if match:
                results.append(person)

        # Sort results alphabetically by full name
        results.sort(key=lambda p: p.get_full_name())
        return results
    # --- End Search People Method ---


    # --- Keep get_people_summary, get_relationships_summary, get_nodes_links_data ---
    def get_people_summary(self):
        # (Keep implementation from family_tree_py_init_fix)
        summary_list = []
        for p in self.people.values():
             full_name = p.get_full_name(); display_name = p.get_display_name()
             summary_list.append({"person_id": p.person_id, "name": full_name, "display_name": display_name, "nickname": p.nickname, "dob": p.birth_date, "dod": p.death_date, "gender": p.gender})
        return sorted(summary_list, key=lambda x: x['name'])

    def get_relationships_summary(self):
        # (Keep implementation from family_tree_py_hierarchy_links)
        summary = []
        for rel_id, rel in self.relationships.items():
            person1 = self.people.get(rel.person1_id); person2 = self.people.get(rel.person2_id)
            person1_display_name = person1.get_display_name() if person1 else f"Unknown (ID: {rel.person1_id[:8]}...)"
            person2_display_name = person2.get_display_name() if person2 else f"Unknown (ID: {rel.person2_id[:8]}...)"
            person1_sort_name = person1.get_full_name() if person1 else "Unknown"
            summary.append({"relationship_id": rel_id, "person1_id": rel.person1_id, "person1_name": person1_display_name, "person2_id": rel.person2_id, "person2_name": person2_display_name, "relationship_type": rel.rel_type, "_person1_sort_name": person1_sort_name})
        return sorted(summary, key=lambda x: (x['relationship_type'], x['_person1_sort_name']))

    def get_nodes_links_data(self):
        # (Keep implementation from family_tree_py_hierarchy_links)
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
                 reciprocal_rel = next((r for r_id, r in self.relationships.items() if r.person1_id == target_id and r.person2_id == source_id and r.rel_type.lower() == rel_type), None)
                 if reciprocal_rel: processed_rel_ids.add(reciprocal_rel) # Need ID
            else: link_data = {"source": source_id, "target": target_id, "type": rel_type}
            if link_data: links.append(link_data)
            processed_rel_ids.add(rel_id)
        return {"nodes": nodes, "links": links}

    # --- Keep _to_dict, _from_dict, save_tree, load_tree, edit_person, delete_person ---
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
        try: data_to_save = self._to_dict(); save_data(self.tree_file_path, data_to_save); print(f"Family tree saved successfully to {self.tree_file_path}")
        except Exception as e: print(f"Error saving family tree to {self.tree_file_path}: {e}"); log_audit(self.audit_log_path, saved_by, 'save_tree', f'failure: {e}')
    def load_tree(self, loaded_by="system"):
        try:
            data = load_data(self.tree_file_path)
            if data: loaded_tree = self._from_dict(data, self.tree_file_path, self.audit_log_path); self.people = loaded_tree.people; self.relationships = loaded_tree.relationships; print(f"Family tree loaded successfully from {self.tree_file_path}. Found {len(self.people)} people and {len(self.relationships)} relationships.")
            else: print(f"No existing data found or error loading from {self.tree_file_path}. Starting with an empty tree."); self.people = {}; self.relationships = {}
        except FileNotFoundError: print(f"Tree file {self.tree_file_path} not found. Starting with an empty tree."); self.people = {}; self.relationships = {}
        except Exception as e: print(f"An unexpected error occurred loading the tree from {self.tree_file_path}: {e}"); log_audit(self.audit_log_path, loaded_by, 'load_tree', f'failure: {e}'); self.people = {}; self.relationships = {}
    def edit_person(self, person_id, updated_data, edited_by="system"):
        person = self.find_person(person_id=person_id)
        if person:
            original_display_name = person.get_display_name(); changes_made = False
            for key, value in updated_data.items():
                if hasattr(person, key):
                    current_value = getattr(person, key); new_value = value.strip() if isinstance(value, str) else value
                    if key in ['nickname', 'birth_date', 'death_date', 'gender', 'notes'] and not new_value: new_value = None
                    elif key in ['first_name', 'last_name'] and not new_value:
                         if key == 'first_name': print(f"Warning: Attempted to set empty first_name for person {person_id}. Keeping original."); continue
                         else: new_value = ""
                    if current_value != new_value: setattr(person, key, new_value); changes_made = True
                else: print(f"Warning: Attempted to update non-existent attribute '{key}' for person {person_id}")
            if changes_made: log_audit(self.audit_log_path, edited_by, 'edit_person', f'success - id: {person_id}, name: {original_display_name} -> {person.get_display_name()}'); self.save_tree(edited_by); return True
            else: log_audit(self.audit_log_path, edited_by, 'edit_person', f'no changes made for id: {person_id}'); return False
        else: print(f"Error: Person with ID {person_id} not found for editing."); log_audit(self.audit_log_path, edited_by, 'edit_person', f'failure - person not found: {person_id}'); return False
    def delete_person(self, person_id, deleted_by="system"):
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

