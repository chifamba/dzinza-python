# backend/app/db_init.py
import datetime
import logging
from sqlalchemy.orm import sessionmaker, Session as DbSession # Rename to avoid conflict

# Assuming engine is created in app.py and passed or imported
# For standalone script, you might need to create engine here
# from .app import db_engine # Example if engine is in app.py
# If running standalone, create engine directly:
# from sqlalchemy import create_engine
# DATABASE_URL = "postgresql://user:password@host:port/database" # Get from env
# db_engine = create_engine(DATABASE_URL)

# Import models (adjust paths if needed)
try:
    from .models import Base # Assuming Base is defined in models/__init__.py or models/base.py
    from .models.user import User
    from .models.person import Person
    from .models.person_attribute import PersonAttribute
    from .models.relationship import Relationship as RelationshipModel # Alias
    from .models.relationship_attribute import RelationshipAttribute
    from .models.media import Media
    from .models.event import Event
    from .models.source import Source
    from .models.citation import Citation
except ImportError as e:
    logging.critical(f"Failed to import models in db_init: {e}")
    raise

def create_tables(engine):
    """Creates all tables defined in Base metadata."""
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables created successfully (if they didn't exist).")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}", exc_info=True)
        raise

def populate_db(db: DbSession):
    """Populates the database with initial sample data if empty."""
    try:
        # Check if data already exists (e.g., check for any user)
        user_count = db.query(User).count()
        if user_count > 0:
            logging.info("Database already contains data. Skipping initial population.")
            return

        logging.info("Populating database with initial sample data...")

        # Create users
        # Note: Passwords should be hashed using UserManagement or encryption module
        # This example uses placeholder hashes for simplicity in db_init
        user1 = User(username="user1", password_hash_b64="placeholder_hash1", role="admin")
        user2 = User(username="user2", password_hash_b64="placeholder_hash2", role="basic")
        db.add_all([user1, user2])
        db.flush() # Flush to get user IDs if needed immediately

        # Create people (Ensure created_by uses the flushed user IDs)
        person1 = Person(first_name="John", last_name="Doe", gender="Male",
                         birth_date=date(1900, 1, 1), death_date=date(1980, 12, 31),
                         created_by=user1.user_id) # Use actual ID
        person2 = Person(first_name="Jane", last_name="Doe", gender="Female",
                         birth_date=date(1905, 2, 15), death_date=date(1985, 10, 20),
                         created_by=user1.user_id)
        person3 = Person(first_name="Peter", last_name="Smith", gender="Male",
                         birth_date=date(1902, 3, 10), death_date=date(1975, 5, 5),
                         created_by=user1.user_id)
        person4 = Person(first_name="Alice", last_name="Smith", gender="Female",
                         birth_date=date(1930, 4, 22), created_by=user1.user_id)
        person5 = Person(first_name="Bob", last_name="Smith", gender="Male",
                         birth_date=date(1935, 6, 18), created_by=user1.user_id)
        person6 = Person(first_name="Mike", last_name="Doe", gender="Male",
                         birth_date=date(1932, 8, 1), death_date=date(2000, 9, 12),
                         created_by=user1.user_id)
        db.add_all([person1, person2, person3, person4, person5, person6])
        db.flush() # Flush to get person IDs

        # Create person attributes
        person_attribute1 = PersonAttribute(person_id=person1.person_id, key="Occupation", value="Farmer")
        db.add(person_attribute1)
        db.flush()

        # Create relationships (Use RelationshipModel alias)
        relationship1 = RelationshipModel(person1_id=person2.person_id, person2_id=person3.person_id, rel_type="spouse")
        relationship2 = RelationshipModel(person1_id=person2.person_id, person2_id=person4.person_id, rel_type="parent") # Jane is parent of Alice
        relationship3 = RelationshipModel(person1_id=person2.person_id, person2_id=person5.person_id, rel_type="parent") # Jane is parent of Bob
        relationship4 = RelationshipModel(person1_id=person1.person_id, person2_id=person6.person_id, rel_type="parent") # John is parent of Mike
        db.add_all([relationship1, relationship2, relationship3, relationship4])
        db.flush() # Flush to get relationship IDs

        # Create relationship attributes
        relationship_attribute1 = RelationshipAttribute(relationship_id=relationship1.rel_id, key="wedding_date", value="1925-05-10")
        db.add(relationship_attribute1)
        db.flush()

        # Create sources
        source1 = Source(title="Census 1910", author="Government")
        source2 = Source(title="Birth Certificate", author="Hospital")
        db.add_all([source1, source2])
        db.flush() # Flush to get source IDs

        # Create events
        event1 = Event(person_id=person1.person_id, event_type="birth", date=date(1900, 1, 1), place="New York")
        event2 = Event(person_id=person2.person_id, event_type="birth", date=date(1905, 2, 15), place="Boston")
        # ... add other events ...
        db.add_all([event1, event2]) # Add more events here
        db.flush() # Flush to get event IDs if needed for citations

        # Create citations (Ensure IDs from flushed objects are used)
        citation1 = Citation(source_id=source1.id, person_id=person1.person_id, citation_text="Listed in household", page_number="12")
        citation2 = Citation(source_id=source2.id, person_id=person2.person_id, citation_text="Birth certificate", page_number="1")
        # ... add other citations ...
        db.add_all([citation1, citation2]) # Add more citations here
        db.flush()

        # Create media
        media1 = Media(person_id=person1.person_id, media_type="image", file_path="person1.jpg", title="Person 1 Image")
        media2 = Media(person_id=person2.person_id, media_type="image", file_path="person2.jpg", title="Person 2 Image")
        db.add_all([media1, media2])
        db.flush()

        db.commit() # Commit all changes
        logging.info("Initial sample data populated successfully.")

    except IntegrityError as ie:
        db.rollback()
        logging.warning(f"Database integrity error during population (maybe data exists?): {ie}")
    except Exception as e:
        db.rollback()
        logging.error(f"Error populating database: {e}", exc_info=True)
        raise

# Example standalone execution (optional)
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     if db_engine: # Check if engine was created
#         create_tables(db_engine)
#         SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
#         db = SessionLocal()
#         try:
#             populate_db(db)
#         finally:
#             db.close()
#     else:
#         logging.critical("Cannot run db_init standalone without a configured db_engine.")
