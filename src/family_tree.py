# src/family_tree.py
import os
import csv
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any # Import necessary types

from src.person import Person
from src.relationship import Relationship, RELATIONSHIP_TYPES
# Import placeholder classes
from src.audit_log import AuditLog
from src.encryption import DataEncryptor

# Optional: Import gedcom library if installed
try:
    import gedcom.parser
    import gedcom.tags
    GEDCOM_AVAILABLE = True
except ImportError:
    GEDCOM_AVAILABLE = False
    print("Warning: 'gedcom-py' library not found. GEDCOM import/export disabled.")


class FamilyTree:
    """
    Manages a collection of Person objects and their relationships.

    Attributes:
        person_nodes (Dict[str, Person]): Dictionary mapping person_id to Person object.
        audit_log (AuditLog): Instance for logging changes (placeholder).
        data_encryptor (DataEncryptor): Instance for encrypting/decrypting data (placeholder).
        encryption_key (Optional[str]): Key used for encryption (placeholder).
    """
    def __init__(self,
                 audit_log: Optional[AuditLog] = None,
                 data_encryptor: Optional[DataEncryptor] = None,
                 encryption_key: Optional[str] = None):
        """
        Initializes the FamilyTree.

        Args:
            audit_log (Optional[AuditLog]): An instance of AuditLog for tracking changes.
            data_encryptor (Optional[DataEncryptor]): An instance for encryption.
            encryption_key (Optional[str]): The key for encryption.
        """
        self.person_nodes: Dict[str, Person] = {}
        self.audit_log = audit_log if audit_log else AuditLog() # Use placeholder if none provided
        self.data_encryptor = data_encryptor if data_encryptor else DataEncryptor() # Use placeholder
        self.encryption_key = encryption_key # Store encryption key

    def add_person(self, person: Person, user_id: str = "system"):
        """
        Adds a person to the family tree.

        Args:
            person (Person): The Person object to add.
            user_id (str): The ID of the user performing the action (for audit log).

        Raises:
            ValueError: If a person with the same ID already exists.
        """
        if person.person_id in self.person_nodes:
            raise ValueError(f"Person with ID {person.person_id} already exists in the family tree.")

        # Assign the tree reference to the person
        person.family_tree = self

        # Add person to the central dictionary
        self.person_nodes[person.person_id] = person

        self.audit_log.log_event(user_id, "person_added", f"Added person: {person.person_id} ({person.get_full_name()})")

        # Optional: Validate data upon adding
        # validation_errors = self.validate_person_data(person)
        # if validation_errors:
        #     # Decide how to handle validation errors (e.g., log warning, raise error)
        #     print(f"Warning: Validation errors for added person {person.person_id}: {validation_errors}")
        #     # self.delete_person(person.person_id, user_id) # Rollback?
        #     # raise ValueError(f"Invalid person data added: {validation_errors}")


    def get_person_by_id(self, person_id: str) -> Optional[Person]:
        """
        Retrieves a person from the tree by their ID.

        Args:
            person_id (str): The ID of the person to retrieve.

        Returns:
            Optional[Person]: The Person object if found, otherwise None.
        """
        return self.person_nodes.get(person_id)

    def link_persons(self, relationship: Relationship, user_id: str = "system"):
        """
        Adds a relationship between two persons already in the tree.

        Args:
            relationship (Relationship): The relationship object to add.
            user_id (str): The ID of the user performing the action.

        Raises:
            ValueError: If either person in the relationship is not found,
                        or if the relationship is invalid (e.g., self-link).
        """
        person1 = self.get_person_by_id(relationship.person1_id)
        person2 = self.get_person_by_id(relationship.person2_id)

        if not person1:
            raise ValueError(f"Person 1 with ID {relationship.person1_id} not found in the family tree.")
        if not person2:
            raise ValueError(f"Person 2 with ID {relationship.person2_id} not found in the family tree.")

        # Add the relationship to both involved persons' relationship lists
        person1.add_relationship(relationship)
        person2.add_relationship(relationship)

        self.audit_log.log_event(user_id, "relationship_added", f"Added relationship: {relationship}")

        # Optional: Check consistency after adding
        # consistency_errors = self.check_relationship_consistency(person1.person_id) + \
        #                      self.check_relationship_consistency(person2.person_id)
        # if consistency_errors:
        #      print(f"Warning: Potential consistency issues after adding relationship {relationship}: {consistency_errors}")
        #      # Decide how to handle: log, raise error, attempt auto-fix?


    def unlink_persons(self, relationship: Relationship, user_id: str = "system"):
        """
        Removes a relationship between two persons.

        Args:
            relationship (Relationship): The relationship object to remove.
            user_id (str): The ID of the user performing the action.

        Raises:
            ValueError: If either person is not found or the relationship doesn't exist for them.
        """
        person1 = self.get_person_by_id(relationship.person1_id)
        person2 = self.get_person_by_id(relationship.person2_id)

        if not person1:
            raise ValueError(f"Person 1 with ID {relationship.person1_id} not found.")
        if not person2:
            raise ValueError(f"Person 2 with ID {relationship.person2_id} not found.")

        try:
            person1.remove_relationship(relationship)
            person2.remove_relationship(relationship)
            self.audit_log.log_event(user_id, "relationship_removed", f"Removed relationship: {relationship}")
        except ValueError as e:
            # Relationship might not exist for one or both, raise error
            raise ValueError(f"Could not remove relationship {relationship}: {e}")


    def delete_person(self, person_id: str, user_id: str = "system"):
        """
        Deletes a person and all relationships involving them from the tree.

        Args:
            person_id (str): The ID of the person to delete.
            user_id (str): The ID of the user performing the action.

        Raises:
            ValueError: If the person with the given ID is not found.
        """
        person_to_delete = self.get_person_by_id(person_id)
        if not person_to_delete:
            raise ValueError(f"Person with ID {person_id} not found.")

        # Find all relationships involving this person
        relationships_to_remove = list(person_to_delete.relationships) # Copy list before iterating

        # Remove the relationships from the other involved persons
        for rel in relationships_to_remove:
            other_person_id = rel.get_other_person(person_id)
            if other_person_id:
                other_person = self.get_person_by_id(other_person_id)
                if other_person:
                    try:
                        other_person.remove_relationship(rel)
                        self.audit_log.log_event(user_id, "relationship_removed", f"Removed relationship involving deleted person {person_id}: {rel}")
                    except ValueError:
                        # Should not happen if data is consistent, but log if it does
                        print(f"Warning: Relationship {rel} not found on person {other_person_id} during deletion of {person_id}.")

        # Remove the person node itself
        del self.person_nodes[person_id]
        self.audit_log.log_event(user_id, "person_deleted", f"Deleted person: {person_id} ({person_to_delete.get_full_name()})")


    def validate_person_data(self, person: Person) -> List[str]:
        """
        Validates the data of a single person. (Basic Example)

        Args:
            person (Person): The person to validate.

        Returns:
            List[str]: A list of validation error messages.
        """
        errors = []
        if not person.names:
            errors.append("Person must have at least one name.")
        if person.date_of_birth and person.date_of_death and person.date_of_birth > person.date_of_death:
            errors.append(f"Date of death ({person.date_of_death}) cannot be before date of birth ({person.date_of_birth}).")

        # Add more validation rules as needed (e.g., email format, URL format, date ranges)
        if person.profile_photo:
            # Basic URL check (can be improved)
            from urllib.parse import urlparse
            try:
                result = urlparse(person.profile_photo)
                if not all([result.scheme, result.netloc]):
                     errors.append(f"Profile photo URL is invalid: {person.profile_photo}")
            except ValueError:
                 errors.append(f"Profile photo URL is invalid: {person.profile_photo}")

        # Validate privacy settings keys/values?

        return errors

    def check_relationship_consistency(self, person_id: str) -> List[str]:
        """
        Checks for logical inconsistencies in a person's relationships. (Basic Example)

        Args:
            person_id (str): The ID of the person whose relationships to check.

        Returns:
            List[str]: A list of consistency error messages.
        """
        errors = []
        person = self.get_person_by_id(person_id)
        if not person:
            # This case should ideally not happen if called internally
            return [f"Consistency check failed: Person {person_id} not found."]

        # Check 1: Reciprocity (Spouse, Sibling, Friend)
        symmetric_types = ["spouse", "sibling", "friend"]
        for rel in person.relationships:
            other_person_id = rel.get_other_person(person_id)
            other_person = self.get_person_by_id(other_person_id) if other_person_id else None

            if not other_person:
                errors.append(f"Consistency Error (Person {person_id}): Related person {other_person_id} in relationship {rel} not found in tree.")
                continue # Skip further checks for this relationship

            # Check if the other person also has this relationship recorded
            if rel not in other_person.relationships:
                 errors.append(f"Consistency Error (Person {person_id}): Relationship {rel} with {other_person_id} is not recorded on the other person.")

            # Specific checks based on type
            if rel.relationship_type == "parent": # P1 is parent of P2
                # Check if P2 has a corresponding 'child' relationship with P1
                found_child_rel = any(
                    r.relationship_type == 'child' and r.get_other_person(other_person_id) == person_id
                    for r in other_person.relationships
                )
                if not found_child_rel:
                     errors.append(f"Consistency Error (Person {person_id}): 'parent' relationship with {other_person_id} lacks corresponding 'child' relationship on {other_person_id}.")

            elif rel.relationship_type == "child": # P1 is child of P2
                # Check if P2 has a corresponding 'parent' relationship with P1
                found_parent_rel = any(
                    r.relationship_type == 'parent' and r.get_other_person(other_person_id) == person_id
                    for r in other_person.relationships
                )
                if not found_parent_rel:
                     errors.append(f"Consistency Error (Person {person_id}): 'child' relationship with {other_person_id} lacks corresponding 'parent' relationship on {other_person_id}.")

        # Check 2: Parent/Child Age Logic
        person_dob = person.date_of_birth
        if person_dob:
            for parent_id in person.get_parents():
                parent = self.get_person_by_id(parent_id)
                if parent and parent.date_of_birth and parent.date_of_birth >= person_dob:
                    errors.append(f"Consistency Error (Person {person_id}): Parent {parent_id} DOB ({parent.date_of_birth}) is not before child's DOB ({person_dob}).")
            for child_id in person.get_children():
                child = self.get_person_by_id(child_id)
                if child and child.date_of_birth and child.date_of_birth <= person_dob:
                     errors.append(f"Consistency Error (Person {person_id}): Child {child_id} DOB ({child.date_of_birth}) is not after parent's DOB ({person_dob}).")

        # Add more checks: e.g., cannot be own parent/child/sibling, marriage dates vs birth/death dates

        return errors

    def check_all_relationship_consistency(self, user_id: str = "system") -> Dict[str, List[str]]:
        """
        Checks consistency for all persons in the tree.

        Args:
            user_id (str): User performing the check (for audit log).

        Returns:
            Dict[str, List[str]]: A dictionary mapping person_id to a list of consistency errors found for them.
        """
        all_errors = {}
        self.audit_log.log_event(user_id, "consistency_check_start", "Starting full relationship consistency check.")
        for person_id in list(self.person_nodes.keys()): # Use list to avoid issues if nodes are deleted during check
            errors = self.check_relationship_consistency(person_id)
            if errors:
                all_errors[person_id] = errors
        self.audit_log.log_event(user_id, "consistency_check_end", f"Finished full consistency check. Issues found for {len(all_errors)} persons.")
        return all_errors

    def find_duplicates(self, threshold: float = 0.8) -> List[Tuple[Person, Person, float]]:
        """
        Finds potential duplicate persons based on name and birth date similarity. (Basic Example)

        Args:
            threshold (float): Similarity score threshold (0.0 to 1.0) for considering a match.

        Returns:
            List[Tuple[Person, Person, float]]: List of tuples, each containing two potential duplicate Person objects and their similarity score.
        """
        duplicates: List[Tuple[Person, Person, float]] = []
        person_ids = list(self.person_nodes.keys())
        checked_pairs: Set[Tuple[str, str]] = set()

        # Very basic similarity check - needs improvement (e.g., fuzzy matching libraries)
        def calculate_similarity(p1: Person, p2: Person) -> float:
            score = 0.0
            # Name similarity (exact match for now)
            name1 = p1.get_full_name()
            name2 = p2.get_full_name()
            if name1 and name1 == name2:
                score += 0.6
            # Birth date similarity (exact match for now)
            if p1.date_of_birth and p1.date_of_birth == p2.date_of_birth:
                score += 0.4
            # Birth place similarity? Other fields?
            return score

        for i in range(len(person_ids)):
            for j in range(i + 1, len(person_ids)):
                id1, id2 = person_ids[i], person_ids[j]
                pair = tuple(sorted((id1, id2)))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                person1 = self.person_nodes[id1]
                person2 = self.person_nodes[id2]

                similarity = calculate_similarity(person1, person2)

                if similarity >= threshold:
                    duplicates.append((person1, person2, similarity))

        # Sort by similarity score descending
        duplicates.sort(key=lambda item: item[2], reverse=True)
        return duplicates

    def merge_persons(self, primary_person_id: str, duplicate_person_id: str, user_id: str = "system"):
        """
        Merges data from the duplicate person into the primary person and deletes the duplicate. (Basic Example)

        Args:
            primary_person_id (str): The ID of the person to keep.
            duplicate_person_id (str): The ID of the person to merge and delete.
            user_id (str): The ID of the user performing the merge.

        Raises:
            ValueError: If either person ID is not found or if they are the same ID.
        """
        if primary_person_id == duplicate_person_id:
            raise ValueError("Cannot merge a person with themselves.")

        primary_person = self.get_person_by_id(primary_person_id)
        duplicate_person = self.get_person_by_id(duplicate_person_id)

        if not primary_person:
            raise ValueError(f"Primary person {primary_person_id} not found.")
        if not duplicate_person:
            raise ValueError(f"Duplicate person {duplicate_person_id} not found.")

        self.audit_log.log_event(user_id, "merge_start", f"Starting merge of {duplicate_person_id} into {primary_person_id}.")

        # --- Merge Logic (Needs careful implementation based on desired strategy) ---
        # Example: Add unique names, affiliations, documents, etc., from duplicate to primary
        for name_entry in duplicate_person.names:
            try:
                primary_person.add_name(**name_entry) # Add if not present
            except ValueError: # Handle potential duplicate errors if add_name raises them
                pass # Ignore if already exists

        # Merge other list attributes (simple concatenation, avoid duplicates)
        for doc in duplicate_person.documents: primary_person.add_document(doc)
        # ... merge media, affiliations, histories, etc. ...

        # Merge dictionary attributes (more complex - decide how to handle conflicts)
        # Example: Merge cultural relationships
        for rel_type, person_ids in duplicate_person.cultural_relationships.items():
             for p_id in person_ids:
                 try:
                     primary_person.add_cultural_relationship(rel_type, p_id)
                 except ValueError: pass # Ignore if exists

        # --- Re-link Relationships ---
        # Find all relationships involving the duplicate person
        rels_to_relink = list(duplicate_person.relationships) # Copy before modifying

        for rel in rels_to_relink:
            # Create a new relationship object pointing to the primary person
            new_rel_data = rel.to_dict()
            if new_rel_data['person1_id'] == duplicate_person_id:
                new_rel_data['person1_id'] = primary_person_id
            else: # person2_id must be the duplicate
                new_rel_data['person2_id'] = primary_person_id

            # Avoid creating duplicate relationships on the primary person
            try:
                 new_rel = Relationship.from_dict(new_rel_data)
                 # Check if an equivalent relationship already exists for the primary person
                 if new_rel not in primary_person.relationships:
                     self.link_persons(new_rel, user_id=f"{user_id}-merge") # Add the re-linked relationship
                 else:
                     self.audit_log.log_event(user_id, "merge_info", f"Skipped adding duplicate relationship during merge: {new_rel}")

            except ValueError as e:
                 self.audit_log.log_event(user_id, "merge_warning", f"Could not re-link relationship {rel} during merge: {e}")


        # --- Delete the duplicate person ---
        # Deleting the duplicate will also clean up its relationships from others
        try:
            self.delete_person(duplicate_person_id, user_id=f"{user_id}-merge")
        except ValueError as e:
             # Should not happen if checks passed, but log if it does
             self.audit_log.log_event(user_id, "merge_error", f"Error deleting duplicate person {duplicate_person_id} after merge: {e}")
             # Consider rollback strategy?

        self.audit_log.log_event(user_id, "merge_complete", f"Completed merge of {duplicate_person_id} into {primary_person_id}.")


    # --- Import/Export Methods ---

    def _load_data(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Helper to load persons and relationships from various formats."""
        persons_data = []
        relationships_data = []
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Import file not found: {file_path}")

        try:
            if ext == ".json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    # --- Placeholder Decryption ---
                    if isinstance(raw_data, dict) and "encrypted_data" in raw_data:
                        print("Placeholder: Decrypting JSON data...")
                        # decrypted_str = self.data_encryptor.decrypt_data(raw_data["encrypted_data"], self.encryption_key)
                        # data = json.loads(decrypted_str)
                        data = json.loads(raw_data["encrypted_data"]) # Assume not actually encrypted for now
                    else:
                        data = raw_data # Assume plain JSON

                    persons_data = data.get("persons", [])
                    relationships_data = data.get("relationships", [])
            elif ext == ".csv":
                 with open(file_path, 'r', encoding='utf-8', newline='') as f:
                     reader = csv.DictReader(f)
                     # Simple CSV: assumes each row is a person, relationships need separate handling/file
                     for row in reader:
                          # Map CSV columns to Person attributes
                          # Handle potential missing columns gracefully
                          persons_data.append({
                              "person_id": row.get("person_id"),
                              "creator_user_id": row.get("creator_user_id", "csv_import"),
                              "first_name": row.get("first_name"),
                              "last_name": row.get("last_name"),
                              "gender": row.get("gender"),
                              "date_of_birth": row.get("date_of_birth"),
                              "place_of_birth": row.get("place_of_birth"),
                              "date_of_death": row.get("date_of_death"),
                              "place_of_death": row.get("place_of_death"),
                              # Add other fields as needed
                          })
                 # Relationships might need to be loaded from a separate CSV or inferred
            elif ext == ".xml":
                 tree = ET.parse(file_path)
                 root = tree.getroot()
                 for person_elem in root.findall(".//person"): # Find person elements anywhere
                      persons_data.append(person_elem.attrib) # Assumes attributes match Person fields
                 for rel_elem in root.findall(".//relationship"): # Find relationship elements
                      relationships_data.append(rel_elem.attrib) # Assumes attributes match Relationship fields
            elif ext == ".ged" and GEDCOM_AVAILABLE:
                 persons_data, relationships_data = self._parse_gedcom(file_path)
            else:
                raise ValueError(f"Unsupported import file format: {ext}. Supported: .json, .csv, .xml, .ged (if library installed)")

        except FileNotFoundError:
             raise
        except json.JSONDecodeError as e:
             raise ValueError(f"Invalid JSON format in {file_path}: {e}")
        except ET.ParseError as e:
             raise ValueError(f"Invalid XML format in {file_path}: {e}")
        except Exception as e: # Catch other potential errors during loading
            raise ValueError(f"Error loading data from {file_path}: {e}")

        return persons_data, relationships_data

    def import_file(self, file_path: str, user_id: str = "system"):
        """
        Imports persons and relationships from a file (JSON, CSV, XML, GEDCOM).
        This will clear the current tree before importing.
        """
        self.audit_log.log_event(user_id, "import_start", f"Starting import from {file_path}.")
        try:
            persons_data, relationships_data = self._load_data(file_path)

            # Clear existing tree data
            self.person_nodes.clear()
            self.audit_log.log_event(user_id, "import_info", "Cleared existing tree data before import.")

            # Import Persons
            imported_person_ids = set()
            for p_data in persons_data:
                try:
                    # Ensure required fields are present
                    if not p_data.get('person_id') or not p_data.get('first_name') or not p_data.get('last_name'):
                         print(f"Warning: Skipping person record due to missing ID or name: {p_data}")
                         continue

                    # Create Person object (pass encryption key if needed)
                    person = Person(
                        creator_user_id=p_data.get("creator_user_id", user_id),
                        person_id=p_data["person_id"],
                        first_name=p_data["first_name"],
                        last_name=p_data["last_name"],
                        date_of_birth=p_data.get("date_of_birth"),
                        place_of_birth=p_data.get("place_of_birth"),
                        gender=p_data.get("gender"),
                        date_of_death=p_data.get("date_of_death"),
                        place_of_death=p_data.get("place_of_death"),
                        family_tree=self,
                        encryption_key=self.encryption_key # Pass key
                    )
                    # Add other attributes from p_data if necessary
                    # person.biography = p_data.get("biography", "")
                    # ... etc.

                    self.add_person(person, user_id=f"{user_id}-import")
                    imported_person_ids.add(person.person_id)
                except ValueError as e:
                    print(f"Warning: Skipping person during import due to error: {e}. Data: {p_data}")
                except Exception as e:
                     print(f"Warning: Unexpected error importing person {p_data.get('person_id')}: {e}")


            # Import Relationships
            imported_relationships = 0
            for r_data in relationships_data:
                 try:
                     # Check if both persons exist
                     p1_id = r_data.get("person1_id")
                     p2_id = r_data.get("person2_id")
                     if p1_id in imported_person_ids and p2_id in imported_person_ids:
                          relationship = Relationship.from_dict(r_data)
                          self.link_persons(relationship, user_id=f"{user_id}-import")
                          imported_relationships += 1
                     else:
                          print(f"Warning: Skipping relationship due to missing person(s): {r_data}")

                 except ValueError as e:
                      print(f"Warning: Skipping relationship during import due to error: {e}. Data: {r_data}")
                 except Exception as e:
                      print(f"Warning: Unexpected error importing relationship {r_data}: {e}")

            self.audit_log.log_event(user_id, "import_complete", f"Import from {file_path} complete. Added {len(imported_person_ids)} persons and {imported_relationships} relationships.")

        except (FileNotFoundError, ValueError) as e:
            self.audit_log.log_event(user_id, "import_failed", f"Import from {file_path} failed: {e}")
            raise # Re-raise the exception
        except Exception as e:
             self.audit_log.log_event(user_id, "import_failed", f"Unexpected error during import from {file_path}: {e}")
             raise ValueError(f"Unexpected error during import: {e}")


    def _get_export_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Helper to gather persons and unique relationships for export."""
        persons_export_data = []
        relationships_export_data = []
        exported_relationship_hashes = set()

        for person in self.person_nodes.values():
            persons_export_data.append(person.get_person_info()) # Use person's method to get data
            for rel in person.relationships:
                rel_hash = hash(rel) # Use hash based on __hash__ implementation
                if rel_hash not in exported_relationship_hashes:
                     relationships_export_data.append(rel.to_dict())
                     exported_relationship_hashes.add(rel_hash)

        return persons_export_data, relationships_export_data

    def export_file(self, file_path: str, user_id: str = "system"):
        """
        Exports the current family tree data to a file (JSON, CSV, XML, GEDCOM).
        """
        self.audit_log.log_event(user_id, "export_start", f"Starting export to {file_path}.")
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        try:
            persons_data, relationships_data = self._get_export_data()

            if not persons_data and not relationships_data:
                 print("Warning: Exporting an empty tree.")
                 # Create an empty file? Or raise error?

            if ext == ".json":
                data_to_export = {"persons": persons_data, "relationships": relationships_data}
                json_string = json.dumps(data_to_export, indent=4, ensure_ascii=False)

                # --- Placeholder Encryption ---
                if self.encryption_key:
                     print("Placeholder: Encrypting JSON data...")
                     # encrypted_json = self.data_encryptor.encrypt_data(json_string, self.encryption_key)
                     # output_data = {"encrypted_data": encrypted_json}
                     output_data = {"encrypted_data": json_string} # Store plain string for now
                else:
                     output_data = data_to_export # Store plain dict

                with open(file_path, 'w', encoding='utf-8') as f:
                     json.dump(output_data, f, indent=4, ensure_ascii=False)

            elif ext == ".csv":
                 # Simple CSV export (only person data, relationships ignored)
                 if not persons_data:
                      print("Warning: No person data to export to CSV.")
                      # Create empty file with headers?
                      fieldnames = ["person_id", "creator_user_id", "first_name", "last_name", "gender", "date_of_birth", "place_of_birth", "date_of_death", "place_of_death"] # Add more?
                      with open(file_path, 'w', encoding='utf-8', newline='') as f:
                           writer = csv.DictWriter(f, fieldnames=fieldnames)
                           writer.writeheader()
                 else:
                      # Use keys from the first person's data as headers (may vary if data is inconsistent)
                      fieldnames = list(persons_data[0].keys())
                      with open(file_path, 'w', encoding='utf-8', newline='') as f:
                           writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore') # Ignore extra fields
                           writer.writeheader()
                           for person_row in persons_data:
                                # Convert datetime objects back to strings for CSV
                                row_to_write = person_row.copy()
                                if isinstance(row_to_write.get('date_of_birth'), datetime):
                                     row_to_write['date_of_birth'] = row_to_write['date_of_birth'].isoformat()
                                if isinstance(row_to_write.get('date_of_death'), datetime):
                                     row_to_write['date_of_death'] = row_to_write['date_of_death'].isoformat()
                                # Convert list/dict fields to simple strings if needed
                                for key, value in row_to_write.items():
                                     if isinstance(value, (list, dict)):
                                          row_to_write[key] = json.dumps(value) # Store as JSON string
                                writer.writerow(row_to_write)

            elif ext == ".xml":
                 root = ET.Element("family_tree")
                 persons_root = ET.SubElement(root, "persons")
                 relationships_root = ET.SubElement(root, "relationships")

                 for p_data in persons_data:
                      # Convert complex types to strings for XML attributes/text
                      xml_p_data = {}
                      for key, value in p_data.items():
                           if isinstance(value, datetime):
                                xml_p_data[key] = value.isoformat()
                           elif isinstance(value, (list, dict)):
                                xml_p_data[key] = json.dumps(value) # Store complex types as JSON string
                           elif value is not None:
                                xml_p_data[key] = str(value)
                           # else: skip None values

                      ET.SubElement(persons_root, "person", **xml_p_data) # Use attributes

                 for r_data in relationships_data:
                      xml_r_data = {}
                      for key, value in r_data.items():
                           if isinstance(value, datetime):
                                xml_r_data[key] = value.isoformat()
                           elif value is not None:
                                xml_r_data[key] = str(value)
                           # else: skip None values
                      ET.SubElement(relationships_root, "relationship", **xml_r_data)

                 tree = ET.ElementTree(root)
                 ET.indent(tree, space="\t", level=0) # Pretty print
                 tree.write(file_path, encoding="utf-8", xml_declaration=True)

            elif ext == ".ged" and GEDCOM_AVAILABLE:
                 self._write_gedcom(file_path, persons_data, relationships_data)
            else:
                 raise ValueError(f"Unsupported export file format: {ext}. Supported: .json, .csv, .xml, .ged (if library installed)")

            self.audit_log.log_event(user_id, "export_complete", f"Export to {file_path} complete.")

        except (IOError, ValueError) as e:
            self.audit_log.log_event(user_id, "export_failed", f"Export to {file_path} failed: {e}")
            raise # Re-raise exception
        except Exception as e:
             self.audit_log.log_event(user_id, "export_failed", f"Unexpected error during export to {file_path}: {e}")
             raise ValueError(f"Unexpected error during export: {e}")


    # --- GEDCOM Specific Methods (requires gedcom-py) ---

    def _parse_gedcom(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Parses a GEDCOM file into person and relationship dictionaries."""
        if not GEDCOM_AVAILABLE:
            raise ImportError("GEDCOM library not available.")

        persons_data = []
        relationships_data = []
        gedcom_parser = gedcom.parser.Parser()

        try:
            gedcom_parser.parse_file(file_path, False) # False = don't follow pointers yet
            elements = gedcom_parser.get_element_list()
            persons_map = {} # Store temp person data keyed by GEDCOM pointer

            # Pass 1: Extract Individuals (INDI)
            for element in elements:
                if element.get_tag() == gedcom.tags.GEDCOM_TAG_INDIVIDUAL:
                    pointer = element.get_pointer()
                    person_id = pointer.replace("@", "") # Use GEDCOM pointer as initial ID
                    p_data = {"person_id": person_id, "creator_user_id": "gedcom_import"}

                    name_parts = element.get_name() # Returns (first, last)
                    p_data["first_name"] = name_parts[0] if name_parts[0] else "Unknown"
                    p_data["last_name"] = name_parts[1] if name_parts[1] else "Unknown"

                    birth_event = element.get_birth_data() # Returns (date, place)
                    p_data["date_of_birth"] = birth_event[0] # Keep as string for now
                    p_data["place_of_birth"] = birth_event[1]

                    death_event = element.get_death_data()
                    p_data["date_of_death"] = death_event[0]
                    p_data["place_of_death"] = death_event[1]

                    p_data["gender"] = element.get_gender()

                    # Add other fields if needed (e.g., notes, sources)
                    persons_data.append(p_data)
                    persons_map[pointer] = p_data # Store for relationship linking

            # Pass 2: Extract Families (FAM) and create relationships
            for element in elements:
                if element.get_tag() == gedcom.tags.GEDCOM_TAG_FAMILY:
                    fam_pointer = element.get_pointer()
                    husb_pointer = element.get_husband()
                    wife_pointer = element.get_wife()
                    child_pointers = element.get_children()

                    husb_id = husb_pointer.replace("@", "") if husb_pointer else None
                    wife_id = wife_pointer.replace("@", "") if wife_pointer else None

                    # Create Spouse relationship
                    if husb_id and wife_id:
                        # Check if persons exist before adding relationship
                        if persons_map.get(husb_pointer) and persons_map.get(wife_pointer):
                             relationships_data.append({
                                 "person1_id": husb_id,
                                 "person2_id": wife_id,
                                 "relationship_type": "spouse",
                                 # Add marriage date/place if available in FAM record
                             })
                        else:
                             print(f"Warning: Skipping spouse relationship in FAM {fam_pointer} due to missing person(s).")


                    # Create Parent/Child relationships
                    parent_ids = [p_id for p_id in [husb_id, wife_id] if p_id]
                    for child_pointer in child_pointers:
                        child_id = child_pointer.replace("@", "")
                        # Check if child exists
                        if not persons_map.get(child_pointer):
                            print(f"Warning: Skipping parent/child relationship in FAM {fam_pointer} for child {child_id} (child not found).")
                            continue

                        for parent_id in parent_ids:
                             # Check if parent exists
                             parent_pointer = f"@{parent_id}@"
                             if persons_map.get(parent_pointer):
                                 # Add PARENT relationship (Parent is P1, Child is P2)
                                 relationships_data.append({
                                     "person1_id": parent_id,
                                     "person2_id": child_id,
                                     "relationship_type": "parent"
                                 })
                                 # Add CHILD relationship (Child is P1, Parent is P2)
                                 relationships_data.append({
                                     "person1_id": child_id,
                                     "person2_id": parent_id,
                                     "relationship_type": "child"
                                 })
                             else:
                                  print(f"Warning: Skipping parent/child relationship in FAM {fam_pointer} for parent {parent_id} (parent not found).")

        except Exception as e:
            raise ValueError(f"Error parsing GEDCOM file {file_path}: {e}")

        return persons_data, relationships_data


    def _write_gedcom(self, file_path: str, persons_data: List[Dict], relationships_data: List[Dict]):
        """Writes person and relationship data to a GEDCOM file."""
        if not GEDCOM_AVAILABLE:
            raise ImportError("GEDCOM library not available.")

        # Basic GEDCOM structure - might need refinement for complex data
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                # Header
                f.write("0 HEAD\n")
                f.write("1 SOUR DzinzaApp\n")
                f.write("2 VERS 1.0\n")
                f.write("1 CHAR UTF-8\n")
                f.write("1 GEDC\n")
                f.write("2 VERS 5.5.1\n") # GEDCOM version
                f.write("2 FORM LINEAGE-LINKED\n")

                # Individuals (INDI)
                person_map = {p["person_id"]: p for p in persons_data} # For quick lookup
                for p_data in persons_data:
                    person_id = p_data["person_id"]
                    f.write(f"0 @{person_id}@ INDI\n")
                    # Name - assuming first/last are in names list
                    first_name = next((n['name'] for n in p_data.get('names', []) if n.get('type') == 'first'), 'Unknown')
                    last_name = next((n['name'] for n in p_data.get('names', []) if n.get('type') == 'last'), 'Unknown')
                    f.write(f"1 NAME {first_name} /{last_name}/\n")
                    if p_data.get("gender"): f.write(f"1 SEX {p_data['gender']}\n")
                    # Birth
                    if p_data.get("date_of_birth") or p_data.get("place_of_birth"):
                        f.write("1 BIRT\n")
                        if p_data.get("date_of_birth"): f.write(f"2 DATE {p_data['date_of_birth']}\n") # Assumes string format
                        if p_data.get("place_of_birth"): f.write(f"2 PLAC {p_data['place_of_birth']}\n")
                    # Death
                    if p_data.get("date_of_death") or p_data.get("place_of_death"):
                        f.write("1 DEAT\n")
                        if p_data.get("date_of_death"): f.write(f"2 DATE {p_data['date_of_death']}\n")
                        if p_data.get("place_of_death"): f.write(f"2 PLAC {p_data['place_of_death']}\n")
                    # Add links to families later

                # Families (FAM) - Group relationships by family unit
                # This requires identifying spouses and their children
                family_units = {} # Key: tuple(sorted(spouse_ids)), Value: list(child_ids)
                processed_spouses = set()
                processed_children_in_fam = set()

                for r_data in relationships_data:
                     # Identify spouse pairs
                     if r_data["relationship_type"] == "spouse":
                          s1, s2 = sorted((r_data["person1_id"], r_data["person2_id"]))
                          spouse_pair = (s1, s2)
                          if spouse_pair not in family_units:
                               family_units[spouse_pair] = []
                          processed_spouses.add(s1)
                          processed_spouses.add(s2)

                     # Identify children linked to parents
                     elif r_data["relationship_type"] == "parent": # P1 is parent, P2 is child
                          parent_id = r_data["person1_id"]
                          child_id = r_data["person2_id"]
                          # Find the family unit this child belongs to
                          for spouses, children in family_units.items():
                               if parent_id in spouses:
                                    if child_id not in children:
                                         children.append(child_id)
                                    processed_children_in_fam.add(child_id)
                                    break # Assume child belongs to only one family unit for simplicity


                fam_counter = 1
                for spouses, children in family_units.items():
                    fam_id = f"F{fam_counter}"
                    f.write(f"0 @{fam_id}@ FAM\n")
                    if len(spouses) > 0: f.write(f"1 HUSB @{spouses[0]}@\n") # Assumes first is husband
                    if len(spouses) > 1: f.write(f"1 WIFE @{spouses[1]}@\n") # Assumes second is wife
                    for child_id in children:
                         f.write(f"1 CHIL @{child_id}@\n")
                    fam_counter += 1
                    # Link persons back to this family
                    for spouse_id in spouses:
                        f.write(f"0 @{spouse_id}@ INDI\n")
                        f.write(f"1 FAMS @{fam_id}@\n") # Family where spouse
                    for child_id in children:
                         f.write(f"0 @{child_id}@ INDI\n")
                         f.write(f"1 FAMC @{fam_id}@\n") # Family where child


                # Handle single parents? Handle persons not in families?

                # Trailer
                f.write("0 TRLR\n")

        except Exception as e:
            raise ValueError(f"Error writing GEDCOM file {file_path}: {e}")

    # --- Reporting and Display ---

    def display_tree(self, start_person_id: Optional[str] = None, max_depth: int = 5):
        """
        Displays the family tree structure starting from a person. (Basic Console Example)

        Args:
            start_person_id (Optional[str]): The ID of the person to start from.
                                             If None, attempts to display all components.
            max_depth (int): Maximum depth to traverse from the start person.
        """
        print("\n--- Family Tree Display ---")
        if not self.person_nodes:
            print("Tree is empty.")
            return

        visited = set()

        def print_branch(person_id: str, indent: int = 0):
            if person_id in visited or indent >= max_depth:
                return
            visited.add(person_id)

            person = self.get_person_by_id(person_id)
            if not person:
                print("  " * indent + f"[Error: Person {person_id} not found]")
                return

            dob = person.date_of_birth.strftime('%Y-%m-%d') if person.date_of_birth else "?"
            dod = person.date_of_death.strftime('%Y-%m-%d') if person.date_of_death else ""
            life_span = f"({dob} - {dod})" if dod else f"({dob})"

            print("  " * indent + f"- {person.get_full_name()} [{person.person_id[:6]}...] {life_span}")

            # Display spouses on the same level
            spouse_ids = person.get_spouses()
            for spouse_id in spouse_ids:
                 # Avoid infinite loops with visited check
                 if spouse_id not in visited:
                     spouse = self.get_person_by_id(spouse_id)
                     if spouse:
                          print("  " * indent + f"  Spouse: {spouse.get_full_name()} [{spouse_id[:6]}...]")
                     # Mark spouse as visited *for this branch level* to avoid re-printing as main node immediately
                     # visited.add(spouse_id) # Careful: this might prevent showing their own branch later

            # Recurse for children
            child_ids = person.get_children()
            for child_id in child_ids:
                print_branch(child_id, indent + 1)

        if start_person_id:
            if start_person_id not in self.person_nodes:
                 print(f"Start person with ID {start_person_id} not found.")
            else:
                 print(f"Displaying branch starting from {start_person_id}:")
                 print_branch(start_person_id)
        else:
            print("Displaying all tree components (up to depth 5):")
            # Find potential roots (persons with no parents in the tree) or just iterate all
            processed_nodes = set()
            for person_id in self.person_nodes:
                 if person_id not in visited:
                     # Check if it's a potential root or just an unvisited node
                     person = self.get_person_by_id(person_id)
                     # Simplified: just print any unvisited node as a starting point
                     if person:
                          print(f"\nComponent starting from {person_id}:")
                          print_branch(person_id)


    def search_person(self, query: str, fields: Optional[List[str]] = None) -> List[Person]:
        """
        Searches for persons matching the query in specified fields.

        Args:
            query (str): The search term (case-insensitive).
            fields (Optional[List[str]]): List of Person attributes (as strings) to search within.
                                         If None, searches common fields like names, birth/death places.

        Returns:
            List[Person]: A list of matching Person objects.
        """
        results = []
        query_lower = query.lower()

        if fields is None:
            # Default fields to search if none provided
            fields = ["names", "place_of_birth", "place_of_death"] # Add more defaults?

        for person in self.person_nodes.values():
            match_found = False
            for field in fields:
                try:
                    value = getattr(person, field, None)
                    if value is None:
                        continue

                    value_str = ""
                    if field == "names":
                        # Search within all name parts
                        value_str = " ".join(f"{n.get('name', '')}" for n in value).lower()
                    elif isinstance(value, list):
                         # Search within list elements (e.g., affiliations, documents)
                         value_str = " ".join(str(item) for item in value).lower()
                    elif isinstance(value, dict):
                         # Search within dict values (e.g., privacy_settings) - might not be useful
                         value_str = " ".join(str(v) for v in value.values()).lower()
                    elif isinstance(value, datetime):
                         # Search formatted date string
                         value_str = value.isoformat().lower()
                    else:
                         value_str = str(value).lower()

                    if query_lower in value_str:
                        match_found = True
                        break # Found match in this person, move to next person

                except AttributeError:
                    print(f"Warning: Field '{field}' not found on Person object during search.")
                    continue # Skip invalid field

            if match_found:
                results.append(person)

        return results

    def generate_family_tree_report(self) -> str:
        """Generates a simple text report of the tree structure."""
        report = "Family Tree Report:\n\n"
        # Re-use display_tree logic but capture output to string
        # This is complex to do perfectly without capturing stdout.
        # For now, just list persons and their direct relationships.
        if not self.person_nodes:
            return report + "Tree is empty.\n"

        for person_id, person in sorted(self.person_nodes.items()):
             report += f"Person: {person.get_full_name()} (ID: {person_id})\n"
             parents = [self.get_person_by_id(pid) for pid in person.get_parents()]
             children = [self.get_person_by_id(pid) for pid in person.get_children()]
             spouses = [self.get_person_by_id(pid) for pid in person.get_spouses()]

             if parents: report += f"  Parents: {', '.join([p.get_full_name() if p else 'Unknown' for p in parents])}\n"
             if spouses: report += f"  Spouses: {', '.join([s.get_full_name() if s else 'Unknown' for s in spouses])}\n"
             if children: report += f"  Children: {', '.join([c.get_full_name() if c else 'Unknown' for c in children])}\n"
             report += "\n" # Separator

        return report

    def generate_person_summary_report(self, person_id: str) -> str:
        """Generates a summary report for a specific person."""
        person = self.get_person_by_id(person_id)
        if not person:
            raise ValueError(f"Person with ID {person_id} not found.")

        info = person.get_person_info() # Get data dictionary
        report = f"Person Summary Report for ID: {person_id}\n"
        report += f"----------------------------------------\n"
        for key, value in info.items():
             if value: # Only show fields with data
                 # Format complex fields for readability
                 if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                      report += f"{key.replace('_', ' ').title()}:\n"
                      for item in value:
                           report += f"  - {item}\n" # Basic dict print
                 elif isinstance(value, list):
                      report += f"{key.replace('_', ' ').title()}: {', '.join(map(str, value))}\n"
                 elif isinstance(value, dict):
                      report += f"{key.replace('_', ' ').title()}:\n"
                      for k, v in value.items():
                           report += f"  - {k}: {v}\n"
                 else:
                      report += f"{key.replace('_', ' ').title()}: {value}\n"
        report += f"----------------------------------------\n"
        return report

    def generate_custom_report(self, person_ids: List[str], fields: List[str]) -> str:
        """Generates a custom report for specific persons and fields."""
        report = f"Custom Report\n"
        report += f"Fields: {', '.join(fields)}\n"
        report += f"----------------------------------------\n"

        for person_id in person_ids:
            person = self.get_person_by_id(person_id)
            if not person:
                report += f"Person ID: {person_id} (Not Found)\n"
                continue

            report += f"Person: {person.get_full_name()} (ID: {person_id})\n"
            person_info = person.get_person_info()
            for field in fields:
                 value = person_info.get(field)
                 if value:
                     # Basic formatting
                     value_str = str(value)
                     if isinstance(value, list): value_str = ", ".join(map(str, value))
                     elif isinstance(value, dict): value_str = json.dumps(value)
                     report += f"  {field.replace('_', ' ').title()}: {value_str}\n"
                 else:
                      report += f"  {field.replace('_', ' ').title()}: (No data)\n"
            report += "---\n"

        report += f"----------------------------------------\n"
        return report

