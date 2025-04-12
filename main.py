# main.py
import os # Import os for file operations
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship
from src.user_management import UserManager, User # Import User class
from src.user_interface import (
    FamilyGroupView,
    PersonDetailView,
    RelationshipView,
    UserProfileView, # Import UserProfileView
)
# Import placeholder classes
from src.audit_log import AuditLog
from src.encryption import DataEncryptor

# --- Setup ---
# Initialize placeholder components
audit_log = AuditLog()
# encryption_key = "a-very-secret-key-keep-safe!" # !! IMPORTANT: Manage keys securely !! Not used by placeholder.
# data_encryptor = DataEncryptor() # Placeholder

# Initialize core managers
user_manager = UserManager(audit_log=audit_log)
family_tree = FamilyTree(
    audit_log=audit_log,
    # data_encryptor=data_encryptor, # Pass real encryptor when implemented
    # encryption_key=encryption_key   # Pass real key when implemented
)

print("--- Dzinza Family Tree Application ---")

# --- User Management Examples ---
print("\n--- Testing User Management ---")
try:
    guest_user = user_manager.create_user("guest01", "guest@example.com", "password", role="guest")
    normal_user = user_manager.create_user("user01", "user@example.com", "password123") # Default role 'basic'
    admin_user = user_manager.create_user("admin01", "admin@example.com", "adminpass", role="administrator")
    print(f"Users created: {guest_user}, {normal_user}, {admin_user}")

    # Test login
    validated_user = user_manager.validate_user_credentials("user@example.com", "password123")
    if validated_user:
        print(f"Login successful for: {validated_user.user_id}")
    else:
        print("Login failed for user@example.com")

    validated_user_fail = user_manager.validate_user_credentials("user@example.com", "wrongpassword")
    if not validated_user_fail:
        print("Login correctly failed for wrong password.")

    # Test update
    user_manager.update_user("user01", new_email="user_new@example.com", new_password="newpass", new_role="trusted", acting_user_id=admin_user.user_id)
    updated_user = user_manager.get_user("user01")
    print(f"User updated: {updated_user}")
    if updated_user and updated_user.email == "user_new@example.com" and updated_user.role == "trusted":
         # Check password (using placeholder check)
         if user_manager.validate_user_credentials("user_new@example.com", "newpass"):
              print("User update verified (including password).")
         else:
              print("User update verification failed (password check).")


    # Test trust points
    user_manager.add_trust_points("user01", 150, "Verified 5 records", admin_user.user_id)
    print(f"User {updated_user.user_id} trust level: {updated_user.get_trust_level()}") # Should be level 2 or 3

    # Test UserProfileView
    profile_view = UserProfileView(target_user=updated_user, requesting_user=admin_user)
    profile_view.display_profile()


except ValueError as e:
    print(f"Error during user management setup: {e}")
except Exception as e:
     print(f"Unexpected error during user management setup: {e}")


# --- Family Tree Examples ---
print("\n--- Testing Family Tree ---")

# Define sample file paths (ensure these files exist or comment out related tests)
json_file_path_import = "test_data/sample_family.json"
json_file_path_export = "test_data/exported_family.json"
gedcom_file_path = "test_data/sample.ged" # Example path

# Create output directory if it doesn't exist
os.makedirs("test_data", exist_ok=True)

# Create a dummy JSON file for import testing if it doesn't exist
if not os.path.exists(json_file_path_import):
     print(f"Creating dummy import file: {json_file_path_import}")
     dummy_data = {
         "persons": [
             {"person_id": "p1", "creator_user_id": "system", "first_name": "John", "last_name": "Doe", "date_of_birth": "1970-01-01", "place_of_birth": "City A"},
             {"person_id": "p2", "creator_user_id": "system", "first_name": "Jane", "last_name": "Smith", "date_of_birth": "1975-05-10", "place_of_birth": "City B", "gender": "F"}
         ],
         "relationships": [
             {"person1_id": "p1", "person2_id": "p2", "relationship_type": "spouse", "start_date": "1998-06-15"}
         ]
     }
     try:
         with open(json_file_path_import, 'w') as f:
             json.dump(dummy_data, f, indent=4)
     except IOError as e:
         print(f"Error creating dummy JSON file: {e}")


# Test Import (JSON)
print(f"\nTesting import from {json_file_path_import}...")
try:
    # Create a new tree instance for import test
    imported_tree = FamilyTree(audit_log=audit_log) # Pass components
    imported_tree.import_file(json_file_path_import, user_id=admin_user.user_id)
    print("JSON file imported successfully.")
    # Display imported tree
    imported_tree.display_tree(start_person_id="p1") # Display starting from p1 if it exists
    # Assign to main tree variable if import is the primary way to load
    # family_tree = imported_tree
except (FileNotFoundError, ValueError, Exception) as e:
    print(f"Error importing JSON: {e}")

# --- Manual Person/Relationship Creation (if not importing) ---
print("\nTesting manual creation...")
try:
    # Use the main family_tree instance
    # Create persons (ensure IDs are unique if not importing)
    person1 = Person(creator_user_id=normal_user.user_id, person_id="person001", first_name="Alice", last_name="Johnson", date_of_birth="1980-03-15")
    person2 = Person(creator_user_id=normal_user.user_id, person_id="person002", first_name="Bob", last_name="Williams", date_of_birth="1978-11-20")
    person3 = Person(creator_user_id=normal_user.user_id, person_id="person003", first_name="Charlie", last_name="Johnson", date_of_birth="2005-07-01")
    person4 = Person(creator_user_id=normal_user.user_id, person_id="person004", first_name="Diana", last_name="Williams", date_of_birth="2008-09-22")

    # Add persons to the tree
    family_tree.add_person(person1, user_id=normal_user.user_id)
    family_tree.add_person(person2, user_id=normal_user.user_id)
    family_tree.add_person(person3, user_id=normal_user.user_id)
    family_tree.add_person(person4, user_id=normal_user.user_id)
    print(f"Manually added {len(family_tree.person_nodes)} persons.")

    # Create and link relationships
    rel_spouse = Relationship(person1.person_id, person2.person_id, "spouse", start_date="2003-05-10")
    rel_parent1_c1 = Relationship(person1.person_id, person3.person_id, "parent") # Alice is parent of Charlie
    rel_child1_p1 = Relationship(person3.person_id, person1.person_id, "child")   # Charlie is child of Alice
    rel_parent2_c1 = Relationship(person2.person_id, person3.person_id, "parent") # Bob is parent of Charlie
    rel_child1_p2 = Relationship(person3.person_id, person2.person_id, "child")   # Charlie is child of Bob

    rel_parent1_c2 = Relationship(person1.person_id, person4.person_id, "parent") # Alice is parent of Diana
    rel_child2_p1 = Relationship(person4.person_id, person1.person_id, "child")   # Diana is child of Alice
    rel_parent2_c2 = Relationship(person2.person_id, person4.person_id, "parent") # Bob is parent of Diana
    rel_child2_p2 = Relationship(person4.person_id, person2.person_id, "child")   # Diana is child of Bob


    family_tree.link_persons(rel_spouse, user_id=normal_user.user_id)
    family_tree.link_persons(rel_parent1_c1, user_id=normal_user.user_id)
    family_tree.link_persons(rel_child1_p1, user_id=normal_user.user_id)
    family_tree.link_persons(rel_parent2_c1, user_id=normal_user.user_id)
    family_tree.link_persons(rel_child1_p2, user_id=normal_user.user_id)
    family_tree.link_persons(rel_parent1_c2, user_id=normal_user.user_id)
    family_tree.link_persons(rel_child2_p1, user_id=normal_user.user_id)
    family_tree.link_persons(rel_parent2_c2, user_id=normal_user.user_id)
    family_tree.link_persons(rel_child2_p2, user_id=normal_user.user_id)


    print("Relationships linked.")

    # Display the manually created tree
    family_tree.display_tree(start_person_id=person1.person_id)

    # Test relationship consistency check
    print("\nChecking relationship consistency...")
    consistency_errors = family_tree.check_all_relationship_consistency(admin_user.user_id)
    if not consistency_errors:
        print("Consistency check passed.")
    else:
        print("Consistency issues found:")
        for pid, errors in consistency_errors.items():
            print(f"  Person {pid}: {errors}")

    # Test Views
    print("\nTesting Views...")
    p1_detail_view = PersonDetailView(person1)
    p1_detail_view.display_person_details()

    rel_view = RelationshipView(rel_spouse, family_tree) # Pass tree to show names
    rel_view.display_relationship()

    group_view = FamilyGroupView(family_tree)
    group_view.display_family_group([person1.person_id, person2.person_id, person3.person_id])

    # Test Search
    print("\nTesting Search...")
    search_results = family_tree.search_person("Johnson", fields=["names"])
    print(f"Search results for 'Johnson': {[p.person_id for p in search_results]}")
    search_results_date = family_tree.search_person("1978", fields=["date_of_birth"])
    print(f"Search results for '1978' in DOB: {[p.person_id for p in search_results_date]}")


    # Test Export (JSON)
    print(f"\nTesting export to {json_file_path_export}...")
    try:
        family_tree.export_file(json_file_path_export, user_id=admin_user.user_id)
        print("Export to JSON successful.")
        # Add check: try importing the exported file
        print(f"Attempting to re-import exported file: {json_file_path_export}")
        reimported_tree = FamilyTree(audit_log=audit_log)
        reimported_tree.import_file(json_file_path_export, user_id="system-reimport")
        print("Re-import successful.")
        if len(reimported_tree.person_nodes) == len(family_tree.person_nodes):
             print("Re-imported tree has the correct number of persons.")
        else:
             print("Warning: Re-imported tree person count mismatch.")


    except (ValueError, IOError, Exception) as e:
        print(f"Error exporting JSON: {e}")

    # Test Export (GEDCOM - if library available)
    if family_tree.GEDCOM_AVAILABLE:
         gedcom_export_path = "test_data/exported_family.ged"
         print(f"\nTesting export to {gedcom_export_path}...")
         try:
             family_tree.export_file(gedcom_export_path, user_id=admin_user.user_id)
             print("Export to GEDCOM successful.")
         except (ValueError, IOError, ImportError, Exception) as e:
              print(f"Error exporting GEDCOM: {e}")
    else:
         print("\nSkipping GEDCOM export test (library not available).")


except ValueError as e:
    print(f"Error during family tree setup: {e}")
except Exception as e:
     print(f"Unexpected error during family tree setup: {e}")


# --- Final Audit Log ---
print("\n--- Final Audit Log Entries ---")
all_logs = audit_log.get_log_entries()
if all_logs:
    for log in all_logs[-10:]: # Print last 10 entries
        print(f"- {log['timestamp'].strftime('%H:%M:%S')} | User: {log['user_id']} | Event: {log['event_type']} | Desc: {log['description']}")
else:
    print("(No audit log entries)")

print("\n--- Application Finished ---")
