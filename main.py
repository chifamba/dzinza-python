from src.user_management import UserManager  # Import the UserManager class
from src.user import User  # Import the User class
from src.family_tree import FamilyTree # Import the FamilyTree class
from src.person import Person # Import the Person class
from src.relationship import Relationship # Import the Relationship class


# Main function
def main():
    # Create an instance of UserManager
    user_manager = UserManager()

    # Create a new user with an id, email and password
    user_id = 1  # User ID must be an integer
    email = "test@example.com"  # Email must be a string
    password = "password123"  # Password must be a string
    user_manager.create_user(user_id, email, password)

    # Create an instance of FamilyTree
    family_tree = FamilyTree()

    # Create two persons
    person1 = Person(first_name="John", last_name="Doe", date_of_birth="1980-01-01", place_of_birth="New York", date_of_death=None, place_of_death=None, gender="Male", current_location="Los Angeles", biography="A short biography of John", privacy="public")
    person2 = Person(first_name="Jane", last_name="Doe", date_of_birth="2000-01-01", place_of_birth="Los Angeles", date_of_death=None, place_of_death=None, gender="Female", current_location="Los Angeles", biography="A short biography of Jane", privacy="public")



    # Add persons to the family tree
    family_tree.add_person(person1) # Add the first person to the FamilyTree without parent (root)
    family_tree.add_person(person2, person1) # Add the second person to the FamilyTree with the first one as parent
    
    # Create a parent-child relationship between the two persons
    parent_child_relationship = Relationship(person1, person2, "parent-child")
    
    # Add the relationship to the family tree
    family_tree.add_relationship(parent_child_relationship)
    
    # Print the relationships of person1 and person2
    print(f"Relationships of {person1.first_name}:")
    for relationship in person1.relationships:
        print(f"- {relationship.type} with {relationship.person2.first_name}")
    print(f"Relationships of {person2.first_name}:")
    for relationship in person2.relationships:
        print(f"- {relationship.type} with {relationship.person1.first_name}")

if __name__ == "__main__":
    main()
