from src.family_tree import FamilyTree
from src.person import Person
from src.encryption import DataEncryptor
from src.relationship import Relationship
from src.user_management import UserManager
from src.user_interface import UserProfileView, FamilyGroupView, PersonDetailView, RelationshipView, User


print(f"\n--------------------------------------------------------")
print("\nTesting FamilyTree...")

# Create a DataEncryptor object
data_encryptor = DataEncryptor()

# Create the encryption key
encryption_key = "mysecretkey"

#Create a family tree

family_tree = FamilyTree(encryption_key = encryption_key)

print(f"\n--------------------------------------------------------")
print("\nTesting encryption in export and import json...")
# Path to a sample JSON file with correct data
json_file_path_import = "test.json"
# Import the JSON file (should work correctly)
family_tree.import_json(json_file_path_import)
print("Json file imported successfully")
# Export the tree in another json file
json_file_path_export = "test_exported.json"
family_tree.export_json(json_file_path_export)
print(f"The json was exported in {json_file_path_export}, check if it is encrypted.")


# Test JSON import with an incorrect person inside the data, must raise a ValueError
try:
    # Path to a sample JSON file with incorrect data
    json_file_path_import_incorrect = "test_incorrect.json"
    # Import the JSON file (should raise a ValueError)
    family_tree_incorrect = FamilyTree(encryption_key=encryption_key)
    family_tree_incorrect.import_json(json_file_path_import_incorrect)
except ValueError as e:
    print(f"Correctly caught ValueError during JSON import with incorrect data: {e}")
except Exception as e:
    print(f"An error occurred during JSON import: {e}")


# Test JSON import again with the exported json, must work correctly
try:
    #Create a new tree
    family_tree_2 = FamilyTree(encryption_key = encryption_key)
    family_tree_2.import_json(json_file_path_export)
    print("Json file imported successfully again")
    # Display the tree after importing
    family_tree_2.display_tree()
except Exception as e:
    print(f"An error occurred during JSON import again: {e}")


print(f"\n--------------------------------------------------------")
print(f"\n--------------------------------------------------------")
print(f"\n--------------------------------------------------------")

# Test encryption
print(f"\nTesting encryption...")

#Create a DataEncryptor object

# Create the persons
# Create person1 with the encryption key
person1 = Person("person1", "Name1", "LastName1", "1970-01-01", "Place1", encryption_key=encryption_key)
# Add some data to person1 that will be encrypted
person1.add_biography("This is my biography")
person1.add_medical_history("This is my medical history")
person1.add_physical_characteristic("This is my physical characteristics")
person1.add_dna_haplogroup("This is my dna haplogroup")
person3 = Person("person3", "Name3", "LastName3", "1995-11-15", "Place3")
person4 = Person("person4", "Name4", "LastName4", "1998-03-20", "Place4")

# Create and add persons to the tree
family_tree.add_person(person1)
family_tree.add_person(person3)

# Create person2 (is in the json file)
# Create and add relationships to the tree
relationship1 = Relationship(person1.person_id, person2.person_id, "spouse")  # person1 is the spouse of person2
relationship2 = Relationship(person3.person_id, person1.person_id, "child")  # person3 is a child of person1
relationship3 = Relationship(person4.person_id, person1.person_id, "child")
family_tree.link_persons(relationship1)
family_tree.link_persons(relationship2)
family_tree.link_persons(relationship3)
# Check if the data was encrypted in person1

print(f"Is the biography encrypted? {type(person1.biography) != str}")

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
person1.set_privacy_setting("names", "public")
person1.set_privacy_setting("date_of_birth", "private")
person1.set_privacy_setting("place_of_birth", "family_only")
person1.set_privacy_setting("date_of_death", "godparents_only")
person1.set_privacy_setting("place_of_death", "foster_only")
person1.set_privacy_setting("biography", "guardians_only")  

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


# Create a UserManager object
user_manager = UserManager()

# Create the users with different access levels, user2, user3, user4 are created in the json import
guest_user:User = user_manager.create_user("guest", "guest@example.com", "password", access_level="guest")
normal_user:User = user_manager.create_user("normal_user", "normal@example.com", "password", access_level = "user")
admin_user:User = user_manager.create_user("admin", "admin@example.com", "password", access_level="admin")

# Add person2 as a spouse of person1, (is imported in the json file)
relationship1 = Relationship(person1.person_id, person2.person_id, "spouse")
family_tree.link_persons(relationship1)

# Add person3 as a godparent of person1, must exist in the tree
person1.add_godparent(person3.person_id)

# Add person4 as a foster relationship of person1, must exist in the tree
person1.add_foster_relationship(person4.person_id)

print(f"\n--------------------------------------------------------")
print("\nTesting UserProfileView with different access levels...")

# Test UserProfileView with the guest user
print("\nGuest User Profile:")
user_profile_view_guest = UserProfileView(guest_user, person1)
user_profile_view_guest.display_profile(family_tree)

# Test UserProfileView with the normal user
print("\nNormal User Profile:")
user_profile_view_normal = UserProfileView(normal_user, person1)
user_profile_view_normal.display_profile()

# Test UserProfileView with the admin user
print("\nAdmin User Profile:")

user_profile_view_admin = UserProfileView(admin_user, person1)
user_profile_view_admin.display_profile()

print(f"\n--------------------------------------------------------")

# Test FamilyGroupView class
print(f"\n--------------------------------------------------------")
print("\nTesting FamilyGroupView...")
try:
    # Create a FamilyGroupView object
    family_group_view = FamilyGroupView(family_tree)
    # Display a family group
    family_group_view.display_family_group([person1.person_id, person2.person_id, person3.person_id])
except ValueError as e:
    print(f"Error displaying family group: {e}")





print(f"\n--------------------------------------------------------")
# Create a PersonDetailView object and display the details of person1
print(f"\n--------------------------------------------------------")
print("\nTesting PersonDetailView...")

# Create a RelationshipView object and display the details of relationship1
print(f"\nTesting RelationshipView...")
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

print(f"\n--------------------------------------------------------")

