from src.family_tree import FamilyTree
from src.person import Person
from src.user_management import UserManager
from src.user import User
import time
from datetime import datetime
import json

# Create a FamilyTree object
family_tree = FamilyTree()

# Example Usage

try:
    # Path to a sample JSON file for import
    json_file_path_import = "test.json"
    # Import the JSON file
    family_tree.import_json(json_file_path_import)
    # Display the tree after import
    print("Tree after JSON import:")
    family_tree.display_tree()
except Exception as e:
    print(f"An error occurred during JSON import: {e}")

# Now, test the export_json method
try:
    # Path to export the JSON file
    json_file_path_export = "test_exported.json"
    # Export the JSON file
    family_tree.export_json(json_file_path_export)
    print(f"Tree exported to {json_file_path_export}")
except Exception as e:
    print(f"An error occurred during JSON export: {e}")


# # Test gedcom import and export
# try:
#     # Import the GEDCOM file
#     family_tree.import_gedcom("test.ged")
#     family_tree.export_gedcom("test_exported.ged")
# except Exception as e:
#     print(f"An error occurred: {e}")

