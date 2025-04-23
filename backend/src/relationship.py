# src/relationship.py

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import logging
import uuid # Import uuid for potential rel_id generation if needed

# Define known relationship types and their reciprocals
# Use lowercase for consistency
RELATIONSHIP_MAP = {
    "spouse": "spouse",
    "parent": "child",
    "child": "parent",
    "sibling": "sibling",
    "grandparent": "grandchild",
    "grandchild": "grandparent",
    "aunt": "nephew/niece", # Consider gendered reciprocals or use neutral?
    "uncle": "nephew/niece",
    "nephew": "aunt/uncle",
    "niece": "aunt/uncle",
    "cousin": "cousin",
    "step-parent": "step-child",
    "step-child": "step-parent",
    "step-sibling": "step-sibling",
    "adopted child": "adoptive parent", # Use specific terms
    "adoptive parent": "adopted child",
    "godparent": "godchild",
    "godchild": "godparent",
    "friend": "friend", # Example non-familial
    "partner": "partner", # Gender-neutral alternative to spouse
    "divorced": "divorced", # State rather than relationship type? Or use attributes.
    # Add more as needed
}

# Generate a list of valid types from the map keys
VALID_RELATIONSHIP_TYPES = list(RELATIONSHIP_MAP.keys())

def get_reciprocal_relationship(rel_type: str) -> str:
    """
    Determines the reciprocal relationship type.

    Args:
        rel_type: The relationship type (e.g., 'parent', 'spouse'). Case-insensitive.

    Returns:
        The reciprocal relationship type (e.g., 'child', 'spouse'), or the original
        type if no specific reciprocal is defined.
    """
    if not rel_type: # Handle empty string case
        return ""
    logging.debug(f"Getting reciprocal relationship for: {rel_type}")
    rel_type_lower = rel_type.lower()
    # Direct lookup
    if rel_type_lower in RELATIONSHIP_MAP:
        return RELATIONSHIP_MAP[rel_type_lower]

    # Check if it's a value (reciprocal) in the map
    for key, value in RELATIONSHIP_MAP.items():
        if rel_type_lower == value:
            # Find the corresponding key(s)
            reciprocal_keys = [k for k, v in RELATIONSHIP_MAP.items() if v == rel_type_lower]
            if reciprocal_keys:
                # If multiple keys map to this value (like aunt/uncle -> nephew/niece),
                # returning the first one found or a combined string might be options.
                # Returning the first found key for simplicity here.
                logging.debug(f"Reciprocal keys found: {reciprocal_keys}")
                return reciprocal_keys[0]
    logging.warning(f"No specific reciprocal found for relationship type '{rel_type}'. Returning original.")
    # Default: return the original type if no reciprocal mapping found
    return rel_type # Return original type if not found


@dataclass
class Relationship:
    """
    Represents a relationship between two individuals in the family tree.
    Stores the relationship from the perspective of person1.

    Attributes:
        person1_id (str): ID of the first person in the relationship.
        person2_id (str): ID of the second person in the relationship.
        rel_type (str): Type of relationship from person1 to person2 (e.g., 'parent', 'spouse').
        rel_id (str): Unique identifier for the relationship instance. Generated if not provided.
        attributes (Optional[Dict[str, Any]]): Dictionary for custom attributes like dates, notes.
    """
    person1_id: str
    person2_id: str
    rel_type: str
    rel_id: str = field(default_factory=lambda: str(uuid.uuid4())) # Auto-generate ID if not provided
    attributes: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization checks and setup."""
        logging.debug(f"Initializing Relationship object: {self.rel_id}")
        # Ensure IDs are strings
        if not isinstance(self.person1_id, str) or not self.person1_id:
             raise ValueError("person1_id must be a non-empty string")
        if not isinstance(self.person2_id, str) or not self.person2_id:
             raise ValueError("person2_id must be a non-empty string")
        if not isinstance(self.rel_type, str) or not self.rel_type:
             raise ValueError("rel_type must be a non-empty string")
        if not isinstance(self.rel_id, str) or not self.rel_id:
             raise ValueError("rel_id must be a non-empty string")

        # Validate rel_type against known types (optional warning)
        if self.rel_type.lower() not in VALID_RELATIONSHIP_TYPES:
            logging.warning(f"Relationship {self.rel_id} created with potentially invalid type: '{self.rel_type}'")

        # Ensure attributes is a dict
        if self.attributes is None:
            self.attributes = {}
        elif not isinstance(self.attributes, dict):
             logging.warning(f"Relationship {self.rel_id} attributes initialized with non-dict type ({type(self.attributes)}). Setting to empty dict.")
             self.attributes = {}


    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Relationship(id={self.rel_id}, p1={self.person1_id}, p2={self.person2_id}, type='{self.rel_type}')"

    def __str__(self) -> str:
        """Provides a user-friendly string representation."""
        # Potentially fetch names if a FamilyTree instance is available?
        # For now, just show IDs and type.
        return f"{self.person1_id} -> {self.person2_id} ({self.rel_type})"

    def __eq__(self, other: object) -> bool:
        """Checks equality based on rel_id."""
        if not isinstance(other, Relationship):
            return NotImplemented
        # Primary key for equality is the relationship ID
        return self.rel_id == other.rel_id

    def __hash__(self) -> int:
         """Hashes based on the unique relationship ID."""
         return hash(self.rel_id)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Relationship object to a dictionary."""
        return {
            "rel_id": self.rel_id,
            "person1_id": self.person1_id,
            "person2_id": self.person2_id,
            "rel_type": self.rel_type,
            "attributes": self.attributes if self.attributes is not None else {} # Ensure attributes is always a dict
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """
        Creates a Relationship object from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary containing relationship data.
                                   Expected keys: 'person1_id', 'person2_id', 'rel_type'.
                                   Optional keys: 'rel_id', 'attributes'.

        Returns:
            Relationship: An instance of the Relationship class.

        Raises:
            KeyError: If required keys ('person1_id', 'person2_id', 'rel_type') are missing.
            ValueError: If any ID or type field is invalid (e.g., not a string, empty).
        """
        # Handle potential variations in key names ('type' vs 'rel_type') for robustness
        rel_type = data.get('rel_type', data.get('type'))
        if rel_type is None:
             raise KeyError("Relationship data must include 'rel_type' or 'type'.")

        # Get required fields, letting KeyError propagate if missing
        person1_id = data['person1_id']
        person2_id = data['person2_id']

        # Get optional fields
        rel_id = data.get('rel_id') # If missing, __init__ will generate one
        attributes = data.get('attributes') # Defaults to None if missing, handled by __post_init__

        logging.debug(f"Creating relationship from dict. Provided rel_id: {rel_id}, Data: {data}")

        # Use cls() which calls __init__ and __post_init__
        # The extra parenthesis was removed from the end of this return statement
        return cls(
            rel_id=rel_id, # Pass rel_id if present, otherwise default factory in __init__ handles it
            person1_id=person1_id,
            person2_id=person2_id,
            rel_type=rel_type,
            attributes=attributes
        )
