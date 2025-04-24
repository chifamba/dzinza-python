import datetime
from sqlalchemy.orm import sessionmaker
from app import engine, create_tables
from app.models.user import User
from app.models.person import Person
from app.models.person_attribute import PersonAttribute
from app.models.relationship import Relationship
from app.models.relationship_attribute import RelationshipAttribute
from app.models.media import Media
from app.models.event import Event
from app.models.source import Source
from app.models.citation import Citation

def create_initial_data():
    Session = sessionmaker(bind=engine)
    session = Session()

    create_tables()

    # Create users
    user1 = User(username="user1", password_hash="hash1", role="admin", created_at=datetime.datetime.now(), last_login=datetime.datetime.now())
    user2 = User(username="user2", password_hash="hash2", role="user", created_at=datetime.datetime.now(), last_login=datetime.datetime.now())
    session.add_all([user1, user2])
    session.commit()

    # Create people
    person1 = Person(first_name="John", last_name="Doe", gender="male", birth_date=datetime.date(1900, 1, 1), death_date=datetime.date(1980, 12, 31), created_by=user1.id, created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    person2 = Person(first_name="Jane", last_name="Doe", gender="female", birth_date=datetime.date(1905, 2, 15), death_date=datetime.date(1985, 10, 20), created_by=user1.id, created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    person3 = Person(first_name="Peter", last_name="Smith", gender="male", birth_date=datetime.date(1902, 3, 10), death_date=datetime.date(1975, 5, 5), created_by=user1.id, created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    person4 = Person(first_name="Alice", last_name="Smith", gender="female", birth_date=datetime.date(1930, 4, 22), created_by=user1.id, created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    person5 = Person(first_name="Bob", last_name="Smith", gender="male", birth_date=datetime.date(1935, 6, 18), created_by=user1.id, created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    person6 = Person(first_name="Mike", last_name="Doe", gender="male", birth_date=datetime.date(1932, 8, 1), death_date=datetime.date(2000, 9, 12), created_by=user1.id, created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    session.add_all([person1, person2, person3, person4, person5, person6])
    session.commit()

    #Create person attributes
    person_attribute1 = PersonAttribute(person_id=person1.id, key="test", value="test")
    session.add_all([person_attribute1])
    session.commit()

    # Create relationships
    relationship1 = Relationship(person1_id=person2.id, person2_id=person3.id, rel_type="married", created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    relationship2 = Relationship(person1_id=person4.id, person2_id=person2.id, rel_type="parent", created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    relationship3 = Relationship(person1_id=person5.id, person2_id=person2.id, rel_type="parent", created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    relationship4 = Relationship(person1_id=person6.id, person2_id=person1.id, rel_type="parent", created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())

    session.add_all([relationship1, relationship2, relationship3, relationship4])
    session.commit()

    # Create relationship attributes
    relationship_attribute1 = RelationshipAttribute(relationship_id=relationship1.id, key="wedding_date", value="1925-05-10")
    session.add_all([relationship_attribute1])
    session.commit()


    # Create sources
    source1 = Source(title="Census 1910", author="Government", created_at=datetime.datetime.now())
    source2 = Source(title="Birth Certificate", author="Hospital", created_at=datetime.datetime.now())
    session.add_all([source1, source2])
    session.commit()
    
    # Create citations
    citation1 = Citation(source_id=source1.id, person_id=person1.id, citation_text="Listed in household", page_number="12", created_at=datetime.datetime.now())
    citation2 = Citation(source_id=source2.id, person_id=person2.id, citation_text="Birth certificate", page_number="1", created_at=datetime.datetime.now())
    citation3 = Citation(source_id=source2.id, person_id=person3.id, citation_text="Birth certificate", page_number="1", created_at=datetime.datetime.now())
    session.add_all([citation1, citation2,citation3])
    session.commit()
    
    # Create events
    event1 = Event(person_id=person1.id, event_type="birth", date=datetime.date(1900, 1, 1), place="New York", created_at=datetime.datetime.now())
    event2 = Event(person_id=person2.id, event_type="birth", date=datetime.date(1905, 2, 15), place="Boston", created_at=datetime.datetime.now())
    event3 = Event(person_id=person3.id, event_type="birth", date=datetime.date(1902, 3, 10), place="Chicago", created_at=datetime.datetime.now())
    event4 = Event(person_id=person4.id, event_type="birth", date=datetime.date(1930, 4, 22), place="Los Angeles", created_at=datetime.datetime.now())
    event5 = Event(person_id=person5.id, event_type="birth", date=datetime.date(1935, 6, 18), place="Houston", created_at=datetime.datetime.now())
    event6 = Event(person_id=person6.id, event_type="birth", date=datetime.date(1932, 8, 1), place="San Francisco", created_at=datetime.datetime.now())
    
    session.add_all([event1,event2,event3,event4,event5,event6])
    session.commit()


    #Create media
    media1 = Media(person_id=person1.id, media_type="image", file_path="person1.jpg", title="Person 1 Image", description="Image of person 1", uploaded_at=datetime.datetime.now())
    media2 = Media(person_id=person2.id, media_type="image", file_path="person2.jpg", title="Person 2 Image", description="Image of person 2", uploaded_at=datetime.datetime.now())
    session.add_all([media1, media2])
    session.commit()


def main():
    create_initial_data()

if __name__ == "__main__":
    main()