from src.relationship import Relationship


class Person:
    def __init__(self, first_name, last_name, date_of_birth, place_of_birth, date_of_death=None, place_of_death=None):
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.place_of_birth = place_of_birth
        self.date_of_death = date_of_death
        self.place_of_death = place_of_death
        self.relationships = []

    def add_relationship(self, relationship: Relationship):
        self.relationships.append(relationship)