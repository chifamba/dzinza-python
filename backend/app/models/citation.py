# backend/app/models/citation.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index # Import Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base # Import shared Base

class Citation(Base):
    __tablename__ = "citations"
    # id is inherited from Base

    # Foreign keys - make nullable depending on whether a citation MUST link to all/some
    source_id = Column(Integer, ForeignKey("sources.id", ondelete='CASCADE'), nullable=False) # Added nullable and ondelete
    person_id = Column(Integer, ForeignKey("people.id", ondelete='CASCADE'), nullable=True) # Allow citation not linked to person?
    event_id = Column(Integer, ForeignKey("events.id", ondelete='CASCADE'), nullable=True) # Allow citation not linked to event?

    citation_text = Column(Text) # Use Text
    page_number = Column(String(50)) # Added length
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source = relationship("Source", back_populates="citations")
    person = relationship("Person", back_populates="citations")
    event = relationship("Event", back_populates="citations")

    # Add indexes
    __table_args__ = (
        Index('ix_citations_source_id', 'source_id'),
        Index('ix_citations_person_id', 'person_id'),
        Index('ix_citations_event_id', 'event_id'),
    )

    def to_dict(self):
        """Returns a dictionary representation of the citation."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "person_id": self.person_id,
            "event_id": self.event_id,
            "citation_text": self.citation_text,
            "page_number": self.page_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
