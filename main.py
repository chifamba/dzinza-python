from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship
from src.user_management import UserManager

from src.user_interface import (
    FamilyGroupView,
    PersonDetailView,
    RelationshipView,
    User,
)

print("\nTesting FamilyTree...")



# Create a family tree
family_tree = FamilyTree()

print(f"\n--------------------------------------------------------")
print("\nTesting encryption in export and import json...")
# Path to a sample JSON file with correct data
json_file_path_import = "test.json"
# Import the JSON file (should work correctly)
family_tree.import_json(json_file_path_import, "system")
print("Json file imported successfully")
# Export the tree in another json file
json_file_path_export = "test_exported.json"
family_tree.export_json(
    json_file_path_export
)
print(f"The json was exported in {json_file_path_export}, check if it is encrypted.")


# Test JSON import with an incorrect person inside the data, must raise a ValueError
try:
    # Path to a sample JSON file with incorrect data
    json_file_path_import_incorrect = "test_incorrect.json"
    # Import the JSON file (should raise a ValueError)
    family_tree_incorrect = FamilyTree()
    family_tree_incorrect.import_json(json_file_path_import_incorrect)
except ValueError as e: 


    print(f"Correctly caught ValueError during JSON import with incorrect data: {e}")
except Exception as e:
    print(f"An error occurred during JSON import: {e}")


# Test JSON import again with the exported json, must work correctly
try:
    #Create a new tree
    family_tree_2 = FamilyTree()
    family_tree_2.import_json(json_file_path_export,"system")
    print("Json file imported successfully again")
    # Display the tree after importing again
    family_tree_2.display_tree()
except Exception as e:
    print(f"An error occurred during JSON import again: {e}")


print(f"\n--------------------------------------------------------")

# Create the persons
# Create person1 with the encryption key
person1 = Person("person1", "Name1", "LastName1", "1970-01-01", "Place1")
# Create other persons
person3 = Person("person3", "Name3", "LastName3", "1995-11-15", "Place3")
person4 = Person("person4", "Name4", "LastName4", "1998-03-20", "Place4")

# Create and add persons to the tree
family_tree.add_person(person1, "system")
family_tree.add_person(person3, "system")

# Create person2 (is in the json file)
# Create and add relationships to the tree
relationship1 = Relationship(
    person1.person_id, person2.person_id, "spouse"
)  # person1 is the spouse of person2
relationship2 = Relationship(
    person3.person_id, person1.person_id, "child")  # person3 is a child of person1
relationship3 = Relationship(person4.person_id, person1.person_id, "child")
family_tree.link_persons(relationship1)
family_tree.link_persons(relationship2)
family_tree.link_persons(relationship3)
# Check if the data was encrypted in person1

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
print(f"\nCheck the consistency of the entire tree...")
family_tree.check_all_relationship_consistency()


# Display the tree, must show the tree in hierarchical view
print(f"\nDisplay the entire tree...")
family_tree.display_tree()

print(f"\n--------------------------------------------------------")

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

print(f"\n--------------------------------------------------------")


# Test the privacy settings of the Person class
print("\nTesting privacy settings for person1...")
# Set privacy settings for person1
person1.set_privacy_setting("names", "public")  # anyone can see it
person1.set_privacy_setting("date_of_birth", "private")  # only admin
person1.set_privacy_setting("place_of_birth", "family_only")  # only family
person1.set_privacy_setting("date_of_death", "godparents_only")  # only godparents
person1.set_privacy_setting("place_of_death", "foster_only")  # only foster
person1.set_privacy_setting(
    "place_of_birth", "guardians_only")  # only guardians
# Print the privacy settings
print(f"Privacy setting for names: {person1.get_privacy_setting('names')}")
print(f"Privacy setting for date_of_birth: {person1.get_privacy_setting('date_of_birth')}")
print(f"Privacy setting for place_of_birth: {person1.get_privacy_setting('place_of_birth')}")
print(f"Privacy setting for biography: {person1.get_privacy_setting('biography')}")

print(f"\n--------------------------------------------------------")
# Test the new get_person_info method of the Person class
print("\nTesting get_person_info method...")
print(f"\nPerson1 info: {person1.get_person_info()}")
print(f"\nPerson2 info: {person2.get_person_info()}")
print(f"\nPerson3 info: {person3.get_person_info()}")
print(f"\nPerson4 info: {person4.get_person_info()}")


# Test the UserManager
print(f"\n--------------------------------------------------------")
print("\nTesting the UserManager")

# Create a UserManager object with the audit log object
user_manager = UserManager()

# Create the users with different access levels
guest_user: User = user_manager.create_user(
    "guest", "guest@example.com", "password", access_level="guest"
)
normal_user: User = user_manager.create_user(
    "normal_user", "normal@example.com", "password", access_level="user"
)
admin_user: User = user_manager.create_user(
    "admin", "admin@example.com", "password", access_level="admin"
)






# Add person3 as a godparent of person1, must exist in the tree
person1.add_godparent(person3.person_id)

# Add person4 as a foster relationship of person1, must exist in the tree
person1.add_foster_relationship(person4.person_id)
person2 = family_tree.get_person("person2")


print(f"\n--------------------------------------------------------")




# Get and print log entries for system
print("\nLog entries for system:")
system_logs = user_manager.audit_log.get_log_entries(user_id="system")
for log in system_logs:
    print(log)

# Get and print log entries for user creation
print("\nLog entries for user created:")
create_logs = user_manager.audit_log.get_log_entries(event_type="user_created")
for log in create_logs:
    print(log)


# Add a relationship
relationship4 = Relationship(person5.person_id, person3.person_id, "parent")
family_tree.link_persons(relationship4, admin_user.user_id)


# Import the persons from the test.json (there is person2)
family_tree.import_json("test.json", user_id=guest_user.user_id)



# Test FamilyGroupView class, person2 is added when the json is imported
print(f"\n--------------------------------------------------------")
print("\nTesting FamilyGroupView...")
try:
    # Create a FamilyGroupView object
    family_group_view = FamilyGroupView(family_tree)
    # Display a family group

    # Add person2 as a spouse of person1
    relationship1 = Relationship(person1.person_id, person2.person_id, "spouse")
    family_tree.link_persons(relationship1)
    family_group_view.display_family_group([person1.person_id, person2.person_id, person3.person_id])
except ValueError as e:
    print(f"Error displaying family group: {e}")



print(f"\n--------------------------------------------------------")
# Create a PersonDetailView object and display the details of person1
print(f"\n--------------------------------------------------------")
print("\nTesting PersonDetailView...")
person_detail_view = PersonDetailView(person1)
person_detail_view.display_person_details()

# Create a RelationshipView object and display the details of relationship1
print(f"\nTesting RelationshipView...")
relationship_view = RelationshipView(relationship2)
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


