from src.person import Person
from src.relationship import Relationship


class FamilyTree:
    def __init__(self, root_person: Person = None):
        self.root_person = root_person
        self.person_nodes = {}
        if root_person:
            self.person_nodes[root_person.user_id] = {"person": root_person, "parent": None, "children": []}

    def add_person(self, person: Person, parents: list[Person] = None):
        if not self.root_person and parents:
            raise ValueError("Cannot add a person with parents if the tree is empty")        
        if person.user_id in self.person_nodes:
            raise ValueError("Person already exists in the family tree")

        if parents:
            for parent in parents:
                if parent.user_id not in self.person_nodes:
                    raise ValueError(f"Parent with ID {parent.user_id} not found in the family tree")

        if not self.root_person and not parents:
             self.root_person = person
        elif self.root_person and not parents:
            raise ValueError("Cannot add a root person if the tree already has a root")

        self.person_nodes[person.user_id] = {"person": person, "parents": parents or [], "children": []}

        if parents:
            for parent in parents:
                self.person_nodes[parent.user_id]["children"].append(person)

    def link_persons(self, person1_id, person2_id, relationship_type):
        person1 = self.get_person_by_id(person1_id)
        person2 = self.get_person_by_id(person2_id)

        if not person1 or not person2:
            raise ValueError("One or both persons not found in the family tree")
        
        if relationship_type == 'parent':
            person2.add_parent(person1_id)
            person1.add_child(person2_id)
        elif relationship_type == 'child':
            person1.add_parent(person2_id)
            person2.add_child(person1_id)


    def add_relationship(self, relationship: Relationship):
        person1 = relationship.person1
        person2 = relationship.person2

        if person1.user_id not in self.person_nodes or person2.user_id not in self.person_nodes:
            raise ValueError("One or both persons are not in the family tree")

        person1.add_relationship(relationship)
        person2.add_relationship(relationship)

    def get_person(self, person_id: int):
        person_data = self.person_nodes.get(person_id)
        return person_data["person"] if person_data else None
    
    def get_person_by_id(self, person_id: int):
        person_data = self.person_nodes.get(person_id)
        return person_data["person"] if person_data else None