# src/family_tree.py

import logging
from typing import List, Dict, Optional, Tuple, Any
from tinydb import TinyDB, Query, table # Import TinyDB components

# Assuming db_utils.py exists for getting DB instances
from .db_utils import get_tree_db # Import the function to get the DB instance

from .person import Person
from .relationship import Relationship, get_reciprocal_relationship
from .audit_log import AuditLog, PlaceholderAuditLog
from .encryption import DataEncryptor, PlaceholderDataEncryptor

# Configure logging - Ensure this is configured in your main app setup
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FamilyTree:
    """
    Manages persons and relationships in a family tree using TinyDB.
    """

    def __init__(self, audit_log: Optional[AuditLog] = None, encryptor: Optional[DataEncryptor] = None):
        """
        Initializes the FamilyTree with TinyDB backend.

        Args:
            audit_log: An instance of AuditLog. Defaults to PlaceholderAuditLog.
            encryptor: An instance of DataEncryptor. Defaults to PlaceholderDataEncryptor.
                       (Note: Encryption logic needs integration within CRUD methods if required).
        """
        self.audit_log = audit_log or PlaceholderAuditLog()
        self.encryptor = encryptor or PlaceholderDataEncryptor()

        # REMOVED: Direct DB access in init
        # self.tree_db = get_tree_db()
        # self.persons_table = self.tree_db.table('persons')
        # self.relationships_table = self.tree_db.table('relationships')
        logging.info("FamilyTree initialized (DB access deferred to methods).")

    # --- Helper Methods to Get Tables ---
    def _get_persons_table(self) -> table.Table:
        """Helper method to get the TinyDB persons table within context."""
        return get_tree_db().table('persons')

    def _get_relationships_table(self) -> table.Table:
        """Helper method to get the TinyDB relationships table within context."""
        return get_tree_db().table('relationships')


    # --- Person Management (using TinyDB) ---

    def add_person(self, person: Person, user: str = "system") -> None:
        """
        Adds a new person to the TinyDB 'persons' table.

        Args:
            person: The Person object to add.
            user: The user performing the action.

        Raises:
            ValueError: If a person with the same ID already exists or validation fails.
        """
        if not isinstance(person, Person):
             raise TypeError("person must be an instance of Person")

        persons_table = self._get_persons_table() # Get table now
        PersonQuery = Query()
        if persons_table.contains(PersonQuery.person_id == person.person_id):
            raise ValueError(f"Person with ID {person.person_id} already exists in DB.")

        try:
            person_data = person.to_dict()
            # Add encryption here if needed
            persons_table.insert(person_data)
            self.audit_log.log_event(user, "person_added", f"Added person: {person.person_id} ({person.get_full_name()})")
            logging.info(f"Added person {person.person_id} to DB by user {user}")
        except Exception as e:
             logging.exception(f"Error adding person {person.person_id} to DB: {e}")
             raise ValueError(f"Could not add person {person.person_id} to database.") from e

    def get_person(self, person_id: str) -> Optional[Person]:
        """Retrieves a person by their ID from TinyDB."""
        persons_table = self._get_persons_table() # Get table now
        PersonQuery = Query()
        person_data_list = persons_table.search(PersonQuery.person_id == person_id)
        if person_data_list:
            person_data = person_data_list[0]
            # Add decryption here if needed
            try:
                return Person.from_dict(person_data)
            except (KeyError, ValueError) as e:
                 logging.error(f"Error creating Person object from DB data for ID '{person_id}': {e}. Data: {person_data}")
                 return None
        return None

    def update_person(self, person_id: str, update_data: Dict[str, Any], user: str = "system") -> bool:
        """
        Updates details of an existing person in TinyDB.

        Args:
            person_id: The ID of the person to update.
            update_data: A dictionary containing the attributes to update.
            user: The user performing the action.

        Returns:
            True if the update was successful, False otherwise.
        """
        persons_table = self._get_persons_table() # Get table now
        PersonQuery = Query()
        if not persons_table.contains(PersonQuery.person_id == person_id):
            logging.warning(f"Update failed: Person with ID {person_id} not found in DB.")
            return False

        db_update_data = update_data.copy()
        # Add encryption here if needed

        try:
            persons_table.update(db_update_data, PersonQuery.person_id == person_id)
            updated_person = self.get_person(person_id)
            person_name = updated_person.get_full_name() if updated_person else person_id

            self.audit_log.log_event(user, "person_updated", f"Updated person: {person_id} ({person_name}). Changes: {list(update_data.keys())}")
            logging.info(f"Updated person {person_id} in DB by user {user}")
            return True
        except Exception as e:
             logging.exception(f"Error updating person {person_id} in DB: {e}")
             return False

    def delete_person(self, person_id: str, user: str = "system") -> bool:
        """
        Deletes a person from the 'persons' table and all their relationships
        from the 'relationships' table in TinyDB.

        Args:
            person_id: The ID of the person to delete.
            user: The user performing the action.

        Returns:
            True if deletion was successful, False if the person was not found.
        """
        persons_table = self._get_persons_table() # Get table now
        relationships_table = self._get_relationships_table() # Get table now
        PersonQuery = Query()
        RelationshipQuery = Query()

        person_data_list = persons_table.search(PersonQuery.person_id == person_id)
        if not person_data_list:
            logging.warning(f"Deletion failed: Person with ID {person_id} not found in DB.")
            return False
        person_name = f"{person_data_list[0].get('first_name', '')} {person_data_list[0].get('last_name', '')}".strip() or person_id

        try:
            rels_deleted_count = relationships_table.remove(
                (RelationshipQuery.person1_id == person_id) | (RelationshipQuery.person2_id == person_id)
            )
            if rels_deleted_count > 0:
                 log_desc = f"Removed {rels_deleted_count} relationships involving deleted person {person_id} ({person_name})"
                 self.audit_log.log_event(user, "relationship_removed", log_desc)
                 logging.info(f"{log_desc} by user {user}")

            persons_table.remove(PersonQuery.person_id == person_id)

            self.audit_log.log_event(user, "person_deleted", f"Deleted person: {person_id} ({person_name})")
            logging.info(f"Deleted person {person_id} from DB by user {user}")
            return True
        except Exception as e:
             logging.exception(f"Error deleting person {person_id} from DB: {e}")
             return False

    def find_person_by_name(self, name_query: str) -> List[Person]:
        """Finds persons by name in TinyDB (case-insensitive substring match)."""
        persons_table = self._get_persons_table() # Get table now
        results = []
        name_query_lower = name_query.lower()
        all_persons_data = persons_table.all()
        for p_data in all_persons_data:
             full_name = f"{p_data.get('first_name', '')} {p_data.get('last_name', '')}".lower()
             if name_query_lower in full_name:
                 try:
                    # Add decryption here if needed
                    results.append(Person.from_dict(p_data))
                 except (KeyError, ValueError) as e:
                    logging.error(f"Error creating Person object during search: {e}. Data: {p_data}")
        return results

    def get_all_persons(self) -> List[Person]:
        """ Retrieves all persons from the database. """
        persons_table = self._get_persons_table() # Get table now
        all_persons_data = persons_table.all()
        persons = []
        for p_data in all_persons_data:
            try:
                # Add decryption here if needed
                persons.append(Person.from_dict(p_data))
            except (KeyError, ValueError) as e:
                logging.error(f"Error creating Person object from DB data: {e}. Data: {p_data}")
        return persons


    # --- Relationship Management (using TinyDB) ---

    def add_relationship(self, person1_id: str, person2_id: str, rel_type: str, attributes: Optional[Dict] = None, user: str = "system") -> bool:
        """
        Adds a relationship document to the 'relationships' table in TinyDB.
        Handles reciprocal relationships implicitly by querying.

        Args:
            person1_id: ID of the first person.
            person2_id: ID of the second person.
            rel_type: The type of relationship from person1 to person2.
            attributes: Optional dictionary of relationship attributes.
            user: The user performing the action.

        Returns:
            True if the relationship was added successfully, False otherwise.

        Raises:
            ValueError: If either person ID does not exist or relationship is to self.
        """
        persons_table = self._get_persons_table() # Get table now
        relationships_table = self._get_relationships_table() # Get table now
        PersonQuery = Query()
        if not persons_table.contains(PersonQuery.person_id == person1_id):
            raise ValueError(f"Person with ID {person1_id} not found.")
        if not persons_table.contains(PersonQuery.person_id == person2_id):
            raise ValueError(f"Person with ID {person2_id} not found.")
        if person1_id == person2_id:
             raise ValueError("Cannot add relationship to self.")

        relationship = Relationship(person1_id, person2_id, rel_type, attributes)
        rel_data = relationship.to_dict()

        RelationshipQuery = Query()
        exists = relationships_table.contains(
            (RelationshipQuery.person1_id == person1_id) &
            (RelationshipQuery.person2_id == person2_id) &
            (RelationshipQuery.rel_type == rel_type)
        )

        if exists:
            logging.info(f"Relationship {person1_id} -> {person2_id} ({rel_type}) already exists in DB.")
            return False

        try:
            relationships_table.insert(rel_data)
            log_desc = f"Added relationship: {relationship}"
            self.audit_log.log_event(user, "relationship_added", log_desc)
            logging.info(f"Added relationship {person1_id} -> {person2_id} ({rel_type}) to DB by user {user}")

            reciprocal_type = get_reciprocal_relationship(rel_type)
            reciprocal_exists = relationships_table.contains(
                (RelationshipQuery.person1_id == person2_id) &
                (RelationshipQuery.person2_id == person1_id) &
                (RelationshipQuery.rel_type == reciprocal_type)
            )
            if not reciprocal_exists:
                 reciprocal_rel = Relationship(person2_id, person1_id, reciprocal_type, attributes)
                 reciprocal_data = reciprocal_rel.to_dict()
                 relationships_table.insert(reciprocal_data)
                 log_desc_recip = f"Added reciprocal relationship: {reciprocal_rel}"
                 self.audit_log.log_event(user, "relationship_added", log_desc_recip)
                 logging.info(f"Added reciprocal relationship {person2_id} -> {person1_id} ({reciprocal_type}) to DB by user {user}")

            return True
        except Exception as e:
             logging.exception(f"Error adding relationship {person1_id} -> {person2_id} ({rel_type}) to DB: {e}")
             return False


    def get_relationships(self, person_id: str, direction: str = 'outgoing') -> List[Relationship]:
        """
        Retrieves relationships for a given person ID from TinyDB.

        Args:
            person_id: The ID of the person whose relationships to find.
            direction: 'outgoing' (person is person1), 'incoming' (person is person2), or 'both'.

        Returns:
            A list of Relationship objects.
        """
        relationships_table = self._get_relationships_table() # Get table now
        RelationshipQuery = Query()
        relationships_data = []

        if direction == 'outgoing' or direction == 'both':
            relationships_data.extend(relationships_table.search(RelationshipQuery.person1_id == person_id))
        if direction == 'incoming' or direction == 'both':
            incoming_data = relationships_table.search(RelationshipQuery.person2_id == person_id)
            if direction == 'both':
                 existing_ids = { (d['person1_id'], d['person2_id'], d['rel_type']) for d in relationships_data }
                 for inc_data in incoming_data:
                     rev_tuple = (inc_data['person2_id'], inc_data['person1_id'], get_reciprocal_relationship(inc_data['rel_type']))
                     if rev_tuple not in existing_ids:
                         relationships_data.append(inc_data)
            else:
                 relationships_data.extend(incoming_data)

        relationships = []
        for r_data in relationships_data:
            try:
                relationships.append(Relationship.from_dict(r_data))
            except (KeyError, ValueError) as e:
                 logging.error(f"Error creating Relationship object from DB data: {e}. Data: {r_data}")

        return relationships


    def update_relationship(self, person1_id: str, person2_id: str, old_rel_type: str, update_data: Dict[str, Any], user: str = "system") -> bool:
        """
        Updates attributes or type of an existing relationship document in TinyDB.
        Handles reciprocal update if type changes.

        Args:
            person1_id: ID of the first person.
            person2_id: ID of the second person.
            old_rel_type: The current relationship type from person1 to person2.
            update_data: Dictionary of updates (e.g., {'rel_type': 'divorced', 'attributes': {...}})
            user: The user performing the action.

        Returns:
            True if the update was successful, False otherwise.
        """
        relationships_table = self._get_relationships_table() # Get table now
        RelationshipQuery = Query()
        new_rel_type = update_data.get('rel_type', old_rel_type)
        updated = False

        primary_update_result = relationships_table.update(
            update_data,
            (RelationshipQuery.person1_id == person1_id) &
            (RelationshipQuery.person2_id == person2_id) &
            (RelationshipQuery.rel_type == old_rel_type)
        )
        if primary_update_result:
             updated = True

        if old_rel_type != new_rel_type:
            old_reciprocal_type = get_reciprocal_relationship(old_rel_type)
            new_reciprocal_type = get_reciprocal_relationship(new_rel_type)
            reciprocal_update_payload = {'rel_type': new_reciprocal_type}
            if 'attributes' in update_data:
                 reciprocal_update_payload['attributes'] = update_data['attributes']

            reciprocal_update_result = relationships_table.update(
                 reciprocal_update_payload,
                 (RelationshipQuery.person1_id == person2_id) &
                 (RelationshipQuery.person2_id == person1_id) &
                 (RelationshipQuery.rel_type == old_reciprocal_type)
            )
            if reciprocal_update_result:
                 updated = True
        elif 'attributes' in update_data:
             reciprocal_type = get_reciprocal_relationship(old_rel_type)
             reciprocal_update_result = relationships_table.update(
                 {'attributes': update_data['attributes']},
                 (RelationshipQuery.person1_id == person2_id) &
                 (RelationshipQuery.person2_id == person1_id) &
                 (RelationshipQuery.rel_type == reciprocal_type)
             )
             if reciprocal_update_result:
                  updated = True

        if updated:
            log_desc = f"Updated relationship: {person1_id} <-> {person2_id} (from {old_rel_type} to {new_rel_type})"
            self.audit_log.log_event(user, "relationship_updated", log_desc)
            logging.info(f"Updated relationship {person1_id}<->{person2_id} from {old_rel_type} to {new_rel_type} in DB by {user}")
            return True

        logging.warning(f"Update failed: Relationship {person1_id} -> {person2_id} ({old_rel_type}) not found or no changes applied.")
        return False


    def delete_relationship(self, person1_id: str, person2_id: str, rel_type: str, user: str = "system") -> bool:
        """
        Deletes a specific relationship document from TinyDB. Handles reciprocal deletion.

        Args:
            person1_id: ID of the first person.
            person2_id: ID of the second person.
            rel_type: The type of relationship from person1 to person2 to delete.
            user: The user performing the action.

        Returns:
            True if the relationship was deleted successfully, False otherwise.
        """
        relationships_table = self._get_relationships_table() # Get table now
        RelationshipQuery = Query()
        deleted_count = 0

        deleted_count += len(relationships_table.remove(
            (RelationshipQuery.person1_id == person1_id) &
            (RelationshipQuery.person2_id == person2_id) &
            (RelationshipQuery.rel_type == rel_type)
        ))

        reciprocal_type = get_reciprocal_relationship(rel_type)
        deleted_count += len(relationships_table.remove(
            (RelationshipQuery.person1_id == person2_id) &
            (RelationshipQuery.person2_id == person1_id) &
            (RelationshipQuery.rel_type == reciprocal_type)
        ))

        if deleted_count > 0:
            log_desc = f"Removed relationship: {person1_id} <-> {person2_id} ({rel_type})"
            self.audit_log.log_event(user, "relationship_removed", log_desc)
            logging.info(f"Removed relationship {person1_id} <-> {person2_id} ({rel_type}) from DB by user {user}")
            return True

        logging.warning(f"Deletion failed: Relationship {person1_id} -> {person2_id} ({rel_type}) not found in DB.")
        return False


    def find_relationships_by_type(self, rel_type_query: str) -> List[Relationship]:
        """Finds all relationships matching the given type in TinyDB."""
        relationships_table = self._get_relationships_table() # Get table now
        RelationshipQuery = Query()
        matching_data = relationships_table.search(RelationshipQuery.rel_type.test(lambda t: rel_type_query.lower() in t.lower()))

        results = []
        for r_data in matching_data:
            try:
                results.append(Relationship.from_dict(r_data))
            except (KeyError, ValueError) as e:
                 logging.error(f"Error creating Relationship object during search: {e}. Data: {r_data}")
        return results

    # --- Helper methods requiring FamilyTree access ---

    def find_parents(self, person_id: str) -> List[str]:
        """Finds parent IDs for a given person ID by querying relationships."""
        relationships_table = self._get_relationships_table() # Get table now
        RelationshipQuery = Query()
        child_rels = relationships_table.search(
            (RelationshipQuery.person1_id == person_id) & (RelationshipQuery.rel_type == 'child')
        )
        parent_ids = [rel['person2_id'] for rel in child_rels]
        return parent_ids

    def find_children(self, person_id: str) -> List[str]:
        """Finds children IDs for a given person ID by querying relationships."""
        relationships_table = self._get_relationships_table() # Get table now
        RelationshipQuery = Query()
        parent_rels = relationships_table.search(
            (RelationshipQuery.person1_id == person_id) & (RelationshipQuery.rel_type == 'parent')
        )
        child_ids = [rel['person2_id'] for rel in parent_rels]
        return child_ids

