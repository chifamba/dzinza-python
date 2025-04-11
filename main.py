from src.user_management import UserManager  # Import the UserManager class
from src.user import User  # Import the User class
from src.family_tree import FamilyTree # Import the FamilyTree class
from src.person import Person # Import the Person class


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
    person1 = Person(first_name="John", last_name="Doe", date_of_birth="1980-01-01")
    person2 = Person(first_name="Jane", last_name="Doe", date_of_birth="2000-01-01")

    # Add persons to the family tree
    family_tree.add_person(person1) # Add the first person to the FamilyTree without parent (root)
    family_tree.add_person(person2, person1) # Add the second person to the FamilyTree with the first one as parent


if __name__ == '__main__':
    main()
