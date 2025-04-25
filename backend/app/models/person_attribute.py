# backend/app/models/person_attribute.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Index # Import Text, Index
from sqlalchemy.orm import relationship
from .base import Base # Import shared Base

class PersonAttribute(Base):
    __tablename__ = "person_attributes"
    # id is inherited from Base

    person_id = Column(Integer, ForeignKey("people.id", ondelete='CASCADE'), nullable=False) # Added nullable and ondelete
    key = Column(String(100), nullable=False) # Added length and nullable
    value = Column(Text) # Use Text for potentially long values

    # Relationship back to Person
    person = relationship("Person", back_populates="attributes")

    # Add indexes
    __table_args__ = (
        Index('ix_person_attributes_person_id', 'person_id'),
        Index('ix_person_attributes_key', 'key'),
    )

    def to_dict(self):
        """Returns a dictionary representation of the attribute."""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "key": self.key,
            "value": self.value,
        }
