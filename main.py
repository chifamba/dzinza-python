from src.family_tree import FamilyTree
from src.person import Person
from src.user_management import UserManager
import time
from datetime import datetime


# Create a FamilyTree object
family_tree = FamilyTree()

# Test JSON import and find_duplicates and merge_persons
try:
    # Path to a sample JSON file for import
    json_file_path_import = "test.json"
    # Import the JSON file
    family_tree.import_json(json_file_path_import)

    # Display the tree after import
    print("Tree after JSON import:")
    family_tree.display_tree()

    # Find duplicates in the tree
    print("\nFinding duplicates...")
    duplicates = family_tree.find_duplicates()
    if duplicates:
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
        family_tree.display_tree()

    else:
        print("No merge needed.")
except Exception as e:
    print(f"An error occurred during JSON import, find duplicates or merge: {e}")



# Test XML import and export (this part is not necessary anymore, because the persons are in the tree)
try:
    # Path to a sample XML file for import
    xml_file_path_import = "test.xml"
    # Import the XML file
    family_tree.import_xml(xml_file_path_import)
except Exception as e:
    print(f"An error occurred during XML import: {e}")

try:
    # Path to export the XML file
    xml_file_path_export = "test_exported.xml"
    # Export the XML file
    family_tree.export_xml(xml_file_path_export)
    print(f"Tree exported to {xml_file_path_export}")

except Exception as e:
    print(f"An error occurred during XML export: {e}")



