# Dzinza Family Tree Manager

Dzinza is a Python application designed to manage family trees, genealogical data, and personal records. It provides a structured way to organize information about individuals, their relationships, and various aspects of their lives. This project aims to create a robust and flexible system for managing family history.

## Getting Started

Previews should run automatically when starting a workspace.

## Features Implemented

*   **Person Records:**
    *   Store personal information (names, date/place of birth/death, gender, biography).
    *   Manage multiple name formats for different cultures.
    *   Romanization/transliteration of names.
    *   Religious/cultural affiliations.
    *   Profile photo.
    *   Media and document management.
    *   Military, education, occupational, and medical history.
    *   DNA haplogroups.
    *   Physical characteristics.
    *   Languages spoken.
    *   Immigration/naturalization records.
*   **Relationship Management:**
    *   Define extended family relationships (grandparents, aunts/uncles, cousins, in-laws).
    *   Manage cultural-specific relationship types.
    *   Godparents/religious relationships.
    *   Foster and guardian relationships.
    *   Tribal/clan affiliations.
    *   Historical context for relationships.
    *   Relationship timeline visualization.
    *   Custom relationship types.
*   **Family Tree Features:**
    *   Basic family tree display (hierarchical view).
*   **Data Import/Export:**
    *   GEDCOM import/export.
    *   JSON import/export.
    *   CSV import/export.
    *   XML import/export.
*   **Data Validation and Integrity:**
    *   Duplicate detection and merging.
    *   Data validation rules.
    *   Relationship consistency checks.
*   **User Interface and Reporting:**
    *   User profile view.
    *   Family group view.
    *   Person detail view.
    *   Relationship view.
    *   Family tree report.
    *   Person summary report.
    *   Custom reports.
    *   Search and filtering.
*   **Security and Privacy:**
    *   Privacy settings.
    *   Access control.
    *   Data encryption.
*   **Audit Log:**
    * Not implemented yet.

## Modules and Classes

*   **person.py:** Defines the `Person` class, which represents an individual in the family tree.
*   **relationship.py:** Defines the `Relationship` class, which represents a relationship between two `Person` objects.
*   **family_tree.py:** Defines the `FamilyTree` class, which manages the family tree structure and operations.
*   **user_management.py:** Defines the `User` and `UserManager` classes for user management.
*   **user_interface.py:** Defines classes for displaying data in different views (`UserProfileView`, `FamilyGroupView`, `PersonDetailView`, `RelationshipView`).
*   **encryption.py:** Defines the `DataEncryptor` class for data encryption and decryption.

## Data Encryption

The application uses AES symmetric encryption to protect sensitive data. The `DataEncryptor` class in `encryption.py` handles the encryption and decryption. The `Person` class uses it to encrypt `biography`, `medical_history`, `physical_characteristics`, `dna_haplogroups`, `immigration_naturalization_records`, `documents`, and `media`. The `FamilyTree` class uses it to encrypt and decrypt the entire JSON representation of the tree.
To use encryption, pass an `encryption_key` (string) when creating `Person` and `FamilyTree` objects.

## How to Run

1.  Clone the repository.
2.  Install the required dependencies.
3.  Run the `main.py` file.