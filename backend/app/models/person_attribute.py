from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class PersonAttribute(Base):
    __tablename__ = "person_attributes"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("people.id"))
    key = Column(String)
    value = Column(String)

    person = relationship("Person", back_populates="attributes")