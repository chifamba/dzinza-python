# main.py

import logging
import os # Import the os module
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship
# Import the concrete implementation, not the abstract class for instantiation
from src.audit_log import SimpleAuditLog, PlaceholderAuditLog
from src.encryption import PlaceholderDataEncryptor # Or your actual encryptor
from src.user_management import UserManager
from src.user import User
# Import UI components if you intend to use them directly here
# from src.user_interface import ...

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main function to run the family tree application."""
    logging.info("Starting Dzinza Family Tree application.")

    # --- Initialize Core Components ---
    # Instantiate a concrete AuditLog implementation
    # audit_log = PlaceholderAuditLog() # Use this if no logging needed
    audit_log = SimpleAuditLog()      # Use this for simple in-memory logging
    encryptor = PlaceholderDataEncryptor() # Use a real encryptor in production
    user_manager = UserManager(audit_log=audit_log, encryptor=encryptor)
    family_tree = FamilyTree(audit_log=audit_log, encryptor=encryptor)

    # --- Define Data Paths ---
    # It's good practice to define paths early
    data_dir = "data"
    user_file = os.path.join(data_dir, "users.json")
    tree_file = os.path.join(data_dir, "family_tree.json")

    # --- Ensure Data Directory Exists ---
    # Create the data directory early if it doesn't exist
    try:
        os.makedirs(data_dir, exist_ok=True)
        logging.info(f"Ensured data directory exists: {data_dir}")
    except OSError as e:
        logging.error(f"Could not create data directory '{data_dir}': {e}")
        # Decide how to handle this - maybe exit or run without persistence?
        print(f"Error: Could not create data directory '{data_dir}'. Exiting.")
        return # Exit if data directory cannot be created

    # --- Load Data (Optional) ---
    # Example: Load users if file exists
    try:
        if not user_manager.load_users(user_file, actor_user_id="system"):
             logging.info(f"User file '{user_file}' not found or empty. Starting with no users.")
             # Add a default admin user if none loaded?
             # from src.encryption import hash_password # Import only if needed here
             # default_admin_hash = hash_password("admin123")
             # user_manager.add_user(User(user_id="admin", email="admin@example.com", password_hash=default_admin_hash, role="administrator"))
    except Exception as e:
         # Catch specific exceptions if possible (IOError, JSONDecodeError, etc.)
         logging.error(f"Failed to load users from {user_file}: {e}")


    # Example: Load family tree data if file exists
    try:
        # import_file handles FileNotFoundError internally and logs it
        family_tree.import_file(tree_file, user="system")
    except ValueError as e: # Catch specific errors from import_file if needed
         logging.error(f"Error importing family tree data from {tree_file}: {e}")
    except Exception as e:
        # Catch any other unexpected errors during import
        logging.error(f"Unexpected error loading family tree data from {tree_file}: {e}")


    # --- Application Logic / User Interaction ---
    # This is where you would integrate your command-line interface,
    # web server (like Flask/Django), or GUI (like Tkinter/PyQt).

    print("\n--- Welcome to Dzinza Family Tree ---")

    # Example: Add some data if the tree is empty and no file was loaded
    if not family_tree.persons and not os.path.exists(tree_file):
        logging.info("Family tree is empty and no data file found. Adding sample data.")
        p1 = Person(person_id="p1", first_name="Alice", last_name="Alpha", birth_date="1980-05-15")
        p2 = Person(person_id="p2", first_name="Bob", last_name="Beta", birth_date="1978-11-20")
        p3 = Person(person_id="p3", first_name="Charlie", last_name="Alpha", birth_date="2005-01-30") # Child of A & B

        family_tree.add_person(p1, user="system_setup")
        family_tree.add_person(p2, user="system_setup")
        family_tree.add_person(p3, user="system_setup")

        family_tree.add_relationship("p1", "p2", "spouse", user="system_setup")
        family_tree.add_relationship("p3", "p1", "child", user="system_setup") # p3 is child of p1
        # Reciprocal (parent) is added automatically by add_relationship

        print("Added sample persons: Alice, Bob, Charlie.")
        print("Added relationships: Alice-Bob (spouse), Charlie-Alice (child).")


    # Example: Display some information
    print("\n--- Current Persons ---")
    if family_tree.persons:
        for person_id, person in family_tree.persons.items():
            print(f"- {person.get_full_name()} (ID: {person_id}, Age: {person.get_age()})")
    else:
        print("- No persons in the tree.")

    print("\n--- Relationships for Alice (p1) ---")
    alice = family_tree.get_person("p1")
    if alice:
        alice_rels = family_tree.get_relationships("p1")
        if alice_rels:
            for rel in alice_rels:
                related_person = family_tree.get_person(rel.person2_id)
                related_name = related_person.get_full_name() if related_person else "Unknown"
                print(f"- {rel.rel_type.capitalize()} of {related_name} (ID: {rel.person2_id})")
        else:
            print(f"- {alice.get_full_name()} has no relationships recorded.")
    else:
         print("- Person p1 (Alice) not found.")


    # --- Placeholder for interactive loop or server start ---
    # while True:
    #     command = input("Enter command (e.g., add_person, show_tree, exit): ")
    #     if command == "exit":
    #         break
    #     # Process command using UserInterface or directly call manager/tree methods
    #     pass


    # --- Save Data Before Exiting (Optional) ---
    # Directory creation is now handled earlier

    logging.info("Attempting to save data...")
    if user_manager.save_users(user_file, actor_user_id="system_shutdown"):
        logging.info(f"User data saved to {user_file}")
    else:
        # save_users logs errors internally
        logging.error(f"Saving user data to {user_file} failed (see previous logs).")

    try:
        family_tree.export_file(tree_file, user="system_shutdown")
        logging.info(f"Family tree data saved to {tree_file}")
    except Exception as e:
         # export_file logs errors internally, but we can log failure here too
         logging.error(f"Saving family tree data to {tree_file} failed: {e}")


    logging.info("Dzinza Family Tree application finished.")
    print("\nApplication finished.")

if __name__ == "__main__":
    main()
