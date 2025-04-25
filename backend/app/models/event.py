# backend/app/models/event.py
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Index # Import Text, Index
from sqlalchemy.orm import relationship # Import relationship
from sqlalchemy.sql import func # Import func
from .base import Base # Import shared Base

class Event(Base):
    __tablename__ = 'events'
    # id is inherited from Base

    person_id = Column(Integer, ForeignKey('people.id', ondelete='CASCADE'), nullable=False) # Added nullable and ondelete
    event_type = Column(String(100), nullable=False) # Added length and nullable
    date = Column(Date)
    place = Column(String(255)) # Added length
    description = Column(Text) # Use Text
    created_at = Column(DateTime, server_default=func.now()) # Use server_default

    # Relationship back to Person
    person = relationship("Person", back_populates="events")
    # Relationship to Citation
    citations = relationship("Citation", back_populates="event", cascade="all, delete-orphan")

    # Add indexes
    __table_args__ = (
        Index('ix_events_person_id', 'person_id'),
        Index('ix_events_event_type', 'event_type'),
        Index('ix_events_date', 'date'),
    )

    def to_dict(self):
        """Returns a dictionary representation of the event."""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "event_type": self.event_type,
            "date": self.date.isoformat() if self.date else None,
            "place": self.place,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
