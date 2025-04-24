from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db import Base


class RelationshipAttribute(Base):
    __tablename__ = "relationship_attributes"

    id = Column(Integer, primary_key=True, index=True)
    relationship_id = Column(Integer, ForeignKey("relationships.id"))
    key = Column(String)
    value = Column(String)
    relationship = relationship("Relationship", back_populates="attributes")