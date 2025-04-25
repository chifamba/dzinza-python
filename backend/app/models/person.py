# backend/app/models/person.py
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text # Import Text for notes
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
from typing import Dict, Any, Optional

class Person(Base):
    __tablename__ = "people"
    # id is inherited from Base

    first_name = Column(String(100), index=True) # Added length and index
    last_name = Column(String(100), index=True) # Added length and index
    nickname = Column(String(100)) # Added length
    gender = Column(String(20)) # Added length
    birth_date = Column(Date)
    death_date = Column(Date)
    place_of_birth = Column(String(255)) # Added length
    place_of_death = Column(String(255)) # Added length
    notes = Column(Text) # Use Text for potentially long notes
    created_by = Column(Integer, ForeignKey("users.id")) # Ensure FK matches users table PK
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="created_people")
    attributes = relationship("PersonAttribute", back_populates="person", cascade="all, delete-orphan")
    media = relationship("Media", back_populates="person", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="person", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="person", cascade="all, delete-orphan")

    # Relationships to the Relationship table itself
    person1_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.person1_id",
        back_populates="person1",
        cascade="all, delete-orphan" # Decide if deleting a person deletes relationships
    )
    person2_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.person2_id",
        back_populates="person2",
        cascade="all, delete-orphan" # Decide if deleting a person deletes relationships
    )

    def to_dict(self, fields: Optional[list[str]] = None) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the person.
        If 'fields' is provided, only includes those fields.
        """
        if fields:
            data = {field: getattr(self, field, None) for field in fields if hasattr(self, field)}
            # Ensure essential ID field is always present if requested or not
            if 'id' not in data:
                data['id'] = self.id
        else:
            data = {
                "id": self.id,
                "first_name": self.first_name,
                "last_name": self.last_name,
                "nickname": self.nickname,
                "gender": self.gender,
                "birth_date": self.birth_date.isoformat() if self.birth_date else None,
                "death_date": self.death_date.isoformat() if self.death_date else None,
                "place_of_birth": self.place_of_birth,
                "place_of_death": self.place_of_death,
                "notes": self.notes,
                "created_by": self.created_by,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        return data

