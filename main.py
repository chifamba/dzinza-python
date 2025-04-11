from src.user_management import UserManager
from src.user import User
from src.family_tree import FamilyTree
from src.person import Person
import time
from datetime import datetime, timedelta

# Main function
def main():
    # Create an instance of UserManager to manage users
    user_manager = UserManager()

    # Create users with unique IDs, emails, and passwords
    user1_id = 1
    email1 = "test1@example.com"
    password_1 = "password123"
    user_manager.create_user(user1_id, email1, password_1)

    user2_id = 2
    email2 = "test2@example.com"
    password_2 = "password456"
    user_manager.create_user(user2_id, email2, password_2)

    user3_id = 3
    email3 = "test3@example.com"
    password_3 = "password789"
    user_manager.create_user(user3_id, email3, password_3)

    user4_id = 4
    email4 = "test4@example.com"
    password_4 = "password101"
    user_manager.create_user(user4_id, email4, password_4)


    # Add trust points to the second user
    user2 = user_manager.get_user(user2_id)

    user_manager.add_trust_points(user2_id, 150)

    # Print user information before applying trust decay
    print("Users info before apply decay:")
    for user_id in user_manager.users:
        user = user_manager.users[user_id]
        print(f"User {user.user_id} info : {user.__dict__}")

    # Make user 2 inactive by setting last_login to 35 days ago
    user2.last_login = datetime.now() - timedelta(days=35)

    # Apply trust decay
    user_manager.apply_trust_decay()

    # Print user information after applying trust decay
    print("Users info after apply decay:")
    for user_id in user_manager.users:
        user = user_manager.users[user_id]
        print(f"User {user.user_id} info : {user.__dict__}")

    # Promote the first user to administrator
    user_manager.promote_to_administrator(user1_id)

    # Promote the first user to a trusted user
    user_manager.promote_to_trusted(user1_id)

    # Get the first user object
    user1 = next((user for user in user_manager.users.values() if user.user_id == user1_id), None)


    # Create an instance of FamilyTree
    family_tree = FamilyTree()

    # Create persons
    person1 = Person(id=1, first_name="John", last_name="Doe")
    person2 = Person(id=2, first_name="Jane", last_name="Doe")
    person3 = Person(id=3, first_name="Peter", last_name="Doe")

    #set info to person1
    person1.set_biography("A short biography of John")
    person1.set_date_of_birth("1980-01-01")
    person1.set_place_of_birth("New York")
    person1.set_date_of_death("2023-01-01")
    person1.set_place_of_death("Los Angeles")
    person1.set_gender("Male")
    person1.set_current_location("Los Angeles")
    person1.set_privacy_settings("public")

    # Set a profile photo for the first person
    person1.set_profile_photo("https://example.com/profile1.jpg")

    # Set documents and media for first person
    person1.add_document("https://example.com/document1.pdf")
    person1.add_media("https://example.com/media1.mp4")

    # Add multiple names for the person1
    person1.add_name({"name": "John", "type": "birth", "culture": "English"})
    person1.add_name({"name": "Juan", "type": "nick", "culture": "Spanish"})
    print(f"Names of {person1.first_name}: {person1.get_names()}")
    # Set romanization, transliteration and religious affiliations for first person
    person1.set_romanization("Jhon")
    person1.set_transliteration("Йон")
    person1.add_religious_affiliation("Catholic")

    # Add persons to the family tree using the new methods
    family_tree.add_person(person1)  # Add person1 as root
    family_tree.add_person_with_parents(person2, [person1.id]) # add person 2 and its parents
    family_tree.add_person_with_parents(person3, [person1.id]) # add person 3 and its parents

    # Link persons directly
    # Example: Link person1 and person2 as parent and child
    family_tree.link_persons(person1.id, person2.id, "child")
    # Example: Link person1 and person3 as parent and child
    family_tree.link_persons(person1.id, person3.id, "child")
    # Example: Link person3 and person2 as siblings
    family_tree.link_persons(person3.id, person2.id, "sibling")

    # Test get_parents method
    parents = person2.get_parents(family_tree)
    print(f"Parents of {person2.first_name}: {[parent.first_name for parent in parents]}")  # Should print John

    # Test get_children
    children = person1.get_children(family_tree)
    # Test get_children
    print(f"Children of {person1.first_name}: {[child.first_name for child in person1.get_children(family_tree)]}")  # Should print Jane and Peter

    # Test get_siblings method
    siblings = person2.get_siblings(family_tree)
    # Test get_siblings
    print(f"Siblings of {person2.first_name}: {[sibling.first_name for sibling in person2.get_siblings(family_tree)]}")  # Should print Peter
    # Test get_spouses method (no spouses yet)
    # Test get_spouses (no spouses yet)
    print(f"Spouses of {person1.first_name}: {[spouse.first_name for spouse in person1.get_spouses(family_tree)]}")  # Should print an empty list

    # Test get profile photo
    print(f"Profile photo of {person1.first_name}: {person1.get_profile_photo()}")

    # Test get documents and media
    print(f"Documents of {person1.first_name}: {person1.get_documents()}")
    print(f"Media of {person1.first_name}: {person1.get_media()}")

    # Print Person 1 info
    print(f"Person 1 biography : {person1.get_biography()}")
    print(f"Person 1 Date of birth : {person1.date_of_birth}")
    print(f"Person 1 place of birth : {person1.place_of_birth}")
    print(f"Person 1 Date of death : {person1.date_of_death}")
    print(f"Person 1 place of death : {person1.place_of_death}")
    print(f"Person 1 gender : {person1.gender}")
    print(f"Person 1 current location : {person1.current_location}")
    print(f"Person 1 privacy settings : {person1.privacy}")

    # Test romanization and transliteration
    print(f"Person 1 romanization : {person1.get_romanization()}")
    print(f"Person 1 transliteration : {person1.get_transliteration()}")
    print(f"Person 1 religious affiliations : {person1.get_religious_affiliations()}")
    
    # Set military service records, educational history, occupational history, 
    # medical history, dna haplogroups, physical characteristics, languages spoken, 
    # and immigration/naturalization records for first person
    person1.add_military_service_record("Army 1990-1995")
    person1.add_educational_history("University of New York")
    person1.add_occupational_history("Software Engineer")
    person1.add_medical_history("Healthy")
    person1.add_dna_haplogroup("R1b")
    person1.add_physical_characteristic("Tall")
    person1.add_language_spoken("English")
    person1.add_immigration_naturalization_record("US Naturalization 2000")

    # Test get military service records, educational history, occupational history,
    # medical history, dna haplogroups, physical characteristics, languages spoken,
    # and immigration/naturalization records
    print(f"Person 1 military service records : {person1.get_military_service_records()}")
    print(f"Person 1 educational history : {person1.get_educational_history()}")
    print(f"Person 1 occupational history : {person1.get_occupational_history()}")
    print(f"Person 1 medical history : {person1.get_medical_history()}")
    print(f"Person 1 DNA haplogroups : {person1.get_dna_haplogroups()}")
    print(f"Person 1 physical characteristics : {person1.get_physical_characteristics()}")
    print(f"Person 1 languages spoken : {person1.get_languages_spoken()}")
    print(f"Person 1 immigration/naturalization records : {person1.get_immigration_naturalization_records()}")







if __name__ == "__main__":
    main()
