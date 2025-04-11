from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship

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
    # Try to add the incorrect person to the tree
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
    # Add the correct person to the tree
    family_tree.add_person(correct_person) 
    print("Correct person added successfully")
except ValueError as e:
    print(f"Error adding correct person: {e}")

# Test JSON import with an incorrect person inside the data
try:
    # Path to a sample JSON file with incorrect data
    json_file_path_import_incorrect = "test_incorrect.json"
    # Import the JSON file (should raise a ValueError)
    family_tree.import_json(json_file_path_import_incorrect)
except ValueError as e:
    print(f"Correctly caught ValueError during JSON import with incorrect data: {e}")
except Exception as e:
    print(f"An error occurred during JSON import: {e}")

# Test JSON import with correct data
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

# Test relationship consistency
print("\nTesting relationship consistency...")
try:
    # Check the consistency of the relationships of person1
    family_tree.check_relationship_consistency(person1.person_id)
    print("Relationship consistency check passed.")
except ValueError as e:
    print(f"Relationship consistency check failed: {e}")

# Test adding an incorrect relationship
print("\nTesting adding an incorrect relationship...")
try:
    # Create an incorrect relationship (person3 as spouse of person1, which already has a spouse)
    incorrect_relationship = Relationship(person3.person_id, person1.person_id, "spouse")
    # Try to add the incorrect relationship to the tree
    family_tree.link_persons(incorrect_relationship)
    print("Incorrect relationship added successfully (this should not happen).")
except ValueError as e:
    print(f"Correctly caught ValueError when adding an incorrect relationship: {e}")
# Check the consistency of all the tree
print(f"\nCheck the consistency of the entire tree")
family_tree.check_all_relationship_consistency()
# Display the tree
print(f"\nDisplay the entire tree")
family_tree.display_tree()
