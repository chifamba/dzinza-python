from src.user_management import UserManager
from src.user import User
from src.family_tree import FamilyTree
from src.person import Person
import time
from datetime import datetime, timedelta

# Main function
def main():
    # Create an instance of UserManager to manage users
    user_manager = UserManager()

    # Create users with unique IDs, emails, and passwords
    user1_id = 1
    email1 = "test1@example.com"
    password_1 = "password123"
    user_manager.create_user(user1_id, email1, password_1)

    user2_id = 2
    email2 = "test2@example.com"
    password_2 = "password456"
    user_manager.create_user(user2_id, email2, password_2)

    user3_id = 3
    email3 = "test3@example.com"
    password_3 = "password789"
    user_manager.create_user(user3_id, email3, password_3)

    user4_id = 4
    email4 = "test4@example.com"
    password_4 = "password101"
    user_manager.create_user(user4_id, email4, password_4)

    # Get users using their IDs
    user1 = user_manager.get_user(user1_id)
    user2 = user_manager.get_user(user2_id)

    # Add trust points to the second user
    user_manager.add_trust_points(user2_id, 150)

    # Print user information before applying trust decay
    print("Users info before apply decay:")
    for user_id in user_manager.users:
        user = user_manager.users[user_id]
        print(f"User {user.user_id} info : {user.__dict__}")

    # Make user 2 inactive by setting last_login to 35 days ago
    user2.last_login = datetime.now() - timedelta(days=35)

    # Apply trust decay
    user_manager.apply_trust_decay()

    # Print user information after applying trust decay
    print("Users info after apply decay:")
    for user_id in user_manager.users:
        user = user_manager.users[user_id]
        print(f"User {user.user_id} info : {user.__dict__}")

    # Promote the first user to administrator
    user_manager.promote_to_administrator(user1_id)

    # Promote the second user to Family Historian
    user_manager.promote_to_family_historian(user2_id)

    # Promote the first user to a trusted user
    user_manager.promote_to_trusted(user1_id)

    # Create an instance of FamilyTree
    family_tree = FamilyTree()

    # Create persons
    person1 = Person(id=1, first_name="John", last_name="Doe", date_of_birth="1980-01-01", place_of_birth="New York", date_of_death=None, place_of_death=None, gender="Male", current_location="Los Angeles", biography="A short biography of John", privacy="public")
    person2 = Person(id=2, first_name="Jane", last_name="Doe", date_of_birth="2000-01-01", place_of_birth="Los Angeles", date_of_death=None, place_of_death=None, gender="Female", current_location="Los Angeles", biography="A short biography of Jane", privacy="public")
    person3 = Person(id=3, first_name="Peter", last_name="Doe", date_of_birth="2003-01-01", place_of_birth="Los Angeles", date_of_death=None, place_of_death=None, gender="Male", current_location="Los Angeles", biography="A short biography of Peter", privacy="public")

    # Add persons to the family tree using the new methods
    family_tree.add_person(person1)  # Add person1 as root
    family_tree.add_person_with_parents(person2, [person1.id]) # add person 2 and its parents
    family_tree.add_person_with_parents(person3, [person1.id]) # add person 3 and its parents

    # Link persons directly
    # Example: Link person1 and person2 as parent and child
    family_tree.link_persons(person1.id, person2.id, "child")
    # Example: Link person1 and person3 as parent and child
    family_tree.link_persons(person1.id, person3.id, "child")
    # Example: Link person3 and person2 as siblings
    family_tree.link_persons(person3.id, person2.id, "sibling")

    # Test get_parents method
    parents = person2.get_parents(family_tree)
    print(f"Parents of {person2.first_name}: {[parent.first_name for parent in parents]}")  # Should print John

    # Test get_children
    children = person1.get_children(family_tree)
    # Test get_children
    print(f"Children of {person1.first_name}: {[child.first_name for child in person1.get_children(family_tree)]}")  # Should print Jane and Peter

    # Test get_siblings method
    siblings = person2.get_siblings(family_tree)
    # Test get_siblings
    print(f"Siblings of {person2.first_name}: {[sibling.first_name for sibling in person2.get_siblings(family_tree)]}")  # Should print Peter
    # Test get_spouses method (no spouses yet)
    # Test get_spouses (no spouses yet)
    print(f"Spouses of {person1.first_name}: {[spouse.first_name for spouse in person1.get_spouses(family_tree)]}")  # Should print an empty list

if __name__ == "__main__":
    main()
