# backend/app/models/relationship_attribute.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Index # Import Text, Index
from sqlalchemy.orm import relationship
from .base import Base # Import shared Base

class RelationshipAttribute(Base):
    __tablename__ = "relationship_attributes"
    # id is inherited from Base

    relationship_id = Column(Integer, ForeignKey("relationships.id", ondelete='CASCADE'), nullable=False) # Added nullable and ondelete
    key = Column(String(100), nullable=False) # Added length and nullable
    value = Column(Text) # Use Text for potentially long values

    # Relationship back to Relationship
    relationship = relationship("Relationship", back_populates="attributes")

    # Add indexes
    __table_args__ = (
        Index('ix_relationship_attributes_relationship_id', 'relationship_id'),
        Index('ix_relationship_attributes_key', 'key'),
    )

    def to_dict(self):
        """Returns a dictionary representation of the attribute."""
        return {
            "id": self.id,
            "relationship_id": self.relationship_id,
            "key": self.key,
            "value": self.value,
        }
