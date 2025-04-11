from src.family_tree import FamilyTree, Person
from src.user_management import UserManager
from src.user import User
import time
from datetime import datetime


# Create a FamilyTree instance
family_tree = FamilyTree()


def __init__(self, person_id, first_name, last_name, date_of_birth, place_of_birth, date_of_death=None, place_of_death=None, family_tree=None):
        self.names = []
        self.person_id = person_id
        self.gender = None
        self.add_name(name=first_name, type="first", culture="default")
        self.add_name(name=last_name, type="last", culture="default")
        self.romanization = None
        self.transliteration = None
        self.religious_affiliations = []
        self.current_location = None
        self.privacy_settings = None
        self.biography = ""
        self.date_of_birth = date_of_birth
        self.place_of_birth = place_of_birth
        self.date_of_death = date_of_death
        self.place_of_death = place_of_death
        self.family_tree:FamilyTree = family_tree
        self.profile_photo = None
        self.relationships = {}
        self.init_extended_relationships()
        self.documents: list[str] = []
        self.media: list[str] = []
        self.military_service_records: list[str] = []
        self.educational_history: list[str] = []
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

    def add_parent(self, parent_id):
        if "parent" not in self.relationships:
            self.relationships["parent"] = []
        self.relationships["parent"].append(parent_id)

    def add_child(self, child_id):
        if "child" not in self.relationships:
            self.relationships["child"] = []
        self.relationships["child"].append(child_id)

    def add_spouse(self, spouse_id):
        if "spouse" not in self.relationships:
            self.relationships["spouse"] = []
        self.relationships["spouse"].append(spouse_id)

    def add_sibling(self, sibling_id):
        if "sibling" not in self.relationships:
            self.relationships["sibling"] = []
        self.relationships["sibling"].append(sibling_id)

    def add_grandparent(self, grandparent_id):
        if "grandparents" not in self.relationships:
            raise ValueError("Relationship not found")
        if grandparent_id in self.relationships["grandparents"]:
            raise ValueError("Person is already in this relationship")
        self.relationships["grandparents"].append(grandparent_id)

    def add_aunt_uncle(self, aunt_uncle_id):
        if "aunt_uncles" not in self.relationships:
            raise ValueError("Relationship not found")
        if aunt_uncle_id in self.relationships["aunt_uncles"]:
            raise ValueError("Person is already in this relationship")
        self.relationships["aunt_uncles"].append(aunt_uncle_id)

    def add_cousin(self, cousin_id):
        if "cousins" not in self.relationships:
            raise ValueError("Relationship not found")
        if cousin_id in self.relationships["cousins"]:
            raise ValueError("Person is already in this relationship")
        self.relationships["cousins"].append(cousin_id)

    def add_inlaw(self, inlaw_id):
        if inlaw_id in self.relationships.get("inlaws", []):
            raise ValueError("Person is already in this relationship")
        self.relationships["inlaws"].append(inlaw_id)
    def get_parents(self) -> list:
        parents_ids = self.relationships.get("parent", [])
        return [self.family_tree.get_person(parent_id) for parent_id in parents_ids]

    def get_children(self) -> list:
        children_ids = self.relationships.get("child", [])
        return [self.family_tree.get_person(child_id) for child_id in children_ids]

    def get_spouses(self) -> list:
        spouses_ids = self.relationships.get("spouse", [])
        return [self.family_tree.get_person(spouse_id) for spouse_id in spouses_ids]

    def get_siblings(self) -> list:
        siblings_ids = self.relationships.get("sibling", [])
        return [self.family_tree.get_person(sibling_id) for sibling_id in siblings_ids]
    
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

    def add_document(self, document: str):
        self.documents.append(document)

    def remove_document(self, document: str):
        if document in self.documents:
            self.documents.remove(document)
        else:
            raise ValueError("Document not found")

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
        return self.medical_history

    def set_dna_haplogroups(self, haplogroups):
        self.dna_haplogroups = haplogroups
    
    def get_dna_haplogroups(self) -> list:
        return self.dna_haplogroups

    def add_physical_characteristic(self, characteristic):
        if characteristic in self.physical_characteristics:
            raise ValueError("Characteristic already exists")
        self.physical_characteristics.append(characteristic)

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


# Example Usage

# Create a UserManager instance
user_manager = UserManager()

# Create users
user1 = user_manager.create_user("user1", "user1@example.com", "password")
user2 = user_manager.create_user("user2", "user2@example.com", "password")
user3 = user_manager.create_user("user3", "user3@example.com", "password")
user4 = user_manager.create_user("user4", "user4@example.com", "password")

person1 = Person(user1.user_id, "John", "Doe", "1980-01-01", "New York", family_tree=family_tree)
person2 = Person(user2.user_id, "Jane", "Doe", "1982-05-15", "Los Angeles", family_tree=family_tree)
person3 = Person(user3.user_id, "Peter", "Pan", "1990-03-20", "Neverland", family_tree=family_tree)
person4 = Person(user4.user_id, "Wendy", "Darling", "1992-11-10", "London", family_tree=family_tree)


# Add the persons to the family tree
family_tree.add_person(person1)