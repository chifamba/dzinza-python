# src/person.py
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any # Import necessary types

# Forward declaration for type hinting Relationship
class Relationship:
    pass

# Forward declaration for type hinting FamilyTree
class FamilyTree:
    pass

class Person:
    """
    Represents an individual in the family tree.

    Attributes:
        person_id (str): Unique identifier for the person (UUID).
        creator_user_id (str): The user ID of the person who created this record.
        names (List[Dict[str, str]]): List of names (first, last, middle, maiden, etc.).
        gender (Optional[str]): Gender identity.
        date_of_birth (Optional[datetime]): Date of birth.
        place_of_birth (Optional[str]): Place of birth.
        date_of_death (Optional[datetime]): Date of death.
        place_of_death (Optional[str]): Place of death.
        biography (str): Life story or biographical notes.
        profile_photo (Optional[str]): URL or path to a profile photo.
        relationships (List[Relationship]): List of relationships this person is involved in.
        # --- Other attributes from the original class ---
        romanization (Optional[str]): Romanized name.
        transliteration (Optional[str]): Transliterated name.
        religious_affiliations (List[str]): List of religious affiliations.
        current_location (Optional[str]): Current location.
        privacy_settings (Dict[str, str]): Privacy settings for specific fields.
        documents (List[str]): List of associated document URLs/paths.
        media (List[str]): List of associated media URLs/paths.
        military_service_records (List[str]): Military service records.
        educational_history (List[str]): Educational history records.
        occupational_history (List[str]): Occupational history records.
        medical_history (List[str]): Medical history records (potentially encrypted).
        languages_spoken (List[str]): Languages spoken.
        physical_characteristics (List[str]): Physical characteristics.
        cultural_relationships (Dict[str, List[str]]): Culturally specific relationships.
        godparents (List[str]): List of godparent person IDs.
        foster_relationships (List[str]): List of foster relationship person IDs.
        guardian_relationships (List[str]): List of guardian relationship person IDs.
        tribal_clan_affiliations (List[str]): Tribal or clan affiliations.
        historical_context_relationships (Dict[str, List[str]]): Historical context relationships.
        relationship_timeline (Dict[str, List[Dict[str, str]]]): Timeline of relationship events.
        custom_relationships (Dict[str, List[str]]): User-defined custom relationships.
        family_tree (Optional[FamilyTree]): Reference to the family tree this person belongs to.
    """
    def __init__(self,
                 creator_user_id: str,
                 first_name: str,
                 last_name: str,
                 date_of_birth: Optional[str] = None, # Accept string for flexibility
                 place_of_birth: Optional[str] = None,
                 person_id: Optional[str] = None, # Allow providing ID, otherwise generate
                 gender: Optional[str] = None,
                 date_of_death: Optional[str] = None, # Accept string
                 place_of_death: Optional[str] = None,
                 family_tree: Optional['FamilyTree'] = None, # Use forward reference string
                 encryption_key: Optional[str] = None): # Placeholder for encryption

        # --- Core Identifiers ---
        self.person_id = person_id if person_id else str(uuid.uuid4())
        self.creator_user_id = creator_user_id # Link to the user who created this record

        # --- Basic Info ---
        self.names: List[Dict[str, str]] = []
        self.add_name(name=first_name, type="first", culture="default")
        self.add_name(name=last_name, type="last", culture="default")
        self.gender = gender

        # --- Dates and Places ---
        # Store dates as datetime objects if possible, handle potential parsing errors
        self.date_of_birth = self._parse_date(date_of_birth)
        self.place_of_birth = place_of_birth
        self.date_of_death = self._parse_date(date_of_death)
        self.place_of_death = place_of_death

        # --- Relationships ---
        # Stores Relationship objects where this person is either person1 or person2
        self.relationships: List['Relationship'] = [] # Use forward reference string

        # --- Other Attributes ---
        self.biography: str = "" # Consider encrypting
        self.profile_photo: Optional[str] = None
        self.romanization: Optional[str] = None
        self.transliteration: Optional[str] = None
        self.religious_affiliations: List[str] = []
        self.current_location: Optional[str] = None
        self.privacy_settings: Dict[str, str] = {} # e.g., {"date_of_birth": "private"}
        self.documents: List[str] = [] # Consider encrypting sensitive docs
        self.media: List[str] = []
        self.military_service_records: List[str] = []
        self.educational_history: List[str] = []
        self.occupational_history: List[str] = []
        self.medical_history: List[str] = [] # Consider encrypting
        self.languages_spoken: List[str] = []
        self.physical_characteristics: List[str] = [] # Consider encrypting
        self.cultural_relationships: Dict[str, List[str]] = {} # e.g., {"clan_member": ["person_id_1"]}
        self.godparents: List[str] = [] # List of person_ids
        self.foster_relationships: List[str] = [] # List of person_ids
        self.guardian_relationships: List[str] = [] # List of person_ids
        self.tribal_clan_affiliations: List[str] = []
        self.historical_context_relationships: Dict[str, List[str]] = {}
        self.relationship_timeline: Dict[str, List[Dict[str, str]]] = {} # e.g., {"person_id_1": [{"event": "met", "date": "2023-01-01"}]}
        self.custom_relationships: Dict[str, List[str]] = {} # e.g., {"mentor": ["person_id_1"]}

        # --- Context ---
        self.family_tree = family_tree # Reference to the containing tree

        # --- Encryption Placeholder ---
        self._encryption_key = encryption_key # Store key if provided
        # self.encryptor = DataEncryptor() # Instantiate when implemented

        # Encrypt sensitive fields if key provided (placeholder)
        # self.biography = self._encrypt_field(self.biography)
        # self.medical_history = self._encrypt_list_field(self.medical_history)


    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Helper to parse date strings into datetime objects."""
        if not date_str:
            return None
        try:
            # Attempt standard ISO format first
            return datetime.fromisoformat(date_str.replace(' ', 'T'))
        except ValueError:
            try:
                # Add other common formats if needed
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                 # Could add more formats or return None/raise error
                 print(f"Warning: Could not parse date string: {date_str}") # Or log properly
                 return None # Or keep as string, or raise error

    # --- Encryption Placeholders ---
    def _encrypt_field(self, data: Optional[str]) -> Optional[str]:
        """Placeholder for encrypting a single field."""
        if self._encryption_key and data:
            # return self.encryptor.encrypt_data(data, self._encryption_key)
            print(f"Placeholder: Encrypting field for person {self.person_id}")
            return data # Return original for now
        return data

    def _decrypt_field(self, encrypted_data: Optional[str]) -> Optional[str]:
        """Placeholder for decrypting a single field."""
        if self._encryption_key and encrypted_data:
            # return self.encryptor.decrypt_data(encrypted_data, self._encryption_key)
            print(f"Placeholder: Decrypting field for person {self.person_id}")
            return encrypted_data # Return original for now
        return encrypted_data

    def _encrypt_list_field(self, data_list: List[str]) -> List[str]:
         """Placeholder for encrypting a list of strings."""
         if self._encryption_key:
             # return [self.encryptor.encrypt_data(item, self._encryption_key) for item in data_list]
             print(f"Placeholder: Encrypting list field for person {self.person_id}")
             return data_list # Return original for now
         return data_list

    def _decrypt_list_field(self, encrypted_list: List[str]) -> List[str]:
         """Placeholder for decrypting a list of strings."""
         if self._encryption_key:
              # return [self.encryptor.decrypt_data(item, self._encryption_key) for item in encrypted_list]
              print(f"Placeholder: Decrypting list field for person {self.person_id}")
              return encrypted_list # Return original for now
         return encrypted_list

    # --- Name Management ---
    def add_name(self, name: str, type: str, culture: str):
        """Adds a name entry."""
        new_name = {"name": name, "type": type, "culture": culture}
        if any(
            n["name"] == name and n["type"] == type and n["culture"] == culture
            for n in self.names
        ):
            # Optionally allow duplicates or just ignore
            print(f"Warning: Duplicate name entry ignored for person {self.person_id}: {new_name}")
            # raise ValueError("Name already exists") # Or raise error if strict
        else:
            self.names.append(new_name)

    def remove_name(self, name: str, type: str, culture: str):
        """Removes a specific name entry."""
        name_to_remove = {"name": name, "type": type, "culture": culture}
        if name_to_remove in self.names:
            self.names.remove(name_to_remove)
        else:
            raise ValueError(f"Name not found for person {self.person_id}: {name_to_remove}")

    def get_names(self, name_type: Optional[str] = None, culture: Optional[str] = None) -> List[Dict[str, str]]:
        """Gets names, optionally filtered by type and/or culture."""
        if not name_type and not culture:
            return self.names
        result = []
        for n in self.names:
            type_match = not name_type or n.get("type") == name_type
            culture_match = not culture or n.get("culture") == culture
            if type_match and culture_match:
                result.append(n)
        return result

    def get_full_name(self, culture: str = "default") -> str:
        """Constructs a full name string (simple example)."""
        first = next((n['name'] for n in self.names if n.get('type') == 'first' and n.get('culture') == culture), "")
        last = next((n['name'] for n in self.names if n.get('type') == 'last' and n.get('culture') == culture), "")
        return f"{first} {last}".strip()

    # --- Relationship Management ---
    def add_relationship(self, relationship: 'Relationship'):
        """Adds a relationship involving this person."""
        if relationship not in self.relationships:
            # Ensure the relationship involves this person
            if self.person_id != relationship.person1_id and self.person_id != relationship.person2_id:
                 raise ValueError(f"Relationship {relationship} does not involve person {self.person_id}")
            self.relationships.append(relationship)
        # else: already added

    def remove_relationship(self, relationship: 'Relationship'):
         """Removes a relationship involving this person."""
         if relationship in self.relationships:
             self.relationships.remove(relationship)
         else:
             raise ValueError(f"Relationship {relationship} not found for person {self.person_id}")

    def get_related_person_ids(self, relationship_type: str) -> List[str]:
        """Gets IDs of persons related by a specific type."""
        related_ids = set()
        for rel in self.relationships:
            if rel.relationship_type == relationship_type:
                if rel.person1_id == self.person_id:
                    related_ids.add(rel.person2_id)
                else: # rel.person2_id == self.person_id
                    related_ids.add(rel.person1_id)
        return list(related_ids)

    def get_parents(self) -> List[str]:
        """Gets the person IDs of the parents."""
        parent_ids = set()
        for rel in self.relationships:
            # If this person is the child in the relationship
            if rel.relationship_type == 'child' and rel.person1_id == self.person_id:
                 parent_ids.add(rel.person2_id)
            # If this person is the parent in the relationship (less common to store this way)
            # elif rel.relationship_type == 'parent' and rel.person2_id == self.person_id:
            #      parent_ids.add(rel.person1_id)
        return list(parent_ids)

    def get_children(self) -> List[str]:
        """Gets the person IDs of the children."""
        child_ids = set()
        for rel in self.relationships:
             # If this person is the parent in the relationship
             if rel.relationship_type == 'parent' and rel.person1_id == self.person_id:
                 child_ids.add(rel.person2_id)
             # If this person is the child in the relationship (less common)
             # elif rel.relationship_type == 'child' and rel.person2_id == self.person_id:
             #     child_ids.add(rel.person1_id)
        return list(child_ids)

    def get_spouses(self) -> List[str]:
        """Gets the person IDs of the spouses/partners."""
        return self.get_related_person_ids('spouse')

    def get_siblings(self) -> List[str]:
        """Gets the person IDs of the siblings."""
        # Siblings share at least one parent. More complex logic needed if half/step siblings differentiated.
        # Simple approach: find parents, then find children of those parents (excluding self).
        parent_ids = self.get_parents()
        if not parent_ids or not self.family_tree:
            return []

        sibling_ids = set()
        for parent_id in parent_ids:
            parent = self.family_tree.get_person_by_id(parent_id)
            if parent:
                parent_children = parent.get_children() # Get IDs directly
                for child_id in parent_children:
                    if child_id != self.person_id:
                        sibling_ids.add(child_id)
        return list(sibling_ids)

    # --- Other Attribute Management (Examples) ---

    def set_romanization(self, romanization:str):
        self.romanization = romanization

    def get_romanization(self) -> Optional[str]:
        return self.romanization

    def set_transliteration(self, transliteration: str):
        self.transliteration = transliteration

    def get_transliteration(self) -> Optional[str]:
        return self.transliteration

    def add_religious_affiliation(self, affiliation: str):
        if affiliation not in self.religious_affiliations:
            self.religious_affiliations.append(affiliation)
        else:
             raise ValueError("Affiliation already exists")

    def remove_religious_affiliation(self, affiliation: str):
        if affiliation in self.religious_affiliations:
            self.religious_affiliations.remove(affiliation)
        else:
            raise ValueError("Affiliation not found")

    def get_religious_affiliations(self) -> list:
        return self.religious_affiliations

    def set_privacy_setting(self, field: str, privacy_level: str):
        """Sets the privacy level for a specific field."""
        valid_privacy_levels = [
            "public", "private", "family_only", "connected_only", # Simplified levels
            "godparents_only", "foster_only", "guardians_only" # More specific if needed
        ]
        if privacy_level not in valid_privacy_levels:
            raise ValueError(f"Invalid privacy level: {privacy_level}. Valid levels are: {', '.join(valid_privacy_levels)}")
        self.privacy_settings[field] = privacy_level

    def get_privacy_setting(self, field: str) -> str:
        """Gets the privacy level for a specific field, defaulting to 'private'."""
        return self.privacy_settings.get(field, "private") # Default to private

    def set_profile_photo(self, url: str):
        # Add validation if needed (e.g., check URL format)
        self.profile_photo = url

    def get_profile_photo(self) -> Optional[str]:
        # Add decryption placeholder if photos are encrypted
        return self.profile_photo

    # --- Add/Remove/Get methods for other list attributes ---
    # Example for documents
    def add_document(self, document: str):
        # Add validation (e.g., URL format, file existence if local path)
        if document not in self.documents:
            self.documents.append(document)

    def remove_document(self, document: str):
        if document in self.documents:
            self.documents.remove(document)
        else:
            raise ValueError("Document not found")

    def get_documents(self) -> List[str]:
        # Add decryption placeholder if needed
        return self.documents # self._decrypt_list_field(self.documents)

    # Add similar methods for: media, military_service_records, educational_history,
    # occupational_history, medical_history, languages_spoken, physical_characteristics,
    # godparents, foster_relationships, guardian_relationships, tribal_clan_affiliations

    # Example for godparents (list of IDs)
    def add_godparent(self, godparent_id: str):
        if godparent_id not in self.godparents:
             # Optional: Check if godparent_id exists in the family tree
             # if self.family_tree and not self.family_tree.get_person_by_id(godparent_id):
             #     raise ValueError(f"Godparent with ID {godparent_id} not found in tree.")
             self.godparents.append(godparent_id)
        else:
             raise ValueError("Godparent already added")

    def remove_godparent(self, godparent_id: str):
        if godparent_id in self.godparents:
             self.godparents.remove(godparent_id)
        else:
             raise ValueError("Godparent not found")

    def get_godparents(self) -> List[str]:
        return self.godparents

    # --- Add/Remove/Get methods for dictionary attributes ---
    # Example for cultural_relationships
    def add_cultural_relationship(self, relationship_type: str, related_person_id: str):
        if relationship_type not in self.cultural_relationships:
            self.cultural_relationships[relationship_type] = []
        if related_person_id not in self.cultural_relationships[relationship_type]:
             # Optional: Check if related_person_id exists
             # if self.family_tree and not self.family_tree.get_person_by_id(related_person_id):
             #     raise ValueError(f"Related person with ID {related_person_id} not found.")
             self.cultural_relationships[relationship_type].append(related_person_id)
        else:
             raise ValueError(f"Person {related_person_id} already has cultural relationship {relationship_type}.")

    def remove_cultural_relationship(self, relationship_type: str, related_person_id: str):
        if relationship_type not in self.cultural_relationships:
            raise ValueError("Cultural relationship type not found")
        if related_person_id not in self.cultural_relationships[relationship_type]:
            raise ValueError("Related person not found in this cultural relationship")
        self.cultural_relationships[relationship_type].remove(related_person_id)
        # Remove the type key if the list becomes empty
        if not self.cultural_relationships[relationship_type]:
            del self.cultural_relationships[relationship_type]

    def get_cultural_relationships(self) -> Dict[str, List[str]]:
        return self.cultural_relationships

    # Add similar methods for: historical_context_relationships, relationship_timeline, custom_relationships

    # --- Data Retrieval ---
    def get_person_info(self) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the person's data.
        Handles placeholder decryption for sensitive fields.
        """
        # Decrypt fields before returning (using placeholders)
        decrypted_biography = self._decrypt_field(self.biography)
        decrypted_medical_history = self._decrypt_list_field(self.medical_history)
        decrypted_documents = self._decrypt_list_field(self.documents)
        # ... decrypt other fields as needed

        return {
            "person_id": self.person_id,
            "creator_user_id": self.creator_user_id,
            "names": self.names,
            "gender": self.gender,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "place_of_birth": self.place_of_birth,
            "date_of_death": self.date_of_death.isoformat() if self.date_of_death else None,
            "place_of_death": self.place_of_death,
            "biography": decrypted_biography,
            "profile_photo": self.profile_photo,
            "romanization": self.romanization,
            "transliteration": self.transliteration,
            "religious_affiliations": self.religious_affiliations,
            "current_location": self.current_location,
            "privacy_settings": self.privacy_settings,
            "documents": decrypted_documents,
            "media": self.media, # Add decryption if needed
            "military_service_records": self.military_service_records,
            "educational_history": self.educational_history,
            "occupational_history": self.occupational_history,
            "medical_history": decrypted_medical_history,
            "languages_spoken": self.languages_spoken,
            "physical_characteristics": self.physical_characteristics, # Add decryption if needed
            "cultural_relationships": self.cultural_relationships,
            "godparents": self.godparents,
            "foster_relationships": self.foster_relationships,
            "guardian_relationships": self.guardian_relationships,
            "tribal_clan_affiliations": self.tribal_clan_affiliations,
            "historical_context_relationships": self.historical_context_relationships,
            "relationship_timeline": self.relationship_timeline,
            "custom_relationships": self.custom_relationships,
            # Relationships are handled separately by FamilyTree or Relationship objects
            # "relationships": [rel.to_dict() for rel in self.relationships] # Optionally include relationship details
        }

    def __str__(self) -> str:
        """String representation for the Person object."""
        dob = self.date_of_birth.strftime('%Y-%m-%d') if self.date_of_birth else "Unknown"
        return f"Person(id={self.person_id}, name='{self.get_full_name()}', dob={dob})"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"<Person {self.person_id} - {self.get_full_name()}>"

    def __eq__(self, other: object) -> bool:
        """Equality check based on person_id."""
        if not isinstance(other, Person):
            return NotImplemented
        return self.person_id == other.person_id

    def __hash__(self) -> int:
        """Hash based on person_id."""
        return hash(self.person_id)

# Import Relationship here after Person class definition to avoid circular import issues
from src.relationship import Relationship
# Import FamilyTree here if needed for type hints within methods
# from src.family_tree import FamilyTree
