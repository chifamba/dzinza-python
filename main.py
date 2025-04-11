from src.user_management import UserManager  # Import the UserManager class
from src.user import User  # Import the User class
from src.family_tree import FamilyTree # Import the FamilyTree class
from src.person import Person # Import the Person class


# Main function
def main():
    # Create an instance of UserManager
    user_manager = UserManager()
    
    # Create a new users with an id, email and password
    user1_id = 1  # User ID must be an integer
    email1 = "test1@example.com"  # Email must be a string
    password_1 = "password123"  # Password must be a string
    user_manager.create_user(user1_id, email1, password_1)
    
    user2_id = 2  # User ID must be an integer
    email2 = "test2@example.com"  # Email must be a string
    password_2 = "password456"  # Password must be a string
    user_manager.create_user(user2_id, email2, password_2)
    
    #Get the first user
    user1 = user_manager.get_user(user1_id)
    
    # Promote the first user to a trusted user
    user_manager.promote_to_trusted(user1_id)

    # Create an instance of FamilyTree  
    family_tree = FamilyTree()

    # Create two persons with ids
    person1 = Person(id=1, first_name="John", last_name="Doe", date_of_birth="1980-01-01", place_of_birth="New York", date_of_death=None, place_of_death=None, gender="Male", current_location="Los Angeles", biography="A short biography of John", privacy="public")
    person2 = Person(id=2, first_name="Jane", last_name="Doe", date_of_birth="2000-01-01", place_of_birth="Los Angeles", date_of_death=None, place_of_death=None, gender="Female", current_location="Los Angeles", biography="A short biography of Jane", privacy="public")



    # Add persons to the family tree using the ids
    family_tree.add_person(person1)  # Add the first person to the FamilyTree without parent (root)
    family_tree.add_person(person2, person1)  # Add the second person to the FamilyTree with the first one as parent

    # Add relationships between the created persons using the methods of the Person class
    person1.add_child(person2.id)  # Add person2 as a child of person1
    person2.add_parent(person1.id)  # Add person1 as a parent of person2
    
    #Print the relationships of person 1 and person2
    print(f"Relationships of {person1.first_name}: {person1.relationships}")
    print(f"Relationships of {person2.first_name}: {person2.relationships}")

if __name__ == "__main__":
    main()
