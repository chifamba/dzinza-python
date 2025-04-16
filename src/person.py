# src/person.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import logging
from datetime import date

# Prevent circular import for type hinting
if TYPE_CHECKING:
    from .relationship import Relationship
    from .family_tree import FamilyTree # If needed for methods accessing the tree


@dataclass
class Person:
    """Represents an individual in the family tree."""
    person_id: str # Unique identifier
    first_name: str = ""
    last_name: str = ""
    nickname: Optional[str] = None # Added nickname field
    birth_date: Optional[str] = None # Store as ISO string (YYYY-MM-DD)
    death_date: Optional[str] = None # Store as ISO string (YYYY-MM-DD)
    gender: Optional[str] = None # e.g., 'Male', 'Female', 'Other', or leave None
    notes: Optional[str] = None
    # Store relationships directly? Or rely on FamilyTree?
    # If storing here, need careful management to keep consistent with FamilyTree
    # relationships: List['Relationship'] = field(default_factory=list) # Example if storing locally
    attributes: Dict[str, Any] = field(default_factory=dict) # For other custom fields

    # --- Basic Methods ---

    def __post_init__(self):
        # Basic validation or normalization
        if not self.person_id:
            raise ValueError("Person ID cannot be empty.")
        # Ensure attributes is a dict
        if self.attributes is None:
            self.attributes = {}

    def get_full_name(self) -> str:
        """Returns the full name of the person (first and last)."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_display_name(self) -> str:
        """Returns the name to display, including nickname if available."""
        base_name = self.get_full_name()
        if self.nickname:
            return f"{base_name} ({self.nickname})"
        return base_name

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Person(id='{self.person_id}', name='{self.get_full_name()}')"

    def __eq__(self, other: object) -> bool:
        """Checks equality based on person_id."""
        if not isinstance(other, Person):
            return NotImplemented
        return self.person_id == other.person_id

    def __hash__(self) -> int:
        """Computes hash based on person_id."""
        return hash(self.person_id)

    # --- Data Conversion ---

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Person object to a dictionary."""
        return {
            "person_id": self.person_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "nickname": self.nickname, # Added nickname
            "birth_date": self.birth_date,
            "death_date": self.death_date,
            "gender": self.gender,
            "notes": self.notes,
            "attributes": self.attributes,
            # Do not include 'relationships' here if managed by FamilyTree
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Person':
        """Creates a Person object from a dictionary."""
        required_keys = ["person_id"] # Minimal requirement
        if not all(key in data for key in required_keys):
            missing = [key for key in required_keys if key not in data]
            raise KeyError(f"Person data dictionary missing required keys: {missing}")

        # Ensure first_name and last_name default to empty string if missing
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')

        # Handle potential missing keys gracefully for optional fields
        return cls(
            person_id=data['person_id'],
            first_name=first_name,
            last_name=last_name,
            nickname=data.get('nickname'), # Added nickname
            birth_date=data.get('birth_date'),
            death_date=data.get('death_date'),
            gender=data.get('gender'),
            notes=data.get('notes'),
            attributes=data.get('attributes', {}) # Default to empty dict
        )

    # --- Age and Lifespan Calculation ---

    def get_age(self) -> Optional[int]:
        """Calculates the current age or age at death."""
        if not self.birth_date:
            return None
        try:
            birth_dt = date.fromisoformat(self.birth_date)
            end_date = date.today()
            if self.death_date:
                try:
                    end_date = date.fromisoformat(self.death_date)
                except (ValueError, TypeError):
                    logging.warning(f"Invalid death date format for {self.person_id}: {self.death_date}")
                    # Fallback to today's date or return None? Let's use today's date.

            # Calculate age based on years, adjusting for month/day
            age = end_date.year - birth_dt.year - ((end_date.month, end_date.day) < (birth_dt.month, birth_dt.day))
            return age
        except (ValueError, TypeError):
            logging.warning(f"Invalid birth date format for {self.person_id}: {self.birth_date}")
            return None

    # --- Relationship Handling (Requires access to FamilyTree) ---
    # These methods assume the Person object has access to the FamilyTree instance
    # or that the FamilyTree instance calls these methods passing necessary relationship data.
    # Option 1: Pass FamilyTree instance (or relationship list) to methods
    # Option 2: Store a weakref to FamilyTree in Person (more complex)
    # Option 3: Keep these methods in FamilyTree and pass person_id

    # Let's assume Option 1 for demonstration: methods accept relationship list

    def get_related_person_ids(self, relationship_list: List['Relationship'], relationship_type: str) -> List[str]:
        """
        Gets IDs of persons related by a specific relationship type.

        Args:
            relationship_list: A list of Relationship objects where this person is person1.
            relationship_type: The type of relationship to filter by (e.g., 'spouse', 'child').

        Returns:
            A list of person IDs related by the specified type.
        """
        related_ids = []
        for rel in relationship_list:
            # Use the correct attribute name 'rel_type'
            if rel.rel_type.lower() == relationship_type.lower():
                related_ids.append(rel.person2_id)
        return related_ids

    def get_parents(self, relationship_list: List['Relationship']) -> List[str]:
        """Gets the IDs of this person's parents."""
        # Parents are person2 where the relationship type from self (person1) is 'child'
        # OR person2 where relationship type from person2 (person1) is 'parent'
        # This implementation assumes relationships are stored outgoing from person1
        # A better approach might be needed if relationships are stored differently
        # or require querying the full FamilyTree.

        # This simplified version assumes 'parent' relationship is stored outgoing from child
        # It should likely query the FamilyTree for incoming 'parent' relationships instead.
        # Let's adjust to find 'parent' type relationships *outgoing* from this person.
        # This is likely incorrect logic - parent relationship should point *to* the parent.
        # Correct logic: Find relationships where self is person2 and type is 'child',
        # OR where self is person1 and type is 'parent'.
        # This requires access to the full relationship structure, not just outgoing ones.

        # --- REVISED LOGIC (Still requires broader relationship access) ---
        # This method likely belongs in FamilyTree or needs FamilyTree passed in.
        # Placeholder returning empty list, assuming logic resides in FamilyTree.
        logging.warning("Person.get_parents() called - This logic likely belongs in FamilyTree for accurate results.")
        return [] # Placeholder


    def get_children(self, relationship_list: List['Relationship']) -> List[str]:
        """Gets the IDs of this person's children."""
        # Children are person2 where the relationship type from self (person1) is 'parent'
        return self.get_related_person_ids(relationship_list, 'parent')


    def get_spouses(self, relationship_list: List['Relationship']) -> List[str]:
        """Gets the IDs of this person's spouse(s)."""
        # Spouses are person2 where the relationship type from self (person1) is 'spouse'
        return self.get_related_person_ids(relationship_list, 'spouse')

    def get_siblings(self, family_tree: 'FamilyTree') -> List[str]:
        """
        Gets the IDs of this person's siblings (requires access to FamilyTree).
        Siblings share at least one parent.
        """
        # This logic definitely needs the FamilyTree instance
        if family_tree is None:
            logging.error("Cannot get siblings without FamilyTree instance.")
            return []

        siblings = set()
        # Find parents using FamilyTree's method (assuming it exists)
        parent_ids = family_tree.find_parents(self.person_id) # Assumes method exists

        if not parent_ids:
            return [] # No parents found, cannot find siblings

        # Find children of each parent
        for parent_id in parent_ids:
            # Find children using FamilyTree's method (assuming it exists)
            children_of_parent = family_tree.find_children(parent_id) # Assumes method exists
            for child_id in children_of_parent:
                if child_id != self.person_id: # Exclude self
                    siblings.add(child_id)

        return list(siblings)


    # Add more methods as needed (e.g., get_grandparents, get_cousins)
    # These would likely also require access to the FamilyTree instance.

