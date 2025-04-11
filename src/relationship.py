from datetime import datetime


class Relationship:
    def __init__(self, person1_id, person2_id, relationship_type, start_date=None, end_date=None, description=None):
        self.person1_id = person1_id
        self.person2_id = person2_id
        if relationship_type not in ["parent", "child", "spouse", "sibling", "other"]:
            raise ValueError("Invalid relationship type")
        self.relationship_type = relationship_type
        self.start_date = start_date
        self.end_date = end_date
        self.description = description

    def __eq__(self, other):
        if not isinstance(other, Relationship):
            return False
        return (self.person1_id == other.person1_id and
                self.person2_id == other.person2_id and
                self.relationship_type == other.relationship_type and
                self.start_date == other.start_date and
                self.end_date == other.end_date and
                self.description == other.description)

    def __hash__(self):
        return hash((self.person1_id, self.person2_id, self.relationship_type, self.start_date, self.end_date, self.description))

    def __str__(self):
        return (f"Relationship between {self.person1_id} and {self.person2_id} "
                f"of type {self.relationship_type}. "
                f"Start date: {self.start_date}, "
                f"End date: {self.end_date}, "
                f"Description: {self.description}")