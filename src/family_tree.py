# src/family_tree.py

import json
import csv
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, ElementTree # Import ElementTree explicitly

from .person import Person
from .relationship import Relationship, get_reciprocal_relationship
from .audit_log import AuditLog, PlaceholderAuditLog
from .encryption import DataEncryptor, PlaceholderDataEncryptor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FamilyTree:
    """
    Manages persons and relationships in a family tree.
    Includes import/export functionality and audit logging.
    """

    def __init__(self, audit_log: Optional[AuditLog] = None, encryptor: Optional[DataEncryptor] = None):
        """
        Initializes the FamilyTree.

        Args:
            audit_log: An instance of AuditLog (or compatible) for logging actions.
                       Defaults to PlaceholderAuditLog if None.
            encryptor: An instance of DataEncryptor (or compatible) for data encryption.
                       Defaults to PlaceholderDataEncryptor if None.
        """
        self.persons: Dict[str, Person] = {}
        # Relationships stored outgoing from person1_id: {person1_id: [Relationship(p1, p2), Relationship(p1, p3)]}
        self.relationships: Dict[str, List[Relationship]] = {}
        self.audit_log = audit_log or PlaceholderAuditLog()
        self.encryptor = encryptor or PlaceholderDataEncryptor()
        logging.info("FamilyTree initialized.")

    # --- Person Management ---

    def add_person(self, person: Person, user: str = "system") -> None:
        """
        Adds a new person to the family tree.

        Args:
            person: The Person object to add.
            user: The user performing the action.

        Raises:
            ValueError: If a person with the same ID already exists.
        """
        if not isinstance(person, Person):
             raise TypeError("person must be an instance of Person")
        if person.person_id in self.persons:
            raise ValueError(f"Person with ID {person.person_id} already exists.")

        self.persons[person.person_id] = person
        self.audit_log.log_event(user, "person_added", f"Added person: {person.person_id} ({person.get_full_name()})")
        logging.info(f"Added person {person.person_id} by user {user}")

    def get_person(self, person_id: str) -> Optional[Person]:
        """Retrieves a person by their ID."""
        return self.persons.get(person_id)

    def update_person(self, person_id: str, update_data: Dict[str, Any], user: str = "system") -> bool:
        """
        Updates details of an existing person.

        Args:
            person_id: The ID of the person to update.
            update_data: A dictionary containing the attributes to update.
                         Supports keys like 'first_name', 'last_name', 'birth_date', etc.
            user: The user performing the action.

        Returns:
            True if the update was successful, False otherwise.
        """
        person = self.get_person(person_id)
        if not person:
            logging.warning(f"Update failed: Person with ID {person_id} not found.")
            return False

        updated = False
        for key, value in update_data.items():
            if hasattr(person, key):
                setattr(person, key, value)
                updated = True
            else:
                logging.warning(f"Update warning: Attribute '{key}' not found on Person object for {person_id}.")

        if updated:
            self.audit_log.log_event(user, "person_updated", f"Updated person: {person_id} ({person.get_full_name()})")
            logging.info(f"Updated person {person_id} by user {user}")
            return True
        return False

    def delete_person(self, person_id: str, user: str = "system") -> bool:
        """
        Deletes a person and all their relationships from the tree.

        Args:
            person_id: The ID of the person to delete.
            user: The user performing the action.

        Returns:
            True if deletion was successful, False if the person was not found.
        """
        person = self.get_person(person_id)
        if not person:
            logging.warning(f"Deletion failed: Person with ID {person_id} not found.")
            return False

        person_name = person.get_full_name() # Get name before deleting

        # --- Remove relationships involving this person ---
        # 1. Remove outgoing relationships stored under person_id
        if person_id in self.relationships:
            # Iterate over a copy because we modify the list during iteration
            outgoing_rels = list(self.relationships.get(person_id, []))
            for rel in outgoing_rels:
                # Log removal before attempting deletion
                log_desc = f"Removed relationship involving deleted person {person_id}: {rel}"
                self.audit_log.log_event(user, "relationship_removed", log_desc)
                logging.info(f"Attempting to remove reciprocal relationship for {rel} due to {person_id} deletion by {user}")
                # Also remove the reciprocal relationship from the other person's list
                self._remove_relationship_entry(rel.person2_id, rel.person1_id, get_reciprocal_relationship(rel.rel_type))
            # Clear the entry for the deleted person
            del self.relationships[person_id]


        # 2. Remove incoming relationships stored under other persons' IDs
        # Iterate through all relationship lists to find entries pointing to the deleted person
        related_person_ids = list(self.relationships.keys()) # Iterate over copy of keys
        for other_person_id in related_person_ids:
            if other_person_id == person_id: # Skip self (already handled)
                 continue

            rels_to_remove = []
            if other_person_id in self.relationships: # Check if key still exists
                # Iterate over a copy of the list for safe removal
                current_rels = list(self.relationships.get(other_person_id, []))
                for rel in current_rels:
                    if rel.person2_id == person_id:
                        rels_to_remove.append(rel) # Mark for removal

                # Remove marked relationships
                if rels_to_remove:
                    original_list = self.relationships.get(other_person_id, [])
                    updated_list = [r for r in original_list if r not in rels_to_remove]

                    if not updated_list: # If list becomes empty, remove the key
                        del self.relationships[other_person_id]
                    else:
                        self.relationships[other_person_id] = updated_list

                    # Log the removal (might duplicate logs from step 1, consider refining)
                    for rel in rels_to_remove:
                         log_desc = f"Removed relationship involving deleted person {person_id}: {rel}"
                         self.audit_log.log_event(user, "relationship_removed", log_desc)
                         logging.info(f"Removed relationship {rel} due to {person_id} deletion by {user}")


        # --- Delete the person object ---
        del self.persons[person_id]

        self.audit_log.log_event(user, "person_deleted", f"Deleted person: {person_id} ({person_name})")
        logging.info(f"Deleted person {person_id} and associated relationships by user {user}")
        return True


    def find_person_by_name(self, name_query: str) -> List[Person]:
        """Finds persons whose first or last name contains the query string (case-insensitive)."""
        name_query_lower = name_query.lower()
        results = []
        for person in self.persons.values():
            if name_query_lower in person.get_full_name().lower():
                results.append(person)
        return results

    # --- Relationship Management ---

    def _add_relationship_entry(self, person1_id: str, person2_id: str, rel_type: str, attributes: Optional[Dict] = None):
        """Internal helper to add a single directed relationship entry."""
        if person1_id not in self.relationships:
            self.relationships[person1_id] = []
        # Avoid adding duplicate relationships
        existing_rels = self.relationships[person1_id]
        if not any(r.person2_id == person2_id and r.rel_type == rel_type for r in existing_rels):
             new_rel = Relationship(person1_id, person2_id, rel_type, attributes)
             self.relationships[person1_id].append(new_rel)
             return new_rel
        return None # Indicate relationship already existed


    def _remove_relationship_entry(self, person1_id: str, person2_id: str, rel_type: str) -> bool:
        """Internal helper to remove a single directed relationship entry."""
        if person1_id not in self.relationships:
            return False

        original_rels = self.relationships[person1_id]
        rels_after_removal = [r for r in original_rels if not (r.person2_id == person2_id and r.rel_type == rel_type)]

        if len(rels_after_removal) < len(original_rels):
            if not rels_after_removal: # If list becomes empty, remove the key
                 del self.relationships[person1_id]
            else:
                 self.relationships[person1_id] = rels_after_removal
            return True # Indicate removal occurred
        return False # Relationship not found


    def add_relationship(self, person1_id: str, person2_id: str, rel_type: str, attributes: Optional[Dict] = None, user: str = "system") -> bool:
        """
        Adds a relationship between two persons. Handles reciprocal relationships.

        Args:
            person1_id: ID of the first person.
            person2_id: ID of the second person.
            rel_type: The type of relationship from person1 to person2 (e.g., 'spouse', 'child', 'parent').
            attributes: Optional dictionary of relationship attributes (e.g., start_date, end_date).
            user: The user performing the action.

        Returns:
            True if the relationship was added successfully, False otherwise.

        Raises:
            ValueError: If either person ID does not exist.
        """
        if person1_id not in self.persons or person2_id not in self.persons:
            raise ValueError(f"One or both person IDs not found: {person1_id}, {person2_id}")
        if person1_id == person2_id:
             raise ValueError("Cannot add relationship to self.")

        # Add the primary relationship (p1 -> p2)
        primary_rel = self._add_relationship_entry(person1_id, person2_id, rel_type, attributes)

        # Add the reciprocal relationship (p2 -> p1)
        reciprocal_rel_type = get_reciprocal_relationship(rel_type)
        reciprocal_rel = self._add_relationship_entry(person2_id, person1_id, reciprocal_rel_type, attributes) # Use same attributes for now

        if primary_rel or reciprocal_rel: # Log if at least one direction was added
            # Log the primary relationship addition attempt
            log_desc = f"Added relationship: {primary_rel if primary_rel else f'{person1_id} -> {person2_id} ({rel_type}) - already existed?'}"
            self.audit_log.log_event(user, "relationship_added", log_desc)
            logging.info(f"Added relationship {person1_id} -> {person2_id} ({rel_type}) by user {user}")

            # Optionally log reciprocal if it was distinct
            if reciprocal_rel and reciprocal_rel_type != rel_type: # Avoid logging self-reciprocal like 'spouse' twice implicitly
                log_desc_recip = f"Added reciprocal relationship: {reciprocal_rel}"
                self.audit_log.log_event(user, "relationship_added", log_desc_recip)
                logging.info(f"Added reciprocal relationship {person2_id} -> {person1_id} ({reciprocal_rel_type}) by user {user}")
            return True
        return False # Neither direction resulted in a new entry


    def get_relationships(self, person_id: str) -> List[Relationship]:
        """Retrieves all outgoing relationships for a given person ID."""
        return self.relationships.get(person_id, [])

    def update_relationship(self, person1_id: str, person2_id: str, old_rel_type: str, update_data: Dict[str, Any], user: str = "system") -> bool:
        """
        Updates attributes or type of an existing relationship. Handles reciprocal update.

        Args:
            person1_id: ID of the first person.
            person2_id: ID of the second person.
            old_rel_type: The current relationship type from person1 to person2.
            update_data: Dictionary of updates (e.g., {'rel_type': 'divorced', 'end_date': '...'})
            user: The user performing the action.

        Returns:
            True if the update was successful, False otherwise.
        """
        primary_updated = False
        reciprocal_updated = False
        new_rel_type = update_data.get('rel_type', old_rel_type) # Get new type if provided

        # --- Update primary relationship (p1 -> p2) ---
        if person1_id in self.relationships:
            for rel in self.relationships[person1_id]:
                if rel.person2_id == person2_id and rel.rel_type == old_rel_type:
                    rel.rel_type = new_rel_type # Update type if changed
                    if rel.attributes is None: rel.attributes = {}
                    rel.attributes.update({k: v for k, v in update_data.items() if k != 'rel_type'}) # Update attributes
                    primary_updated = True
                    break # Assume only one relationship of this type between these two

        # --- Update reciprocal relationship (p2 -> p1) ---
        old_reciprocal_type = get_reciprocal_relationship(old_rel_type)
        new_reciprocal_type = get_reciprocal_relationship(new_rel_type)
        if person2_id in self.relationships:
             for rel in self.relationships[person2_id]:
                 if rel.person2_id == person1_id and rel.rel_type == old_reciprocal_type:
                     rel.rel_type = new_reciprocal_type # Update reciprocal type
                     if rel.attributes is None: rel.attributes = {}
                     # Update attributes, be careful not to overwrite different reciprocal attributes if needed
                     rel.attributes.update({k: v for k, v in update_data.items() if k != 'rel_type'})
                     reciprocal_updated = True
                     break

        if primary_updated or reciprocal_updated:
            log_desc = f"Updated relationship: {person1_id} <-> {person2_id} (now {new_rel_type})"
            self.audit_log.log_event(user, "relationship_updated", log_desc)
            logging.info(f"Updated relationship {person1_id}<->{person2_id} from {old_rel_type} to {new_rel_type} by {user}")
            return True

        logging.warning(f"Update failed: Relationship {person1_id} -> {person2_id} ({old_rel_type}) not found.")
        return False

    def delete_relationship(self, person1_id: str, person2_id: str, rel_type: str, user: str = "system") -> bool:
        """
        Deletes a specific relationship between two persons. Handles reciprocal deletion.

        Args:
            person1_id: ID of the first person.
            person2_id: ID of the second person.
            rel_type: The type of relationship from person1 to person2 to delete.
            user: The user performing the action.

        Returns:
            True if the relationship was deleted successfully, False otherwise.
        """
        primary_removed = self._remove_relationship_entry(person1_id, person2_id, rel_type)

        reciprocal_rel_type = get_reciprocal_relationship(rel_type)
        reciprocal_removed = self._remove_relationship_entry(person2_id, person1_id, reciprocal_rel_type)

        if primary_removed or reciprocal_removed:
            log_desc = f"Removed relationship: {person1_id} <-> {person2_id} ({rel_type})"
            self.audit_log.log_event(user, "relationship_removed", log_desc)
            logging.info(f"Removed relationship {person1_id} <-> {person2_id} ({rel_type}) by user {user}")
            return True

        logging.warning(f"Deletion failed: Relationship {person1_id} -> {person2_id} ({rel_type}) not found.")
        return False


    def find_relationships_by_type(self, rel_type_query: str) -> List[Relationship]:
        """Finds all relationships matching the given type."""
        results = []
        rel_type_query_lower = rel_type_query.lower()
        for p1_id, rel_list in self.relationships.items():
            for rel in rel_list:
                if rel_type_query_lower in rel.rel_type.lower():
                    # Avoid adding duplicates if relationship is stored reciprocally elsewhere
                    # This basic check might not be perfect for complex graphs
                    is_duplicate = False
                    reciprocal_type = get_reciprocal_relationship(rel.rel_type)
                    for existing_rel in results:
                        if (existing_rel.person1_id == rel.person2_id and
                            existing_rel.person2_id == rel.person1_id and
                            existing_rel.rel_type == reciprocal_type):
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        results.append(rel)
        return results


    # --- Data Persistence (Import/Export) ---

    def _load_data(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Loads raw person and relationship data from a file (JSON, CSV, XML)."""
        if not os.path.exists(file_path):
             raise FileNotFoundError(f"Import file not found: {file_path}")

        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()

        persons_data = []
        relationships_data = []

        try:
            if file_extension == ".json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read()
                decrypted_data_str = self.encryptor.decrypt(encrypted_data)
                data = json.loads(decrypted_data_str)
                persons_data = data.get("persons", [])
                relationships_data = data.get("relationships", [])
            elif file_extension == ".csv":
                # Basic CSV: Assumes person data only, one file. Relationships need separate handling.
                with open(file_path, 'r', newline='', encoding='utf-8') as f:
                    # Decryption might be needed here if CSV is encrypted line-by-line or whole file
                    # Assuming plain CSV for now
                    reader = csv.DictReader(f)
                    persons_data = list(reader)
                logging.warning("CSV import currently only supports person data.")
            elif file_extension == ".xml":
                # Assuming plain XML for now, add decryption if needed
                tree = ET.parse(file_path)
                root = tree.getroot()
                persons_data = self._parse_persons_xml(root.find('persons'))
                relationships_data = self._parse_relationships_xml(root.find('relationships'))
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")

        except Exception as e:
            logging.error(f"Error loading data from {file_path}: {e}")
            raise # Re-raise the exception after logging

        return persons_data, relationships_data

    def _parse_persons_xml(self, persons_element: Optional[Element]) -> List[Dict]:
        """Parses person data from an XML element."""
        persons_data = []
        if persons_element is None:
            return persons_data
        for person_elem in persons_element.findall('person'):
            p_data = {'person_id': person_elem.get('person_id')}
            for child in person_elem:
                # Handle simple text elements, add logic for complex types/attributes if needed
                if child.tag not in p_data: # Avoid overwriting id
                     p_data[child.tag] = child.text
            if p_data.get('person_id'): # Need at least an ID
                 persons_data.append(p_data)
        return persons_data

    def _parse_relationships_xml(self, relationships_element: Optional[Element]) -> List[Dict]:
        """Parses relationship data from an XML element."""
        relationships_data = []
        if relationships_element is None:
             return relationships_data
        for rel_elem in relationships_element.findall('relationship'):
             r_data = {
                 'person1_id': rel_elem.findtext('person1_id'),
                 'person2_id': rel_elem.findtext('person2_id'),
                 'type': rel_elem.findtext('type'),
                 'attributes': {} # Add parsing for attributes if stored in XML
             }
             # Example attribute parsing:
             attrs_elem = rel_elem.find('attributes')
             if attrs_elem is not None:
                 for attr in attrs_elem:
                     r_data['attributes'][attr.tag] = attr.text

             if r_data['person1_id'] and r_data['person2_id'] and r_data['type']:
                 relationships_data.append(r_data)
        return relationships_data


    def import_file(self, file_path: str, user: str = "system", merge: bool = False) -> None:
        """
        Imports family tree data from a file (JSON, CSV, XML).

        Args:
            file_path: Path to the import file.
            user: User performing the import.
            merge: If True, merges data with existing tree. If False (default), clears existing data first.
        """
        self.audit_log.log_event(user, "import_started", f"Started import from {file_path}")
        logging.info(f"Starting import from {file_path} by user {user}. Merge={merge}")

        try:
            persons_data, relationships_data = self._load_data(file_path)

            if not merge:
                self.persons.clear()
                self.relationships.clear()
                logging.info("Cleared existing tree data before import.")

            # Import Persons
            added_persons = 0
            skipped_persons = 0
            for p_data in persons_data:
                person_id = p_data.get('person_id')
                if not person_id:
                    logging.warning(f"Skipping person data with missing ID: {p_data}")
                    skipped_persons += 1
                    continue
                if person_id in self.persons and merge:
                    # Optionally update existing person data if merging
                    logging.info(f"Person {person_id} already exists, skipping (or implement update logic).")
                    skipped_persons += 1
                    continue
                try:
                    # Create Person object, handling potential missing fields gracefully
                    person = Person(
                        person_id=person_id,
                        first_name=p_data.get('first_name', ''),
                        last_name=p_data.get('last_name', ''),
                        birth_date=p_data.get('birth_date'),
                        death_date=p_data.get('death_date'),
                        gender=p_data.get('gender'),
                        notes=p_data.get('notes'),
                        # Add other fields as needed
                    )
                    self.add_person(person, user=user) # Use add_person to handle logging/validation
                    added_persons += 1
                except ValueError as ve: # Catch duplicate ID errors from add_person
                    logging.warning(f"Skipping duplicate person ID during import: {ve}")
                    skipped_persons += 1
                except Exception as e:
                    logging.error(f"Error creating person object for ID {person_id}: {e} - Data: {p_data}")
                    skipped_persons += 1


            # Import Relationships (after all persons are potentially loaded)
            added_rels = 0
            skipped_rels = 0
            for r_data in relationships_data:
                p1_id = r_data.get('person1_id')
                p2_id = r_data.get('person2_id')
                rel_type = r_data.get('type') or r_data.get('rel_type') # Allow 'type' or 'rel_type'
                attributes = r_data.get('attributes')

                if not (p1_id and p2_id and rel_type):
                    logging.warning(f"Skipping relationship data with missing fields: {r_data}")
                    skipped_rels += 1
                    continue

                # Check if persons exist before adding relationship
                if p1_id not in self.persons or p2_id not in self.persons:
                     logging.warning(f"Skipping relationship for non-existent person(s): {p1_id} -> {p2_id} ({rel_type})")
                     skipped_rels +=1
                     continue

                try:
                    # Use add_relationship to handle reciprocal logic and logging
                    success = self.add_relationship(p1_id, p2_id, rel_type, attributes, user=user)
                    if success:
                        added_rels += 1
                    else:
                        # Relationship might have already existed if merge=True
                        logging.info(f"Relationship {p1_id} -> {p2_id} ({rel_type}) already existed or failed to add.")
                        skipped_rels += 1
                except ValueError as ve: # Catch self-relationships etc.
                    logging.warning(f"Skipping invalid relationship during import: {ve}")
                    skipped_rels += 1
                except Exception as e:
                    logging.error(f"Error adding relationship {p1_id} -> {p2_id}: {e} - Data: {r_data}")
                    skipped_rels += 1


            summary = f"Import from {file_path} completed. Added: {added_persons} persons, {added_rels} relationships. Skipped: {skipped_persons} persons, {skipped_rels} relationships."
            self.audit_log.log_event(user, "import_completed", summary)
            logging.info(summary)

        except FileNotFoundError as e:
            log_msg = f"Import failed: File not found - {e}"
            self.audit_log.log_event(user, "import_failed", log_msg)
            logging.error(log_msg)
            # Optionally re-raise or handle differently
        except Exception as e:
            log_msg = f"Import failed: An unexpected error occurred - {e}"
            self.audit_log.log_event(user, "import_failed", log_msg)
            logging.exception(f"Unexpected error during import from {file_path} by user {user}") # Log full traceback
            # Optionally re-raise or handle differently


    def _prepare_export_data(self) -> Dict[str, List[Dict]]:
        """Prepares person and relationship data for export."""
        persons_export = [p.to_dict() for p in self.persons.values()]
        relationships_export = []
        # Export only one direction to avoid duplicates, e.g., export p1->p2 but not p2->p1 if reciprocal
        exported_pairs = set()
        for p1_id, rel_list in self.relationships.items():
            for rel in rel_list:
                pair = tuple(sorted((rel.person1_id, rel.person2_id))) + (rel.rel_type,)
                reciprocal_type = get_reciprocal_relationship(rel.rel_type)
                reciprocal_pair = tuple(sorted((rel.person1_id, rel.person2_id))) + (reciprocal_type,)

                # Only export if this specific pair or its reciprocal hasn't been exported
                if pair not in exported_pairs and reciprocal_pair not in exported_pairs:
                    relationships_export.append(rel.to_dict())
                    exported_pairs.add(pair) # Mark this pair type as exported

        return {"persons": persons_export, "relationships": relationships_export}

    def export_file(self, file_path: str, user: str = "system") -> None:
        """
        Exports family tree data to a file (JSON, CSV, XML).

        Args:
            file_path: Path to the export file.
            user: User performing the export.
        """
        self.audit_log.log_event(user, "export_started", f"Started export to {file_path}")
        logging.info(f"Starting export to {file_path} by user {user}")

        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()

        try:
            export_data = self._prepare_export_data()

            if file_extension == ".json":
                json_string = json.dumps(export_data, indent=4, default=str) # Use default=str for non-serializable types like dates
                encrypted_data = self.encryptor.encrypt(json_string)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(encrypted_data)

            elif file_extension == ".csv":
                # Basic CSV export for persons only. Relationships are complex for single CSV.
                if not export_data["persons"]:
                     logging.warning("No person data to export to CSV.")
                     # Create empty file with header?
                     with open(file_path, 'w', newline='', encoding='utf-8') as f:
                          f.write("person_id,first_name,last_name,birth_date,death_date,gender,notes\n") # Example header
                else:
                     # Determine headers from the first person (or define explicitly)
                     headers = export_data["persons"][0].keys()
                     with open(file_path, 'w', newline='', encoding='utf-8') as f:
                         # Add encryption here if needed (encrypt rows or whole file)
                         writer = csv.DictWriter(f, fieldnames=headers)
                         writer.writeheader()
                         writer.writerows(export_data["persons"])
                logging.warning("CSV export currently only includes person data.")

            elif file_extension == ".xml":
                root = Element('family_tree')
                # Persons
                persons_elem = SubElement(root, 'persons')
                for p_data in export_data["persons"]:
                    person_elem = SubElement(persons_elem, 'person', person_id=str(p_data.get("person_id","")))
                    for key, value in p_data.items():
                        if key != "person_id" and value is not None: # Skip ID, handle None values
                            child = SubElement(person_elem, key)
                            child.text = str(value) # Convert all values to string for XML

                # Relationships
                relationships_elem = SubElement(root, 'relationships')
                for r_data in export_data["relationships"]:
                    rel_elem = SubElement(relationships_elem, 'relationship')
                    SubElement(rel_elem, 'person1_id').text = str(r_data.get('person1_id'))
                    SubElement(rel_elem, 'person2_id').text = str(r_data.get('person2_id'))
                    SubElement(rel_elem, 'type').text = str(r_data.get('rel_type')) # Use 'type' tag
                    # Add attributes if they exist
                    attributes = r_data.get('attributes')
                    if attributes:
                        attrs_elem = SubElement(rel_elem, 'attributes')
                        for key, value in attributes.items():
                             if value is not None:
                                 SubElement(attrs_elem, key).text = str(value)


                # Create ElementTree object from the root element
                tree = ElementTree(root)

                # Pretty print (indent) - requires Python 3.9+
                # Check if indent is available and use it
                try:
                    ET.indent(tree, space="\t", level=0) # Pass the ElementTree instance
                except AttributeError:
                     logging.warning("XML indentation (ET.indent) not available. Exporting unformatted XML. Requires Python 3.9+.")
                except TypeError as te:
                     # Catch the specific error observed if 'tree' is not an ElementTree instance
                     logging.error(f"XML indentation failed: Incorrect type passed to ET.indent. Error: {te}")
                     # Fallback to writing without indent? Or re-raise? For now, log and continue.

                # Write to file (add encryption if needed)
                # Use tree.write() which handles the XML declaration etc.
                try:
                    tree.write(file_path, encoding="utf-8", xml_declaration=True)
                except Exception as write_error:
                    logging.error(f"Failed to write XML tree to file {file_path}: {write_error}")
                    raise # Re-raise write error


            else:
                raise ValueError(f"Unsupported file format: {file_extension}")

            self.audit_log.log_event(user, "export_completed", f"Exported data to {file_path}")
            logging.info(f"Successfully exported data to {file_path}")

        except Exception as e:
            log_msg = f"Export failed: An unexpected error occurred - {e}"
            self.audit_log.log_event(user, "export_failed", log_msg)
            logging.exception(f"Unexpected error during export to {file_path} by user {user}") # Log full traceback
            # Raise a more specific error or handle as needed
            raise ValueError(f"Unexpected error during export: {e}") from e

    # Add other methods like search, generating reports, etc.
