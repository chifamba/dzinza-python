from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship
from src.user_management import UserManager
from src.user_interface import UserProfileView, FamilyGroupView, PersonDetailView, RelationshipView



# Create a FamilyTree object
family_tree = FamilyTree()

# Test validate_person_data method with incorrect data
try:
    # Create an incorrect person (empty name)
    incorrect_person = Person(
        person_id="incorrect_person",
        first_name="",
        last_name="Last",
        date_of_birth="1990-01-01",
        place_of_birth="Incorrect Place",
    )

    # Try to add the incorrect person to the tree, must raise a ValueError
    family_tree.add_person(incorrect_person)
    print("This should not be printed - incorrect person added successfully")
except ValueError as e:
    print(f"Correctly caught ValueError when adding incorrect person: {e}")


# Test validate_person_data method with correct data
try:
    # Create a correct person
    correct_person = Person(
        person_id="correct_person",
        first_name="Correct",
        last_name="Last",
        date_of_birth="1990-01-01",
        place_of_birth="Correct Place",
    )
    # Add the correct person to the tree, must work correctly
    family_tree.add_person(correct_person)
    print("Correct person added successfully")
except ValueError as e:
    print(f"Error adding correct person: {e}")


# Test JSON import with an incorrect person inside the data, must raise a ValueError
try:
    # Path to a sample JSON file with incorrect data
    json_file_path_import_incorrect = "test_incorrect.json"
    # Import the JSON file (should raise a ValueError)
    family_tree.import_json(json_file_path_import_incorrect)
except ValueError as e:
    print(f"Correctly caught ValueError during JSON import with incorrect data: {e}")
except Exception as e:
    print(f"An error occurred during JSON import: {e}")


# Test JSON import with correct data, must work correctly
try:
    # Path to a sample JSON file with correct data
    json_file_path_import_correct = "test.json"
    # Import the JSON file (should work correctly)
    family_tree.import_json(json_file_path_import_correct)
    # Display the tree after importing
    family_tree.display_tree()
except Exception as e:
    print(f"An error occurred during JSON import: {e}")


# Create persons
person1 = Person("person1", "Name1", "LastName1", "1970-01-01", "Place1")
person2 = Person("person2", "Name2", "LastName2", "1975-05-10", "Place2")
person3 = Person("person3", "Name3", "LastName3", "1995-11-15", "Place3")
person4 = Person("person4", "Name4", "LastName4", "1998-03-20", "Place4")

# Create and add persons to the tree
family_tree.add_person(person1)
family_tree.add_person(person2)
family_tree.add_person(person3)
family_tree.add_person(person4)

# Create and add relationships to the tree
relationship1 = Relationship(person1.person_id, person2.person_id, "spouse")
relationship2 = Relationship(person3.person_id, person1.person_id, "child")
relationship3 = Relationship(person4.person_id, person1.person_id, "child")
family_tree.link_persons(relationship1)
family_tree.link_persons(relationship2)
family_tree.link_persons(relationship3)


# Test relationship consistency, must work correctly
print("\nTesting relationship consistency...")
try:
    # Check the consistency of the relationships of person1, must not raise an exception
    family_tree.check_relationship_consistency(person1.person_id)
    print("Relationship consistency check passed.")
except ValueError as e:
    print(f"Relationship consistency check failed: {e}")

# Test adding an incorrect relationship, must raise a ValueError
print("\nTesting adding an incorrect relationship...")
try:
    # Create an incorrect relationship (person3 as spouse of person1, which already has a spouse)
    incorrect_relationship = Relationship(person3.person_id, person1.person_id, "spouse")
    # Try to add the incorrect relationship to the tree
    family_tree.link_persons(incorrect_relationship)
    print("Incorrect relationship added successfully (this should not happen).")
except ValueError as e:
    print(f"Correctly caught ValueError when adding an incorrect relationship: {e}")


# Check the consistency of all the tree, must work correctly
print(f"\nCheck the consistency of the entire tree")
family_tree.check_all_relationship_consistency()


# Display the tree, must show the tree in hierarchical view
print(f"\nDisplay the entire tree")
family_tree.display_tree()


# Generate and print the reports
print("\nFamily Tree Report:")
family_tree_report = family_tree.generate_family_tree_report()
print(family_tree_report)
print("\nPerson Summary Report for person1:")
person_summary = family_tree.generate_person_summary_report(person1.person_id)
print(person_summary)
print("\nCustom Report for person1 and person2 (name and date of birth):")
custom_report = family_tree.generate_custom_report([person1.person_id, person2.person_id], ["names", "date_of_birth"])
print(custom_report)

# Test the new get_person_info method of the Person class
print("\nTesting get_person_info method...")
print(f"\nPerson1 info: {person1.get_person_info()}")
print(f"\nPerson2 info: {person2.get_person_info()}")
print(f"\nPerson3 info: {person3.get_person_info()}")
print(f"\nPerson4 info: {person4.get_person_info()}")


# Create a UserManager object
user_manager = UserManager()

# Create a user
user = user_manager.create_user("user1", "test@test.com", "password")

# Create a UserProfileView object and display the user's profile
user_profile_view = UserProfileView(user)
user_profile_view.display_profile()


# Test FamilyGroupView class
print("\nTesting FamilyGroupView...")
try:
    # Create a FamilyGroupView object
    family_group_view = FamilyGroupView(family_tree)
    # Display a family group
    family_group_view.display_family_group([person1.person_id, person2.person_id, person3.person_id])
except ValueError as e:
    print(f"Error displaying family group: {e}")


# Create a PersonDetailView object and display the details of person1
print("\nTesting PersonDetailView...")
person_detail_view = PersonDetailView(person1)
person_detail_view.display_person_details()


# Create a RelationshipView object and display the details of relationship1
print("\nTesting RelationshipView...")
relationship_view = RelationshipView(relationship1)
relationship_view.display_relationship()


# Test search_person method
print("\nTesting search_person method...")

# Search for persons with "Name" in their names
print("\nSearch for persons with 'Name' in their names:")
results = family_tree.search_person("Name", ["names"])
for person in results:
    print(person)

# Search for persons with "1975" in their date_of_birth
print("\nSearch for persons with '1975' in their date_of_birth:")
results = family_tree.search_person("1975", ["date_of_birth"])
for person in results:
    print(person)

# Search for persons with "Place4" in their place_of_birth
print("\nSearch for persons with 'Place4' in their place_of_birth:")
results = family_tree.search_person("Place4", ["place_of_birth"])
for person in results:
    print(person)

