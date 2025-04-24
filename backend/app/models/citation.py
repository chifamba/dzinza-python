from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    person_id = Column(Integer, ForeignKey("people.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    citation_text = Column(String)
    page_number = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source = relationship("Source")
    person = relationship("Person")
    event = relationship("Event")