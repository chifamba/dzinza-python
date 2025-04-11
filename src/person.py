from src.family_tree import FamilyTree

class Person:
    def __init__(self, person_id, first_name, last_name, date_of_birth, place_of_birth, date_of_death=None, place_of_death=None, family_tree = None):
        self.person_id = person_id
        self.first_name = first_name
        self.last_name = last_name
        self.gender = None
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
    
    def set_family_tree(self, family_tree:FamilyTree):
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
    
    