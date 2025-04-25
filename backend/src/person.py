# src/person.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import logging
from datetime import date
# Prevent circular import for type hinting
if TYPE_CHECKING:
    from src.relationship import Relationship
    from src.family_tree import FamilyTree # If needed for methods accessing the tree


@dataclass
class Person:
    """Represents an individual in the family tree."""
    person_id: str # Unique identifier
    first_name: str = ""
    last_name: str = ""
    nickname: Optional[str] = None
    birth_date: Optional[str] = None # Store as ISO string (YYYY-MM-DD)
    death_date: Optional[str] = None # Store as ISO string (YYYY-MM-DD)
    place_of_birth: Optional[str] = None # Added Place of Birth
    place_of_death: Optional[str] = None # Added Place of Death
    gender: Optional[str] = None # e.g., 'Male', 'Female', 'Other', or leave None
    notes: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict) # For other custom fields

    # --- Basic Methods ---

    def __post_init__(self):
        if not self.person_id: raise ValueError("Person ID cannot be empty.")
        if self.attributes is None: self.attributes = {}

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_display_name(self) -> str:
        base_name = self.get_full_name()
        if self.nickname: return f"{base_name} ({self.nickname})"
        return base_name

    def __repr__(self) -> str:
        return f"Person(id='{self.person_id}', name='{self.get_full_name()}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Person): return NotImplemented
        return self.person_id == other.person_id

    def __hash__(self) -> int:
        return hash(self.person_id)

    # --- Data Conversion ---

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Person object to a dictionary."""
        return {
            "person_id": self.person_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "nickname": self.nickname,
            "birth_date": self.birth_date,
            "death_date": self.death_date,
            "place_of_birth": self.place_of_birth, # Added
            "place_of_death": self.place_of_death, # Added
            "gender": self.gender,
            "notes": self.notes,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Person':
        """Creates a Person object from a dictionary."""
        required_keys = ["person_id"]
        if not all(key in data for key in required_keys):
            missing = [key for key in required_keys if key not in data]
            raise KeyError(f"Person data dictionary missing required keys: {missing}")

        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')

        return cls(
            person_id=data['person_id'],
            first_name=first_name,
            last_name=last_name,
            nickname=data.get('nickname'),
            birth_date=data.get('birth_date'),
            death_date=data.get('death_date'),
            place_of_birth=data.get('place_of_birth'), # Added
            place_of_death=data.get('place_of_death'), # Added
            gender=data.get('gender'),
            notes=data.get('notes'),
            attributes=data.get('attributes', {})
        )

    # --- Keep get_age, get_related_person_ids, etc. ---
    def get_age(self) -> Optional[int]:
        if not self.birth_date: return None
        try:
            birth_dt = date.fromisoformat(self.birth_date)
            end_date = date.today()
            if self.death_date:
                try: end_date = date.fromisoformat(self.death_date)
                except (ValueError, TypeError) as e: logging.warning(f"get_age: Invalid death date format for {self.person_id}: {self.death_date}. Error: {e}")
            age = end_date.year - birth_dt.year - ((end_date.month, end_date.day) < (birth_dt.month, birth_dt.day))            
            return age
        except (ValueError, TypeError): logging.warning(f"Invalid birth date format for {self.person_id}: {self.birth_date}"); return None

    def get_related_person_ids(self, relationship_list: List['Relationship'], relationship_type: str) -> List[str]:
        related_ids = []
        for rel in relationship_list:
            if rel.rel_type.lower() == relationship_type.lower(): related_ids.append(rel.person2_id)
        return related_ids

    def get_parents(self, relationship_list: List['Relationship']) -> List[str]:
        logging.warning(f"get_parents: method called for person {self.person_id} - This logic likely belongs in FamilyTree for accurate results.")
        return []

    def get_children(self, relationship_list: List['Relationship']) -> List[str]:
        return self.get_related_person_ids(relationship_list, 'parent')

    def get_spouses(self, relationship_list: List['Relationship']) -> List[str]:
        return self.get_related_person_ids(relationship_list, 'spouse')

    def get_siblings(self, family_tree: 'FamilyTree') -> List[str]:        
        if family_tree is None: logging.error(f"get_siblings: Cannot get siblings for person {self.person_id} without FamilyTree instance."); return []
        siblings = set()
        parent_ids = family_tree.find_parents(self.person_id) # Assumes method exists
        if not parent_ids: return []
        for parent_id in parent_ids:
            children_of_parent = family_tree.find_children(parent_id) # Assumes method exists
            for child_id in children_of_parent:
                if child_id != self.person_id: siblings.add(child_id)
        return list(siblings)

