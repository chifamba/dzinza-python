from src.family_tree import FamilyTree
from src.person import Person
from src.user_management import UserManager
import time
from datetime import datetime


# Create a FamilyTree object
family_tree = FamilyTree() 

# Test validate_person_data method
try:
    # Try to add an incorrect person (empty name)
    incorrect_person = Person(
        user_id="incorrect_person",
        first_name="",
        last_name="Last",
        date_of_birth="1990-01-01",
        place_of_birth="Incorrect Place",
        family_tree=family_tree
    )
    family_tree.add_person(incorrect_person)
    print("This should not be printed - incorrect person added successfully")
except ValueError as e:
    print(f"Correctly caught ValueError when adding incorrect person: {e}")

# Try to add a correct person
try:
    correct_person = Person(
        user_id="correct_person",
        first_name="Correct",
        last_name="Last",
        date_of_birth="1990-01-01",
        place_of_birth="Correct Place",
        family_tree=family_tree
    )
    family_tree.add_person(correct_person)
    print("Correct person added successfully")
except ValueError as e:
    print(f"Error adding correct person: {e}")


# Test JSON import (with an incorrect person inside)
try:
    # Path to a sample JSON file for import
    json_file_path_import = "test_incorrect.json"
    # Import the JSON file
    family_tree.import_json(json_file_path_import)
except ValueError as e:
    print(f"Correctly caught ValueError during JSON import with incorrect data: {e}")
except Exception as e:
    print(f"An error occurred during JSON import: {e}")

    """if duplicates:
        print("Duplicates found:")
        for duplicate_group in duplicates:
            for person in duplicate_group:
                print(f"  Person ID: {person.user_id}, Name: {person.get_names()[0]['name']}")
    else:
        print("No duplicates found.")

    # Merge duplicates if any
    if duplicates:
        print("\nMerging duplicates...")
        for duplicate_group in duplicates:
            if len(duplicate_group) > 1:
                primary_person = duplicate_group[0]
                for person_to_merge in duplicate_group[1:]:
                    family_tree.merge_persons(primary_person, person_to_merge)
                print(
                    f"Merged duplicates into Person ID: {primary_person.user_id}, Name: {primary_person.get_names()[0]['name']}"
                )
        # Display the tree after merging
        print("\nTree after merging:")
        family_tree.display_tree()"""

try:
     # Path to a sample JSON file for import
    json_file_path_import = "test.json"
    # Import the JSON file
    family_tree.import_json(json_file_path_import)
    family_tree.display_tree()
except ValueError as e:
    print(f"Error in json correct file import: {e}")



