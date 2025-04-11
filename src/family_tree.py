from src.person import Person

class FamilyTree:
    def __init__(self, root_person: Person = None):
        self.root_person = root_person
        self.person_nodes = {}
        if root_person:
            self.person_nodes[root_person.user_id] = {"person": root_person, "parent": None, "children": []}

    def add_person(self, person: Person, parent: Person = None):
        if not self.root_person and parent:
            raise ValueError("Cannot add a person with a parent if the tree is empty")
        if self.root_person and not parent:
            raise ValueError("Cannot add a root person if the tree already has a root")
        if parent and parent.user_id not in self.person_nodes:
            raise ValueError("Parent not found in the family tree")

        if person.user_id in self.person_nodes:
            raise ValueError("Person already exists in the family tree")
        
        self.person_nodes[person.user_id] = {"person": person, "parent": parent, "children": []}

        if parent:
            self.person_nodes[parent.user_id]["children"].append(person)


    def get_person(self, person_id: int):
        if person_id not in self.person_nodes:
            raise ValueError("Person not found in the family tree")
        return self.person_nodes[person_id]["person"]