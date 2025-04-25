# backend/app/models/source.py
from sqlalchemy import Column, String, DateTime, Text, Index # Import Text, Index
from sqlalchemy.orm import relationship # Import relationship
from sqlalchemy.sql import func # Import func
from .base import Base # Import shared Base

class Source(Base):
    __tablename__ = 'sources'
    # id is inherited from Base

    title = Column(String(255), nullable=False) # Added length and nullable
    author = Column(String(255)) # Added length
    publication_info = Column(Text) # Use Text
    url = Column(String(512)) # Added length
    notes = Column(Text) # Use Text
    created_at = Column(DateTime, server_default=func.now()) # Use server_default

    # Relationship to Citation
    citations = relationship("Citation", back_populates="source", cascade="all, delete-orphan")

    # Add indexes
    __table_args__ = (
        Index('ix_sources_title', 'title'),
        Index('ix_sources_author', 'author'),
    )

    def to_dict(self):
        """Returns a dictionary representation of the source."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "publication_info": self.publication_info,
            "url": self.url,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
