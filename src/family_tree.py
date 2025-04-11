from src.person import Person
from src.relationship import Relationship


class FamilyTree:
    def __init__(self, root_person: Person = None):
        """
        Initializes the FamilyTree with an optional root person.

        Args:
            root_person (Person, optional): The root person of the family tree. Defaults to None.

        Attributes:
            root_person (Person): The root person of the family tree.
            person_nodes (dict): A dictionary to store each person's node information, keyed by user_id.
                Each node contains:
                    - person (Person): The Person object.
                    - parents (list): A list of parent Person objects.
                    - children (list): A list of child Person objects.
        """
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
    
    def display_tree(self, person_id=None, indent=0):
        """
        Displays the family tree in a hierarchical view, starting from the specified person or the root.

        Args:
            person_id (int, optional): The ID of the person to start displaying the tree from. 
                                        If None, starts from the root person. Defaults to None.
            indent (int, optional): The current indentation level for hierarchical display. Defaults to 0.
        """
        if person_id is None:
            if self.root_person is None:
                print("The family tree is empty.")
                return
            person_id = self.root_person.user_id

        person_data = self.person_nodes.get(person_id)
        if not person_data:
            return

        person = person_data["person"]
        print("  " * indent + f"ID: {person.user_id}, Name: {person.get_names()}")
        
        for child_person in person.get_children(self):
            self.display_tree(child_person.user_id, indent + 1)


