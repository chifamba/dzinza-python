from src.family_tree import FamilyTree
from src.relationship import Relationship
from src.encryption import DataEncryptor
from typing import List

class Person:
    def __init__(self, person_id, first_name, last_name, date_of_birth, place_of_birth, encryption_key, date_of_death=None, place_of_death=None, family_tree = None):
        self.names = []
        self.encryptor = DataEncryptor()
        self.person_id = person_id
        self.gender = None
        self.add_name(name=first_name, type="first", culture="default")
        self.add_name(name=last_name, type="last", culture="default")
        self.romanization = None
        self.transliteration = None
        self.religious_affiliations = []
        self.current_location = None
        self.privacy_settings = {}
        self._biography = ""
        self.date_of_birth = date_of_birth
        self.place_of_birth = place_of_birth
        self.date_of_death = date_of_death
        self.place_of_death = place_of_death
        self.family_tree:FamilyTree = family_tree
        self.profile_photo = None
        self.encryption_key = encryption_key
        self.relationships:dict[str, List[Relationship]] = {} #key: person_id, value: list of Relationship
        self.init_extended_relationships()
        self._documents: list[str] = []
        self._media: list[str] = []
        self.military_service_records: list[str] = []
        self.occupational_history: list[str] = []
        self.medical_history: list[str] = []
        self.dna_haplogroups: list[str] = []
        self.physical_characteristics: list[str] = []
        self.languages_spoken: list[str] = []
        self.immigration_naturalization_records: list[str] = []
        self.cultural_relationships = {}
        self.godparents: list[str] = []
        self.foster_relationships: list[str] = []
        self.guardian_relationships: list[str] = []
        self.tribal_clan_affiliations: list[str] = []
        self.historical_context_relationships = {}
        self.relationship_timeline = {}
        self.custom_relationships = {}
        self.educational_history: list[str] = []
    
    @property
    def biography(self):
        """Decrypts and returns the biography."""
        try:
            return self.encryptor.decrypt_data(self._biography, self.encryption_key)
        except ValueError:
            return self._biography

    @biography.setter
    def biography(self, value):
        """Encrypts the biography before storing."""
        self._biography = self.encryptor.encrypt_data(value, self.encryption_key)

    @property
    def medical_history(self):
        return [self.encryptor.decrypt_data(item, self.encryption_key) for item in self._medical_history] if hasattr(self,'_medical_history') else []

    @medical_history.setter
    def medical_history(self, value):
        self._medical_history = [self.encryptor.encrypt_data(item, self.encryption_key) for item in value]

    @property
    def physical_characteristics(self):
        return [self.encryptor.decrypt_data(item, self.encryption_key) for item in self._physical_characteristics] if hasattr(self,'_physical_characteristics') else []

    @physical_characteristics.setter
    def physical_characteristics(self, value):
        self._physical_characteristics = [self.encryptor.encrypt_data(item, self.encryption_key) for item in value]

    @property
    def dna_haplogroups(self):
        return [self.encryptor.decrypt_data(item, self.encryption_key) for item in self._dna_haplogroups] if hasattr(self,'_dna_haplogroups') else []

    @dna_haplogroups.setter
    def dna_haplogroups(self, value):
        self._dna_haplogroups = [self.encryptor.encrypt_data(item, self.encryption_key) for item in value]

    @property
    def immigration_naturalization_records(self):
        return [self.encryptor.decrypt_data(item, self.encryption_key) for item in self._immigration_naturalization_records] if hasattr(self,'_immigration_naturalization_records') else []

    @immigration_naturalization_records.setter
    def immigration_naturalization_records(self, value):
        self._immigration_naturalization_records = [self.encryptor.encrypt_data(item, self.encryption_key) for item in value]

    @property
    def documents(self):
        return [self.encryptor.decrypt_data(doc, self.encryption_key) for doc in self._documents] if hasattr(self,'_documents') else []


    def init_extended_relationships(self):
        self.relationships["grandparents"] = []
        self.relationships["aunt_uncles"] = []
        self.relationships["cousins"] = []
        self.relationships["inlaws"] = []
        self.relationships["extended_family"] = []

    def add_name(self, name, type, culture):
        new_name = {"name": name, "type": type, "culture": culture}
        if any(
            n["name"] == name and n["type"] == type and n["culture"] == culture
            for n in self.names
        ):
            raise ValueError("Name already exists")
        self.names.append(new_name)

    def set_romanization(self, romanization:str):
        self.romanization = romanization

    def get_romanization(self) -> str:
        return self.romanization

    def set_transliteration(self, transliteration: str):
        self.transliteration = transliteration

    def get_transliteration(self) -> str:
        return self.transliteration
    
    def add_religious_affiliation(self, affiliation: str):
        if affiliation in self.religious_affiliations:
            raise ValueError("Affiliation already exists")
        self.religious_affiliations.append(affiliation)

    def remove_religious_affiliation(self, affiliation: str):
        if affiliation in self.religious_affiliations:
            self.religious_affiliations.remove(affiliation)
        else:
            raise ValueError("Affiliation not found")

    def get_religious_affiliations(self) -> list:
        return self.religious_affiliations


    def remove_name(self, name, type, culture):
        for n in self.names:
            if n["name"] == name and n["type"] == type and n["culture"] == culture:
                self.names.remove(n)
                return
        raise ValueError("Name not found")

    def get_names(self, name_type=None, culture=None) -> list:
        if not name_type and not culture:
            return self.names
        result = []
        for n in self.names:
            if (not name_type or n["type"] == name_type) and (
                not culture or n["culture"] == culture
            ):
                result.append(n)
        return result

    def add_relationship(self, relationship: Relationship):
        person_id = relationship.person2_id if relationship.person1_id == self.person_id else relationship.person1_id
        self.relationships.setdefault(person_id, []).append(relationship)
        
    def add_grandparent(self, grandparent_id):
    def set_privacy_setting(self, field:str, privacy_level:str):
        """
        Sets the privacy level for a specific field.
        
        Args:
            field (str): The name of the field (e.g., "date_of_birth", "place_of_birth").
            privacy_level (str): The privacy level ("public", "private", "family_only", "godparents_only", "foster_only", "guardians_only").
        
        Raises:
            ValueError: If the privacy level is invalid.
        """
        valid_privacy_levels = ["public", "private", "family_only", "godparents_only", "foster_only", "guardians_only"]
        if privacy_level not in valid_privacy_levels:
            raise ValueError(f"Invalid privacy level: {privacy_level}. Valid levels are: {', '.join(valid_privacy_levels)}")
        self.privacy_settings[field] = privacy_level

    def get_privacy_setting(self, field:str) -> str:
        """
        Gets the privacy level for a specific field.
        
        Args:
            field (str): The name of the field.
        """
        return self.privacy_settings.get(field, "private")
        raise ValueError("Deprecated method")
        

    def add_aunt_uncle(self, aunt_uncle_id):
        raise ValueError("Deprecated method")
        

    def add_cousin(self, cousin_id):
        raise ValueError("Deprecated method")
        

    def add_inlaw(self, inlaw_id):
        if "cousins" not in self.relationships:
            raise ValueError("Relationship not found")
        if cousin_id in self.relationships["cousins"]:
            raise ValueError("Person is already in this relationship")
        self.relationships["cousins"].append(cousin_id)

    def add_inlaw(self, inlaw_id):
        raise ValueError("Deprecated method")
        
    def get_parents(self) -> list:
        return [self.family_tree.get_person_by_id(relationship.person1_id if relationship.person2_id == self.person_id else relationship.person2_id) for person_id, relationships in self.relationships.items() for relationship in relationships if relationship.relationship_type == 'parent']

    def get_children(self) -> list:
        return [self.family_tree.get_person_by_id(relationship.person1_id if relationship.person2_id == self.person_id else relationship.person2_id) for person_id, relationships in self.relationships.items() for relationship in relationships if relationship.relationship_type == 'child']

    def get_spouses(self) -> list:
        return [self.family_tree.get_person_by_id(relationship.person1_id if relationship.person2_id == self.person_id else relationship.person2_id) for person_id, relationships in self.relationships.items() for relationship in relationships if relationship.relationship_type == 'spouse']

    def get_siblings(self) -> list:
        return [self.family_tree.get_person_by_id(relationship.person1_id if relationship.person2_id == self.person_id else relationship.person2_id) for person_id, relationships in self.relationships.items() for relationship in relationships if relationship.relationship_type == 'sibling']

    
    def add_extended_family(self, extended_family_id: str):
        if "extended_family" not in self.relationships:
            raise ValueError("Relationship not found")
        if extended_family_id in self.relationships["extended_family"]:
            raise ValueError("Person is already in this relationship")
        self.relationships["extended_family"].append(extended_family_id)
        
    
    def get_grandparents(self) -> list:
        grandparents_ids = self.relationships.get("grandparents", [])
        return [self.family_tree.get_person(gp_id) for gp_id in grandparents_ids]
    
    def get_aunt_uncles(self) -> list:
        aunt_uncles_ids = self.relationships.get("aunt_uncles", [])
        return [self.family_tree.get_person(au_id) for au_id in aunt_uncles_ids]
    
    def get_cousins(self) -> list:
        cousins_ids = self.relationships.get("cousins", [])
        return [self.family_tree.get_person(c_id) for c_id in cousins_ids]

    def add_cultural_relationship(self, relationship_type: str, related_person_id: str):
        if relationship_type not in self.cultural_relationships:
            self.cultural_relationships[relationship_type] = []
        if related_person_id in self.cultural_relationships[relationship_type]:
            raise ValueError(
                f"Person {related_person_id} already has relationship type {relationship_type} with this person."
            )
        self.cultural_relationships[relationship_type].append(related_person_id)

    def remove_cultural_relationship(self, relationship_type, related_person_id):
        if relationship_type not in self.cultural_relationships:
            raise ValueError("Relationship type not found")
        if related_person_id not in self.cultural_relationships[relationship_type]:
            raise ValueError("Person not found in this relationship")
        self.cultural_relationships[relationship_type].remove(related_person_id)

    def get_cultural_relationships(self) -> dict:
        return self.cultural_relationships

    def add_godparent(self, godparent_id: str):
        if godparent_id in self.godparents:
            raise ValueError("Godparent already added")
        self.godparents.append(godparent_id)

    def remove_godparent(self, godparent_id: str):
        if godparent_id not in self.godparents:
            raise ValueError("Godparent not found")
        self.godparents.remove(godparent_id)

    def get_godparents(self) -> list:
        return self.godparents

    def add_foster_relationship(self, person_id: str):
        if person_id in self.foster_relationships:
            raise ValueError("Person already added to foster relationships")
        self.foster_relationships.append(person_id)

    def remove_foster_relationship(self, person_id: str):
        if person_id not in self.foster_relationships:
            raise ValueError("Person not found in foster relationships")
        self.foster_relationships.remove(person_id)

    def get_foster_relationships(self) -> list:
        return self.foster_relationships

    def add_guardian_relationship(self, person_id: str):
        if person_id in self.guardian_relationships:
            raise ValueError("Person already added to guardian relationships")
        self.guardian_relationships.append(person_id)

    def remove_guardian_relationship(self, person_id: str):
        if person_id not in self.guardian_relationships:
            raise ValueError("Person not found in guardian relationships")
        self.guardian_relationships.remove(person_id)

    def get_guardian_relationships(self) -> list:
        return self.guardian_relationships

    def add_tribal_clan_affiliation(self, affiliation: str):
        self.tribal_clan_affiliations.append(affiliation)

    def remove_tribal_clan_affiliation(self, affiliation: str):
        self.tribal_clan_affiliations.remove(affiliation)

    def get_tribal_clan_affiliations(self) -> list:
        return self.tribal_clan_affiliations


    def set_family_tree(self, family_tree: FamilyTree):
        self.family_tree = family_tree

    def set_profile_photo(self, url):
        self.profile_photo = url

    def get_profile_photo(self):
        return self.profile_photo


    @documents.setter
    def documents(self, documents):
        """Encrypts the documents before storing."""
        self._documents = [self.encryptor.encrypt_data(doc, self.encryption_key) for doc in documents]

    @property
    def media(self):
        return [self.encryptor.decrypt_data(med, self.encryption_key) for med in self._media] if hasattr(self,'_media') else []

    @media.setter
    def media(self, medias):
        """Encrypts the media before storing."""
        self._media = [self.encryptor.encrypt_data(med, self.encryption_key) for med in medias]



    def get_documents(self) -> list:
        return self.documents

    def add_media(self, media: str):
        self.media.append(media)

    def add_military_service_record(self, record: str):
        if record in self.military_service_records:
            raise ValueError("Record already exists")
        self.military_service_records.append(record)

    def remove_military_service_record(self, record: str):
        if record in self.military_service_records:
            self.military_service_records.remove(record)
        else:
            raise ValueError("Record not found")

    def get_military_service_records(self) -> list:
        return self.military_service_records

    def add_educational_history(self, record: str):
        if record in self.educational_history:
            raise ValueError("Record already exists")
        self.educational_history.append(record)

    def remove_educational_history(self, record: str):
        if record in self.educational_history:
            self.educational_history.remove(record)
        else:
            raise ValueError("Record not found")

    def get_educational_history(self) -> list:
        return self.educational_history

    def add_occupational_history(self, record: str):
        if record in self.occupational_history:
            raise ValueError("Record already exists")
        self.occupational_history.append(record)

    def remove_occupational_history(self, record: str):
        if record in self.occupational_history:
            self.occupational_history.remove(record)
        else:
            raise ValueError("Record not found")

    def get_occupational_history(self) -> list:
        return self.occupational_history

    def add_medical_history(self, record: str):
        if record in self.medical_history:
            raise ValueError("Record already exists")
        self.medical_history.append(record)

    def remove_medical_history(self, record: str):
        if record in self.medical_history:
            self.medical_history.remove(record)
        else:
            raise ValueError("Record not found")
    
    def get_medical_history(self) -> list:

    def remove_physical_characteristic(self, characteristic):
        if characteristic in self.physical_characteristics:
            self.physical_characteristics.remove(characteristic)
        else:
            raise ValueError("Characteristic not found")
    

    def get_physical_characteristics(self):
        return self.physical_characteristics
    
    def add_language_spoken(self, language):
        if language in self.languages_spoken:
            raise ValueError("Language already exists")
        self.languages_spoken.append(language)

    def remove_language_spoken(self, language):
        if language in self.languages_spoken:
            self.languages_spoken.remove(language)
        else:
            raise ValueError("Language not found")
    
    def get_languages_spoken(self):
        return self.languages_spoken
    
    def add_historical_context_relationship(self, relationship_type: str, context: str):
        if relationship_type not in self.historical_context_relationships:
            self.historical_context_relationships[relationship_type] = []
        self.historical_context_relationships[relationship_type].append(context)

    def remove_historical_context_relationship(self, relationship_type: str, context: str):
        if relationship_type not in self.historical_context_relationships:
            raise ValueError("Relationship type not found")
        if context not in self.historical_context_relationships[relationship_type]:
            raise ValueError("Context not found for this relationship type")
        self.historical_context_relationships[relationship_type].remove(context)

    def get_historical_context_relationships(self) -> dict:
        return self.historical_context_relationships
    
    def add_relationship_event(self, person_id:str, event:str, date:str):
        if person_id not in self.relationship_timeline:
            self.relationship_timeline[person_id] = []
        self.relationship_timeline[person_id].append({"event": event, "date": date})
    
    def get_relationship_timeline(self) -> dict:
        return self.relationship_timeline
    
    def add_custom_relationship(self, relationship_name: str, person_id: str):
        if relationship_name not in self.custom_relationships:
            self.custom_relationships[relationship_name] = []
        if person_id in self.custom_relationships[relationship_name]:
            raise ValueError(f"Person {person_id} already has relationship {relationship_name} with this person.")
        self.custom_relationships[relationship_name].append(person_id)

    def remove_custom_relationship(self, relationship_name: str, person_id: str):
        if relationship_name not in self.custom_relationships:
            raise ValueError(f"Relationship {relationship_name} not found.")
        if person_id not in self.custom_relationships[relationship_name]:
            raise ValueError(f"Person {person_id} not found in relationship {relationship_name}.")
        self.custom_relationships[relationship_name].remove(person_id)

    def get_custom_relationships(self) -> dict:
        return self.custom_relationships
    
    def get_person_info(self) -> dict:
        """
        Returns a dictionary with all the information of the person.
        """
        return {
            "person_id": self.person_id,
            "names": self.names,
            "gender": self.gender,
            "romanization": self.romanization,
            "transliteration": self.transliteration,
            "religious_affiliations": self.religious_affiliations,
            "current_location": self.current_location,
            "privacy_settings": self.privacy_settings,
            "biography": self.biography,
            "date_of_birth": self.date_of_birth,
            "place_of_birth": self.place_of_birth,
            "date_of_death": self.date_of_death,
            "place_of_death": self.place_of_death,
            "profile_photo": self.profile_photo,
            "parents": [p.person_id for p in self.get_parents()],
            "children": [c.person_id for c in self.get_children()],
            "spouses": [s.person_id for s in self.get_spouses()],
            "siblings": [s.person_id for s in self.get_siblings()],
            "grandparents": self.relationships.get("grandparents", []),
            "aunt_uncles": self.relationships.get("aunt_uncles", []),
            "cousins": self.relationships.get("cousins", []),
            "inlaws": [inlaw.person_id for inlaw in self.get_inlaws()],
            "extended_family": [ex.person_id for ex in self.get_extended_family()],
            "documents": self.documents,
            "media": self.media,
            "military_service_records": self.military_service_records,
            "educational_history": self.educational_history,
            "occupational_history": self.occupational_history,
            "medical_history": self.medical_history,
            "dna_haplogroups": self.dna_haplogroups,
            "physical_characteristics": self.physical_characteristics,
            "languages_spoken": self.languages_spoken,
            "immigration_naturalization_records": self.immigration_naturalization_records,
            "cultural_relationships": self.cultural_relationships,
            "godparents": self.godparents,
            "foster_relationships": self.foster_relationships,
            "guardian_relationships": self.guardian_relationships,
            "tribal_clan_affiliations": self.tribal_clan_affiliations,
            "historical_context_relationships": self.historical_context_relationships,
            "relationship_timeline": self.relationship_timeline,
            "custom_relationships": self.custom_relationships
        }

    def __str__(self):
        return str(self.get_person_info())
