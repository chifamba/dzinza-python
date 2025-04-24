from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.db import Base


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("person.id"))
    media_type = Column(String)
    file_path = Column(String)
    title = Column(String)
    description = Column(String)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    person = relationship("Person", back_populates="media")