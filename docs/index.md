# Dzinza: Genealogical Data Management Library

## Project Description:

Dzinza is a Python library designed for managing genealogical data. It provides a structured way to represent individuals, families, and their relationships, allowing for efficient storage, retrieval, and manipulation of genealogical information. The library supports data import and export in various formats (GEDCOM, JSON, CSV, XML), includes data validation and integrity checks, and offers a flexible user interface for viewing and reporting genealogical data. It also includes strong security and privacy features like data encryption and access control.

## Main Features

-   **Data Representation:**
    -   `Person`: Represents an individual with personal details, relationships, and life events.
    -   `Relationship`: Represents the relationships between persons.
    - `FamilyTree`: Represents the family tree with the persons and relationships.
-   **Data Import/Export:**
    -   Import data from GEDCOM, JSON, CSV, and XML files.
    -   Export data to GEDCOM, JSON, CSV, and XML files.
-   **Data Validation and Integrity:**
    -   Duplicate detection and merging.
    -   Data validation rules to ensure data quality.
    -   Relationship consistency checks.
-   **User Interface and Reporting:**
    -   User profile view.
    -   Family group view.
    -   Person detail view.
    -   Relationship view.
    -   Family tree report.
    -   Person summary report.
    -   Custom reports.
-   **Security and Privacy:**
    -   Privacy settings for individual fields.
    -   Access control based on user roles and relationships.
    -   Data encryption using AES.
    -   Audit log to track changes.
-   **Search and Filtering:**
    - Search persons by different attributes.

## Installation

To use the Dzinza library, you need to have Python 3 installed on your system. You can install the library using pip:
```
bash
# Not released, so you must clone it and run main.py

# Clone the repository
git clone https://github.com/chifamba/dzinza-python.git

# Enter the directory
cd dzinza-python

#Run the main.py file
python main.py
```
## How to Use the Library

Here's a basic example of how to use the Dzinza library to create a family tree, add persons, and relationships:
```
python
from src.family_tree import FamilyTree
from src.person import Person
from src.relationship import Relationship
from src.encryption import DataEncryptor

# Create a DataEncryptor object
data_encryptor = DataEncryptor()
encryption_key = "your_encryption_key"

# Create a FamilyTree object with encryption
family_tree = FamilyTree(encryption_key=encryption_key)

# Create persons
person1 = Person("person1", "Name1", "LastName1", "1970-01-01", "Place1", encryption_key=encryption_key)
person2 = Person("person2", "Name2", "LastName2", "1975-05-10", "Place2", encryption_key=encryption_key)
person3 = Person("person3", "Name3", "LastName3", "1995-11-15", "Place3", encryption_key=encryption_key)

# Add persons to the tree
family_tree.add_person(person1)
family_tree.add_person(person2)
family_tree.add_person(person3)

# Create and add relationships
relationship1 = Relationship(person1.person_id, person2.person_id, "spouse")
relationship2 = Relationship(person3.person_id, person1.person_id, "child")
family_tree.link_persons(relationship1)
family_tree.link_persons(relationship2)

# Display the tree
family_tree.display_tree()

# Export to json file
family_tree.export_json("output.json")
```
## Class Documentation

### Person

Represents an individual with personal details, relationships, and life events.

**Constructor:**
```
python
Person(person_id, first_name, last_name, date_of_birth, place_of_birth, encryption_key, date_of_death=None, place_of_death=None, family_tree=None)
```
-   `person_id` (str): Unique identifier for the person.
-   `first_name` (str): First name of the person.
-   `last_name` (str): Last name of the person.
-   `date_of_birth` (str): Date of birth (YYYY-MM-DD).
-   `place_of_birth` (str): Place of birth.
- `encryption_key` (str): The encryption key to encrypt the data of this object.
-   `date_of_death` (str, optional): Date of death (YYYY-MM-DD).
-   `place_of_death` (str, optional): Place of death.
-   `family_tree` (`FamilyTree`, optional): The family tree where this person belongs.

**Methods:**

-   `add_name(name, type, culture)`: Adds a name with type and culture.
    - `name` (str): The name.
    - `type` (str): The type of the name.
    - `culture` (str): The culture of the name.
-   `remove_name(name, type, culture)`: Removes a name.
    - `name` (str): The name.
    - `type` (str): The type of the name.
    - `culture` (str): The culture of the name.
-   `get_names(name_type=None, culture=None)`: Returns a list of names.
    - `name_type` (str): The type of name to get (optional).
    - `culture` (str): The culture of name to get (optional).
    - Returns: `list` of names.
-   `set_romanization(romanization)`: Sets the romanization.
    - `romanization` (str): The romanization.
-   `get_romanization()`: Gets the romanization.
    - Returns: `str` with the romanization.
-   `set_transliteration(transliteration)`: Sets the transliteration.
    - `transliteration` (str): The transliteration.
-   `get_transliteration()`: Gets the transliteration.
    - Returns: `str` with the transliteration.
-   `add_religious_affiliation(affiliation)`: Adds a religious affiliation.
    - `affiliation` (str): The affiliation.
- `remove_religious_affiliation(affiliation)`: Removes a religious affiliation.
    - `affiliation` (str): The affiliation.
- `get_religious_affiliations()`: Gets the religious affiliations.
    - Returns: `list` with the affiliations.
-   `get_parents()`: Gets the parents of the person.
    - Returns: `list` of `Person` objects.
-   `get_children()`: Gets the children of the person.
    - Returns: `list` of `Person` objects.
-   `get_spouses()`: Gets the spouses of the person.
    - Returns: `list` of `Person` objects.
-   `get_siblings()`: Gets the siblings of the person.
    - Returns: `list` of `Person` objects.
- `add_grandparent(grandparent_id)`: Adds a grandparent
    - `grandparent_id` (str): The id of the grandparent.
- `add_aunt_uncle(aunt_uncle_id)`: Adds an aunt or uncle.
    - `aunt_uncle_id` (str): The id of the aunt or uncle.
- `add_cousin(cousin_id)`: Adds a cousin.
    - `cousin_id` (str): The id of the cousin.
- `add_inlaw(inlaw_id)`: Adds an inlaw.
    - `inlaw_id` (str): The id of the inlaw.
- `add_extended_family(extended_family_id)`: Adds an extended family member.
    - `extended_family_id` (str): The id of the extended family member.
- `get_grandparents()`: Gets the grandparents.
    - Returns: `list` of `Person` objects.
- `get_aunt_uncles()`: Gets the aunts and uncles.
    - Returns: `list` of `Person` objects.
- `get_cousins()`: Gets the cousins.
    - Returns: `list` of `Person` objects.
- `add_cultural_relationship(relationship_type, related_person_id)`: Adds a cultural relationship.
    - `relationship_type` (str): The type of relationship.
    - `related_person_id` (str): The id of the related person.
- `remove_cultural_relationship(relationship_type, related_person_id)`: Removes a cultural relationship.
    - `relationship_type` (str): The type of relationship.
    - `related_person_id` (str): The id of the related person.
- `get_cultural_relationships()`: Gets the cultural relationships.
    - Returns: `dict` with the cultural relationships.
- `add_godparent(godparent_id)`: Adds a godparent.
    - `godparent_id` (str): The id of the godparent.
- `remove_godparent(godparent_id)`: Removes a godparent.
    - `godparent_id` (str): The id of the godparent.
- `get_godparents()`: Gets the godparents.
    - Returns: `list` with the godparents.
- `add_foster_relationship(person_id)`: Adds a foster relationship.
    - `person_id` (str): The id of the person.
- `remove_foster_relationship(person_id)`: Removes a foster relationship.
    - `person_id` (str): The id of the person.
- `get_foster_relationships()`: Gets the foster relationships.
    - Returns: `list` with the foster relationships.
- `add_guardian_relationship(person_id)`: Adds a guardian relationship.
    - `person_id` (str): The id of the person.
- `remove_guardian_relationship(person_id)`: Removes a guardian relationship.
    - `person_id` (str): The id of the person.
- `get_guardian_relationships()`: Gets the guardian relationships.
    - Returns: `list` with the guardian relationships.
- `add_tribal_clan_affiliation(affiliation)`: Adds a tribal clan affiliation.
    - `affiliation` (str): The affiliation.
- `remove_tribal_clan_affiliation(affiliation)`: Removes a tribal clan affiliation.
    - `affiliation` (str): The affiliation.
- `get_tribal_clan_affiliations()`: Gets the tribal clan affiliations.
    - Returns: `list` with the affiliations.
-   `set_family_tree(family_tree)`: Sets the family tree.
    -   `family_tree` (`FamilyTree`): The family tree.
-   `set_profile_photo(url)`: Sets the profile photo URL.
    -   `url` (str): The profile photo URL.
-   `get_profile_photo()`: Gets the profile photo URL.
    -   Returns: `str` with the profile photo url.
-   `add_document(document)`: Adds a document.
    -   `document` (str): The document.
-   `remove_document(document)`: Removes a document.
    -   `document` (str): The document.
-   `get_documents()`: Gets the documents.
    -   Returns: `list` with the documents.
-   `add_media(media)`: Adds a media.
    -   `media` (str): The media.
-   `add_military_service_record(record)`: Adds a military service record.
    -   `record` (str): The record.
-   `remove_military_service_record(record)`: Removes a military service record.
    -   `record` (str): The record.
-   `get_military_service_records()`: Gets the military service records.
    -   Returns: `list` with the military service records.
-   `add_educational_history(record)`: Adds an educational history record.
    -   `record` (str): The record.
-   `remove_educational_history(record)`: Removes an educational history record.
    -   `record` (str): The record.
-   `get_educational_history()`: Gets the educational history.
    -   Returns: `list` with the educational history.
-   `add_occupational_history(record)`: Adds an occupational history record.
    -   `record` (str): The record.
-   `remove_occupational_history(record)`: Removes an occupational history record.
    -   `record` (str): The record.
-   `get_occupational_history()`: Gets the occupational history.
    -   Returns: `list` with the occupational history.
-   `add_medical_history(record)`: Adds a medical history record.
    -   `record` (str): The record.
-   `remove_medical_history(record)`: Removes a medical history record.
    -   `record` (str): The record.
-   `get_medical_history()`: Gets the medical history.
    -   Returns: `list` with the medical history.
-   `set_dna_haplogroups(haplogroups)`: Sets the DNA haplogroups.
    -   `haplogroups` (list): The haplogroups.
-   `get_dna_haplogroups()`: Gets the DNA haplogroups.
    -   Returns: `list` with the DNA haplogroups.
-   `add_physical_characteristic(characteristic)`: Adds a physical characteristic.
    -   `characteristic` (str): The characteristic.
-   `remove_physical_characteristic(characteristic)`: Removes a physical characteristic.
    -   `characteristic` (str): The characteristic.
-   `get_physical_characteristics()`: Gets the physical characteristics.
    -   Returns: `list` with the physical characteristics.
-   `add_language_spoken(language)`: Adds a language spoken.
    -   `language` (str): The language.
-   `remove_language_spoken(language)`: Removes a language spoken.
    -   `language` (str): The language.
-   `get_languages_spoken()`: Gets the languages spoken.
    -   Returns: `list` with the languages spoken.
- `add_historical_context_relationship(relationship_type, context)`: Adds an historical context relationship.
    - `relationship_type` (str): The type of relationship.
    - `context` (str): The context.
- `remove_historical_context_relationship(relationship_type, context)`: Removes an historical context relationship.
    - `relationship_type` (str): The type of relationship.
    - `context` (str): The context.
- `get_historical_context_relationships()`: Gets the historical context relationships.
    - Returns: `dict` with the historical context relationships.
- `add_relationship_event(person_id, event, date)`: Adds a relationship event.
    - `person_id` (str): The id of the person.
    - `event` (str): The event.
    - `date` (str): The date.
- `get_relationship_timeline()`: Gets the relationship timeline.
    - Returns: `dict` with the relationship timeline.
- `add_custom_relationship(relationship_name, person_id)`: Adds a custom relationship.
    - `relationship_name` (str): The name of the relationship.
    - `person_id` (str): The id of the person.
- `remove_custom_relationship(relationship_name, person_id)`: Removes a custom relationship.
    - `relationship_name` (str): The name of the relationship.
    - `person_id` (str): The id of the person.
- `get_custom_relationships()`: Gets the custom relationships.
    - Returns: `dict` with the custom relationships.
- `set_privacy_setting(field, privacy_level)`: Sets the privacy setting for a field.
    - `field` (str): The name of the field.
    - `privacy_level` (str): The privacy level.
- `get_privacy_setting(field)`: Gets the privacy setting for a field.
    - `field` (str): The name of the field.
    - Returns: `str` with the privacy level.
-   `add_relationship(relationship)`: Adds a relationship.
    -   `relationship` (`Relationship`): The relationship to add.
- `get_person_info()`: Gets a dictionary with all the person info.
    - Returns: `dict` with all the info.

### FamilyTree

Represents a family tree and manages the relationships between individuals.

**Constructor:**
```
python
FamilyTree(encryption_key, audit_log=None)
```
- `encryption_key` (str): The encryption key to encrypt the data of the persons in the tree.
-   `audit_log` (`AuditLog`, optional): The audit log object to track changes.

**Methods:**

-   `add_person(person, parents=None, user_id="system")`: Adds a person to the tree.
    -   `person` (`Person`): The person to add.
    -   `parents` (list of `Person`, optional): The parents of the person.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `link_persons(relationship, user_id="system")`: Links two persons with a relationship.
    -   `relationship` (`Relationship`): The relationship between the persons.
    - `user_id` (str, optional): The id of the user doing the action.
-   `get_person(person_id)`: Gets a person by ID.
    -   `person_id` (int): The ID of the person.
    -   Returns: `Person` object.
- `get_person_by_id(person_id)`: Gets a person by ID.
    - `person_id` (int): The ID of the person.
    - Returns: `Person` object.
-   `display_tree()`: Displays the family tree in the console.
-   `import_gedcom(gedcom_file_path, user_id="system")`: Imports data from a GEDCOM file.
    -   `gedcom_file_path` (str): The path to the GEDCOM file.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `export_gedcom(file_path, user_id="system")`: Exports data to a GEDCOM file.
    -   `file_path` (str): The path to the file.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `import_json(json_file_path, user_id="system")`: Imports data from a JSON file.
    -   `json_file_path` (str): The path to the JSON file.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `export_json(file_path, user_id="system")`: Exports data to a JSON file.
    -   `file_path` (str): The path to the file.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `import_csv(csv_file_path, user_id="system")`: Imports data from a CSV file.
    -   `csv_file_path` (str): The path to the CSV file.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `export_csv(csv_file_path, user_id="system")`: Exports data to a CSV file.
    -   `csv_file_path` (str): The path to the file.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `import_xml(xml_file_path, user_id="system")`: Imports data from an XML file.
    -   `xml_file_path` (str): The path to the XML file.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `export_xml(xml_file_path, user_id="system")`: Exports data to an XML file.
    -   `xml_file_path` (str): The path to the file.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `find_duplicates()`: Finds potential duplicate persons.
    -   Returns: `list` of `list` of `Person` objects (each inner list contains duplicates).
-   `merge_persons(person1_id, person2_id, user_id="system")`: Merges two persons.
    -   `person1_id` (str): The ID of the first person.
    -   `person2_id` (str): The ID of the second person.
    -   `user_id` (str, optional): The id of the user doing the action.
-   `validate_person_data(person)`: Validates the data of a person.
    -   `person` (`Person`): The person to validate.
    -   Returns: `list` of `str` with the errors found.
- `check_relationship_consistency(person_id, user_id="system")`: Check the consistency of the relationships of a person.
    - `person_id` (str): The id of the person.
    - `user_id` (str, optional): The id of the user doing the action.
- `check_all_relationship_consistency(user_id="system")`: Check the consistency of all the relationships of all the persons in the tree.
    - `user_id` (str, optional): The id of the user doing the action.
- `generate_family_tree_report()`: Generate a family tree report.
    - Returns: `str` with the report.
- `generate_person_summary_report(person_id)`: Generate a person summary report.
    - `person_id` (str): The id of the person.
    - Returns: `str` with the report.
- `generate_custom_report(person_ids, fields)`: Generate a custom report.
    - `person_ids` (list): The ids of the persons.
    - `fields` (list): The fields to show in the report.
    - Returns: `str` with the report.
- `search_person(query, fields)`: Search a person.
    - `query` (str): The query to search.
    - `fields` (list): The fields to search in.
    - Returns: `list` of `Person` objects that match the search.
- `delete_person(person_id, user_id="system")`: Deletes a person.
    - `person_id` (str): The ID of the person to delete.
    - `user_id` (str, optional): The id of the user doing the action.

### Relationship

Represents a relationship between two persons.

**Constructor:**
```
python
Relationship(person1_id, person2_id, relationship_type, start_date=None, end_date=None, description=None)
```
-   `person1_id` (str): The ID of the first person.
-   `person2_id` (str): The ID of the second person.
-   `relationship_type` (str): The type of relationship (`parent`, `child`, `spouse`, `sibling`, `other`).
-   `start_date` (str, optional): The start date of the relationship (YYYY-MM-DD).
-   `end_date` (str, optional): The end date of the relationship (YYYY-MM-DD).
-   `description` (str, optional): A description of the relationship.

### User

Represents a user with authentication and access control information.

**Constructor:**
```
python
User(user_id, email, password, role=None, trust_level=None, access_level="user")
```
-   `user_id` (str): Unique identifier for the user.
-   `email` (str): User's email.
-   `password` (str): User's password.
-   `role` (str, optional): User's role.
-   `trust_level` (str, optional): User's trust level.
-   `access_level` (str, optional): The access level of the user (`admin`, `user`, `guest`)

### UserManager

Manages user creation, update and deletion.

**Constructor:**
```
python
UserManager(audit_log=None)
```
-   `audit_log` (`AuditLog`, optional): The audit log object to track changes.

**Methods:**

-   `create_user(user_id, email, password, user_id_creator="system")`: Creates a new user.
    -   `user_id` (str): The user ID.
    -   `email` (str): The user email.
    -   `password` (str): The user password.
    -   `user_id_creator` (str, optional): The id of the user that is creating the user.
    - Returns: The `User` object created.
-   `update_user(user_id, email=None, password=None, role=None, trust_level=None, user_id_updater="system")`: Updates a user.
    -   `user_id` (str): The user ID.
    -   `email` (str, optional): The new email.
    -   `password` (str, optional): The new password.
    -   `role` (str, optional): The new role.
    -   `trust_level` (str, optional): The new trust level.
    - `user_id_updater` (str, optional): The id of the user that is updating the user.
-   `delete_user(user_id, user_id_deleter="system")`: Deletes a user.
    -   `user_id` (str): The user ID.
    - `user_id_deleter` (str, optional): The id of the user that is deleting the user.

### UserProfileView

Displays a user's profile information.

**Constructor:**
```
python
UserProfileView(user, user_request)
```
-   `user` (`User`): The user whose profile is displayed.
- `user_request` (`User`): The user that is requesting the information.

**Methods:**

-   `display_profile()`: Displays the user's profile.

### FamilyGroupView

Displays a summary of a group of family members.

**Constructor:**
```
python
FamilyGroupView(family_tree)
```
-   `family_tree` (`FamilyTree`): The family tree.

**Methods:**

-   `display_family_group(person_ids)`: Displays a family group.
    -   `person_ids` (list of str): The IDs of the persons to display.

### PersonDetailView

Displays the details of a person.

**Constructor:**
```
python
PersonDetailView(person)
```
-   `person` (`Person`): The person to display.

**Methods:**

-   `display_person_details()`: Displays the person's details.

### RelationshipView

Displays the details of a relationship.

**Constructor:**
```
python
RelationshipView(relationship)
```
-   `relationship` (`Relationship`): The relationship to display.

**Methods:**

-   `display_relationship()`: Displays the relationship details.

### DataEncryptor

Encrypts and decrypts data.

**Constructor:**
```
python
DataEncryptor()
```
**Methods:**

-   `encrypt_data(data, encryption_key)`: Encrypts data.
    -   `data` (str): The data to encrypt.
    -   `encryption_key` (str): The encryption key.
    -   Returns: `str` with the encrypted data.
-   `decrypt_data(encrypted_data, encryption_key)`: Decrypts data.
    -   `encrypted_data` (str): The encrypted data.
    -   `encryption_key` (str): The encryption key.
    -   Returns: `str` with the decrypted data.

### AuditLog

Tracks events in the system.

**Constructor:**
```
python
AuditLog()
```
**Methods:**

-   `log_event(user_id, event_type, description)`: Logs an event.
    -   `user_id` (str): The ID of the user.
    -   `event_type` (str): The type of event.
    -   `description` (str): A description of the event.
-   `get_log_entries(user_id=None, event_type=None, start_date=None, end_date=None)`: Gets log entries.
    -   `user_id` (str, optional): The user ID to filter by.
    -   `event_type` (str, optional): The event type to filter by.
    -   `start_date` (str, optional): The start date to filter by (YYYY-MM-DD).
    -   `end_date` (str, optional): The end date to filter by (YYYY-MM-DD).
    -   Returns: `list` of log entries.
-   `clear_log()`: Clears the log.