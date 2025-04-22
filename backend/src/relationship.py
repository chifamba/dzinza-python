# src/relationship.py

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import logging  # noqa: E402

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
                # Consider refining this logic based on desired behavior for ambiguous cases.
                logging.debug(f"Reciprocal keys found: {reciprocal_keys}")
                return reciprocal_keys[0]
    logging.warning(f"No specific reciprocal found for relationship type '{rel_type}'. Returning original.")
    # Default: return the original type if no reciprocal mapping found
    logging.debug(f"No specific reciprocal found for relationship type '{rel_type}'. Returning original.")
    return rel_type # Return original type if not found


@dataclass
class Relationship:
    """
    Represents a relationship between two individuals in the family tree.
    Stores the relationship from the perspective of person1.
    """
    person1_id: str
    person2_id: str
    rel_type: str # Type of relationship from person1 to person2 (e.g., 'parent', 'spouse')
    attributes: Optional[Dict[str, Any]] = field(default_factory=dict) # e.g., start_date, end_date, location, notes

    def __post_init__(self):
        logging.debug("Initializing Relationship object")
        # Validate rel_type against known types
        if self.rel_type.lower() not in VALID_RELATIONSHIP_TYPES:
            logging.warning(f"Relationship created with potentially invalid type: '{self.rel_type}'")

        # Ensure attributes is a dict
        if self.attributes is None:
            self.attributes = {}

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Relationship: {self.person1_id} -> {self.person2_id} ({self.rel_type})"

    def __eq__(self, other: object) -> bool:
        """Checks equality based on persons involved, type, and attributes."""
        if not isinstance(other, Relationship):
            return NotImplemented
        return (self.person1_id == other.person1_id and
                self.person2_id == other.person2_id and
                self.rel_type == other.rel_type and
                self.attributes == other.attributes) # Compare attributes too

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Relationship object to a dictionary."""
        return {
            "person1_id": self.person1_id,
            "person2_id": self.person2_id,
            "rel_type": self.rel_type, # Changed 'type' to 'rel_type' for consistency
            "attributes": self.attributes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """Creates a Relationship object from a dictionary."""
        # Handle potential variations in key names ('type' vs 'rel_type')
        rel_type = data.get('rel_type', data.get('type'))
        if rel_type is None:
             raise KeyError("Relationship data must include 'rel_type' or 'type'.")
        logging.debug(f"Creating relationship from data: {data}")
        return cls(
            person1_id=data['person1_id'], # Let KeyError raise if missing
            person2_id=data['person2_id'], # Let KeyError raise if missing
            rel_type=rel_type,
            attributes=data.get('attributes') # Defaults to None if missing, handled by __post_init__
        )
        )

