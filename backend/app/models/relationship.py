# backend/app/models/relationship.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index # Import Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base # Import shared Base

class Relationship(Base):
    __tablename__ = "relationships"
    # id is inherited from Base

    person1_id = Column(Integer, ForeignKey("people.id", ondelete='CASCADE'), nullable=False) # Added nullable=False and ondelete
    person2_id = Column(Integer, ForeignKey("people.id", ondelete='CASCADE'), nullable=False) # Added nullable=False and ondelete
    rel_type = Column(String(50), nullable=False) # Added length and nullable=False
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships back to Person
    person1 = relationship("Person", foreign_keys=[person1_id], back_populates="person1_relationships")
    person2 = relationship("Person", foreign_keys=[person2_id], back_populates="person2_relationships")

    # Relationship to RelationshipAttribute
    attributes = relationship("RelationshipAttribute", back_populates="relationship", cascade="all, delete-orphan")

    # Add indexes for faster lookups
    __table_args__ = (
        Index('ix_relationships_person1_id', 'person1_id'),
        Index('ix_relationships_person2_id', 'person2_id'),
        Index('ix_relationships_rel_type', 'rel_type'),
    )

    def to_dict(self):
        """Returns a dictionary representation of the relationship."""
        return {
            "id": self.id,
            "person1_id": self.person1_id,
            "person2_id": self.person2_id,
            "rel_type": self.rel_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
