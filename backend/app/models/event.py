from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'))
    event_type = Column(String)
    date = Column(Date)
    place = Column(String)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)