# backend/app/models/user.py
from sqlalchemy import Column, String, DateTime, func # Removed Integer since ID comes from Base
from sqlalchemy.orm import relationship
from datetime import datetime # Keep for default value
from .base import Base # Import shared Base

class User(Base):
    __tablename__ = 'users'
    # id = Column(Integer, primary_key=True) # Inherited from Base

    username = Column(String, unique=True, nullable=False, index=True) # Added index
    password_hash = Column(String, nullable=False) # Use consistent name
    role = Column(String, nullable=False, default='basic') # Added default
    created_at = Column(DateTime, server_default=func.now()) # Use server_default
    last_login = Column(DateTime, default=datetime.utcnow) # Keep default for direct setting

    # Add relationship back to Person if Person.creator relationship exists
    created_people = relationship("Person", back_populates="creator")

    def to_dict(self):
        """Returns a dictionary representation of the user."""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            # DO NOT include password_hash
        }
