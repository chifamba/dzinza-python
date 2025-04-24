from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    author = Column(String)
    publication_info = Column(String)
    url = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)