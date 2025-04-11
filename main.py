from src.family_tree import FamilyTree
from src.person import Person
from src.user_management import UserManager
from src.user import User
import time
from datetime import datetime


# Create a FamilyTree object and a UserManager
family_tree = FamilyTree()
user_manager = UserManager()


# Test XML import and export
try:
    # Path to a sample XML file for import
    xml_file_path_import = "test.xml"
    # Import the XML file
    family_tree.import_xml(xml_file_path_import)
    # Display the tree after import
    print("Tree after XML import:")
    family_tree.display_tree()
except Exception as e:
    print(f"An error occurred during XML import: {e}")

# Now test XML export
try:
    # Path to export the XML file
    xml_file_path_export = "test_exported.xml"
    # Export the XML file
    family_tree.export_xml(xml_file_path_export)
    print(f"Tree exported to {xml_file_path_export}")
except Exception as e:
    print(f"An error occurred during XML export: {e}")

