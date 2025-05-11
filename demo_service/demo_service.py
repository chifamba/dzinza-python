import os
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import Base, User, Tree, Person, Relationship, RelationshipTypeEnum

# Database connection setup
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@dbservice:5432/dzinza")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

# Helper functions to generate random data
def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def create_demo_data():
    try:
        # Create demo users
        for i in range(5):
            user = User(
                id=uuid.uuid4(),
                username=f"demo_user_{i}",
                email=f"demo_user_{i}@example.com",
                password_hash="demo_hash",
                role="user",
                is_active=True,
                email_verified=True,
                created_at=datetime.utcnow()
            )
            session.add(user)

        # Create demo trees and people
        for i in range(3):
            tree = Tree(
                id=uuid.uuid4(),
                name=f"Demo Family Tree {i}",
                description="A demo family tree.",
                created_by=random.choice(session.query(User).all()).id,
                is_public=True,
                created_at=datetime.utcnow()
            )
            session.add(tree)

            # Add people to the tree
            for j in range(10):
                person = Person(
                    id=uuid.uuid4(),
                    tree_id=tree.id,
                    first_name=f"Person_{j}",
                    last_name=f"Last_{j}",
                    birth_date=random_date(datetime(1950, 1, 1), datetime(2000, 1, 1)),
                    is_living=random.choice([True, False]),
                    created_by=tree.created_by,
                    created_at=datetime.utcnow()
                )
                session.add(person)

            # Add relationships
            people = session.query(Person).filter(Person.tree_id == tree.id).all()
            for k in range(len(people) - 1):
                relationship = Relationship(
                    id=uuid.uuid4(),
                    tree_id=tree.id,
                    person1_id=people[k].id,
                    person2_id=people[k + 1].id,
                    relationship_type=random.choice(list(RelationshipTypeEnum)),
                    created_by=tree.created_by,
                    created_at=datetime.utcnow()
                )
                session.add(relationship)

        session.commit()
        print("Demo data created successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error creating demo data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    if os.getenv("ENABLE_DEMO_MODE", "true").lower() == "true":
        create_demo_data()
