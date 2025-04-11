class Person:
    def __init__(self, person_id, first_name, last_name, date_of_birth, place_of_birth, date_of_death=None, place_of_death=None):
        self.person_id = person_id
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.place_of_birth = place_of_birth
        self.date_of_death = date_of_death
        self.place_of_death = place_of_death
        self.relationships = {}

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

    def get_parents(self):
        return self.relationships.get("parent", [])
    
    def get_children(self):
        return self.relationships.get("child", [])
    
    def get_spouses(self):
        return self.relationships.get("spouse", [])
    
    def get_siblings(self):
        return self.relationships.get("sibling", [])