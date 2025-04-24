from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    nickname = Column(String)
    gender = Column(String)
    birth_date = Column(Date)
    death_date = Column(Date)
    place_of_birth = Column(String)
    place_of_death = Column(String)
    notes = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    creator = relationship("User", back_populates="created_people")
    attributes = relationship("PersonAttribute", back_populates="person")
    media = relationship("Media", back_populates="person")
    events = relationship("Event", back_populates="person")
    citations = relationship("Citation", back_populates="person")

    person1_relationships = relationship(
        "Relationship", foreign_keys="Relationship.person1_id", back_populates="person1"
    )
    person2_relationships = relationship(
        "Relationship", foreign_keys="Relationship.person2_id", back_populates="person2"
    )