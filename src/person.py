from src.family_tree import FamilyTree

class Person:    
    def __init__(self, person_id, first_name, last_name, date_of_birth, place_of_birth, date_of_death=None, place_of_death=None, family_tree = None):
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
        self.documents: list[str] = []
        self.media: list[str] = []
        self.military_service_records: list[str] = []
        self.educational_history: list[str] = []
        self.occupational_history: list[str] = []
        self.medical_history: list[str] = []
        self.dna_haplogroups: list[str] = []
        self.physical_characteristics: list[str] = []
        self.languages_spoken: list[str] = []

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
    