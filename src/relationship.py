# src/relationship.py
from datetime import datetime
from typing import Optional, Dict, Any

# Define allowed relationship types (can be expanded)
RELATIONSHIP_TYPES = [
    "parent",      # Person 1 is the parent of Person 2
    "child",       # Person 1 is the child of Person 2
    "spouse",      # Persons 1 and 2 are spouses/partners
    "sibling",     # Persons 1 and 2 are siblings (consider adding half/step later)
    "adopted_child", # Person 1 is adopted child of Person 2
    "adoptive_parent", # Person 1 is adoptive parent of Person 2
    "guardian",    # Person 1 is guardian of Person 2
    "ward",        # Person 1 is ward of Person 2
    "godparent",   # Person 1 is godparent of Person 2
    "godchild",    # Person 1 is godchild of Person 2
    "friend",      # Generic friendship
    "other"        # For custom or undefined relationships
]

class Relationship:
    """
    Represents a relationship between two individuals.

    Attributes:
        person1_id (str): The ID of the first person in the relationship.
        person2_id (str): The ID of the second person in the relationship.
        relationship_type (str): The type of relationship (e.g., 'parent', 'spouse').
        start_date (Optional[datetime]): The start date of the relationship.
        end_date (Optional[datetime]): The end date of the relationship.
        description (Optional[str]): Additional details about the relationship.
    """
    def __init__(self,
                 person1_id: str,
                 person2_id: str,
                 relationship_type: str,
                 start_date: Optional[str] = None, # Accept string
                 end_date: Optional[str] = None,   # Accept string
                 description: Optional[str] = None):

        if person1_id == person2_id:
             raise ValueError("Cannot create a relationship between a person and themselves.")

        self.person1_id = person1_id
        self.person2_id = person2_id

        if relationship_type not in RELATIONSHIP_TYPES:
            # Option: Allow any string, or raise error for strictness
            print(f"Warning: Relationship type '{relationship_type}' is not standard. Allowed types: {RELATIONSHIP_TYPES}")
            # raise ValueError(f"Invalid relationship type: {relationship_type}. Allowed: {RELATIONSHIP_TYPES}")
        self.relationship_type = relationship_type

        self.start_date = self._parse_date(start_date)
        self.end_date = self._parse_date(end_date)
        self.description = description

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Helper to parse date strings into datetime objects."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace(' ', 'T'))
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                 print(f"Warning: Could not parse date string: {date_str}")
                 return None

    def involves_person(self, person_id: str) -> bool:
        """Checks if the given person ID is part of this relationship."""
        return self.person1_id == person_id or self.person2_id == person_id

    def get_other_person(self, person_id: str) -> Optional[str]:
        """Given one person ID in the relationship, returns the other."""
        if self.person1_id == person_id:
            return self.person2_id
        elif self.person2_id == person_id:
            return self.person1_id
        else:
            return None # Person not involved in this relationship

    def to_dict(self) -> Dict[str, Any]:
         """Returns a dictionary representation of the relationship."""
         return {
             "person1_id": self.person1_id,
             "person2_id": self.person2_id,
             "relationship_type": self.relationship_type,
             "start_date": self.start_date.isoformat() if self.start_date else None,
             "end_date": self.end_date.isoformat() if self.end_date else None,
             "description": self.description,
         }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
         """Creates a Relationship object from a dictionary."""
         return cls(
             person1_id=data["person1_id"],
             person2_id=data["person2_id"],
             relationship_type=data["relationship_type"],
             start_date=data.get("start_date"), # Pass string directly
             end_date=data.get("end_date"),     # Pass string directly
             description=data.get("description"),
         )

    def __eq__(self, other: object) -> bool:
        """
        Equality check based on the persons involved and relationship type.
        Order of person1_id and person2_id doesn't matter for equality check
        if the relationship type is symmetrical (like spouse, sibling).
        """
        if not isinstance(other, Relationship):
            return NotImplemented

        # Check basic type and description first
        if self.relationship_type != other.relationship_type or \
           self.start_date != other.start_date or \
           self.end_date != other.end_date or \
           self.description != other.description:
            return False

        # Check person IDs, considering symmetrical relationships
        symmetric_types = ["spouse", "sibling", "friend"] # Add others if needed
        if self.relationship_type in symmetric_types:
            return {self.person1_id, self.person2_id} == {other.person1_id, other.person2_id}
        else: # Asymmetrical (parent/child, guardian/ward) - order matters
            return (self.person1_id == other.person1_id and
                    self.person2_id == other.person2_id)

    def __hash__(self) -> int:
        """
        Hash calculation consistent with __eq__.
        Uses frozenset for person IDs in symmetrical relationships.
        """
        symmetric_types = ["spouse", "sibling", "friend"]
        if self.relationship_type in symmetric_types:
            person_ids_tuple = tuple(sorted({self.person1_id, self.person2_id}))
        else:
            person_ids_tuple = (self.person1_id, self.person2_id)

        return hash((
            person_ids_tuple,
            self.relationship_type,
            self.start_date,
            self.end_date,
            self.description
        ))

    def __str__(self) -> str:
        """User-friendly string representation."""
        date_info = ""
        if self.start_date:
            date_info += f" from {self.start_date.strftime('%Y-%m-%d')}"
        if self.end_date:
            date_info += f" to {self.end_date.strftime('%Y-%m-%d')}"
        desc = f" ({self.description})" if self.description else ""

        return (f"Relationship: {self.person1_id} <-> {self.person2_id} "
                f"({self.relationship_type}){date_info}{desc}")

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (f"Relationship(person1_id='{self.person1_id}', person2_id='{self.person2_id}', "
                f"relationship_type='{self.relationship_type}', start_date={self.start_date}, "
                f"end_date={self.end_date}, description='{self.description}')")

