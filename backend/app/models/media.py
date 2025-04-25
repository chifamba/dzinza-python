# backend/app/models/media.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text # Import Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base # Import shared Base

class Media(Base):
    __tablename__ = "media"
    # id is inherited from Base

    person_id = Column(Integer, ForeignKey("people.id", ondelete='SET NULL')) # Correct FK table name, consider ondelete behavior
    media_type = Column(String(50)) # Added length
    file_path = Column(String(512), nullable=False) # Added length, nullable
    title = Column(String(255)) # Added length
    description = Column(Text) # Use Text
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to Person
    person = relationship("Person", back_populates="media")

    def to_dict(self):
        """Returns a dictionary representation of the media."""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "media_type": self.media_type,
            "file_path": self.file_path,
            "title": self.title,
            "description": self.description,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
