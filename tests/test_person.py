import unittest
from src.person import Person
from src.encryption import DataEncryptor


class TestPerson(unittest.TestCase):
    def setUp(self):
        """Set up a Person object and a DataEncryptor object for testing."""
        self.encryption_key = "test_encryption_key"
        self.person = Person(
            person_id="test_person",
            first_name="Test",
            last_name="Person",
            date_of_birth="1990-01-01",
            place_of_birth="Test Place",
            encryption_key=self.encryption_key
        )
        self.encryptor = DataEncryptor()

    def test_add_name(self):
        """Test adding a name to the Person."""
        self.person.add_name(name="New Name", type="middle", culture="test")
        self.assertEqual(len(self.person.names), 3)

    def test_add_name_duplicate(self):
        """Test adding a duplicate name to the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.add_name(name="Test", type="first", culture="default")

    def test_remove_name(self):
        """Test removing a name from the Person."""
        self.person.remove_name(name="Test", type="first", culture="default")
        self.assertEqual(len(self.person.names), 1)

    def test_remove_name_not_found(self):
        """Test removing a non-existent name from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_name(name="Nonexistent", type="first", culture="test")

    def test_get_names(self):
        """Test getting names from the Person."""
        self.assertEqual(len(self.person.get_names()), 2)
        self.assertEqual(len(self.person.get_names(name_type="first")), 1)
        self.assertEqual(len(self.person.get_names(culture="default")), 2)

    def test_add_religious_affiliation(self):
        """Test adding a religious affiliation to the Person."""
        self.person.add_religious_affiliation("Test Religion")
        self.assertEqual(len(self.person.religious_affiliations), 1)

    def test_add_religious_affiliation_duplicate(self):
        """Test adding a duplicate religious affiliation to the Person, must raise a ValueError."""
        self.person.add_religious_affiliation("Test Religion")
        with self.assertRaises(ValueError):
            self.person.add_religious_affiliation("Test Religion")

    def test_remove_religious_affiliation(self):
        """Test removing a religious affiliation from the Person."""
        self.person.add_religious_affiliation("Test Religion")
        self.person.remove_religious_affiliation("Test Religion")
        self.assertEqual(len(self.person.religious_affiliations), 0)

    def test_remove_religious_affiliation_not_found(self):
        """Test removing a non-existent religious affiliation from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_religious_affiliation("Nonexistent Religion")

    def test_get_religious_affiliations(self):
        """Test getting religious affiliations from the Person."""
        self.person.add_religious_affiliation("Test Religion")
        self.assertEqual(self.person.get_religious_affiliations(), ["Test Religion"])

    def test_add_parent(self):
        """Test adding a parent to the Person."""
        self.person.add_parent("parent1")
        self.assertEqual(len(self.person.relationships["parent"]), 1)

    def test_add_child(self):
        """Test adding a child to the Person."""
        self.person.add_child("child1")
        self.assertEqual(len(self.person.relationships["child"]), 1)

    def test_add_spouse(self):
        """Test adding a spouse to the Person."""
        self.person.add_spouse("spouse1")
        self.assertEqual(len(self.person.relationships["spouse"]), 1)

    def test_add_sibling(self):
        """Test adding a sibling to the Person."""
        self.person.add_sibling("sibling1")
        self.assertEqual(len(self.person.relationships["sibling"]), 1)

    def test_add_grandparent(self):
        """Test adding a grandparent to the Person."""
        self.person.add_grandparent("grandparent1")
        self.assertEqual(len(self.person.relationships["grandparents"]), 1)

    def test_add_aunt_uncle(self):
        """Test adding an aunt/uncle to the Person."""
        self.person.add_aunt_uncle("aunt_uncle1")
        self.assertEqual(len(self.person.relationships["aunt_uncles"]), 1)
    
    def test_add_cousin(self):
        """Test adding a cousin to the Person."""
        self.person.add_cousin("cousin1")
        self.assertEqual(len(self.person.relationships["cousins"]), 1)

    def test_add_inlaw(self):
        """Test adding an inlaw to the Person."""
        self.person.add_inlaw("inlaw1")
        self.assertEqual(len(self.person.relationships["inlaws"]), 1)

    def test_add_extended_family(self):
        """Test adding an extended family member to the Person."""
        self.person.add_extended_family("extended_family1")
        self.assertEqual(len(self.person.relationships["extended_family"]), 1)

    def test_add_cultural_relationship(self):
        """Test adding a cultural relationship to the Person."""
        self.person.add_cultural_relationship("test_relationship", "person1")
        self.assertEqual(len(self.person.cultural_relationships), 1)

    def test_add_cultural_relationship_duplicate(self):
        """Test adding a duplicate cultural relationship to the Person, must raise a ValueError."""
        self.person.add_cultural_relationship("test_relationship", "person1")
        with self.assertRaises(ValueError):
            self.person.add_cultural_relationship("test_relationship", "person1")

    def test_remove_cultural_relationship(self):
        """Test removing a cultural relationship from the Person."""
        self.person.add_cultural_relationship("test_relationship", "person1")
        self.person.remove_cultural_relationship("test_relationship", "person1")
        self.assertEqual(len(self.person.cultural_relationships), 0)

    def test_remove_cultural_relationship_not_found(self):
        """Test removing a non-existent cultural relationship from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_cultural_relationship("test_relationship", "person1")

    def test_get_cultural_relationships(self):
        """Test getting cultural relationships from the Person."""
        self.person.add_cultural_relationship("test_relationship", "person1")
        self.assertEqual(self.person.get_cultural_relationships(), {"test_relationship": ["person1"]})

    def test_add_godparent(self):
        """Test adding a godparent to the Person."""
        self.person.add_godparent("godparent1")
        self.assertEqual(len(self.person.godparents), 1)

    def test_add_godparent_duplicate(self):
        """Test adding a duplicate godparent to the Person, must raise a ValueError."""
        self.person.add_godparent("godparent1")
        with self.assertRaises(ValueError):
            self.person.add_godparent("godparent1")

    def test_remove_godparent(self):
        """Test removing a godparent from the Person."""
        self.person.add_godparent("godparent1")
        self.person.remove_godparent("godparent1")
        self.assertEqual(len(self.person.godparents), 0)

    def test_remove_godparent_not_found(self):
        """Test removing a non-existent godparent from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_godparent("godparent1")

    def test_get_godparents(self):
        """Test getting godparents from the Person."""
        self.person.add_godparent("godparent1")
        self.assertEqual(self.person.get_godparents(), ["godparent1"])

    def test_add_foster_relationship(self):
        """Test adding a foster relationship to the Person."""
        self.person.add_foster_relationship("foster1")
        self.assertEqual(len(self.person.foster_relationships), 1)

    def test_add_foster_relationship_duplicate(self):
        """Test adding a duplicate foster relationship to the Person, must raise a ValueError."""
        self.person.add_foster_relationship("foster1")
        with self.assertRaises(ValueError):
            self.person.add_foster_relationship("foster1")

    def test_remove_foster_relationship(self):
        """Test removing a foster relationship from the Person."""
        self.person.add_foster_relationship("foster1")
        self.person.remove_foster_relationship("foster1")
        self.assertEqual(len(self.person.foster_relationships), 0)

    def test_remove_foster_relationship_not_found(self):
        """Test removing a non-existent foster relationship from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_foster_relationship("foster1")

    def test_get_foster_relationships(self):
        """Test getting foster relationships from the Person."""
        self.person.add_foster_relationship("foster1")
        self.assertEqual(self.person.get_foster_relationships(), ["foster1"])

    def test_add_guardian_relationship(self):
        """Test adding a guardian relationship to the Person."""
        self.person.add_guardian_relationship("guardian1")
        self.assertEqual(len(self.person.guardian_relationships), 1)

    def test_add_guardian_relationship_duplicate(self):
        """Test adding a duplicate guardian relationship to the Person, must raise a ValueError."""
        self.person.add_guardian_relationship("guardian1")
        with self.assertRaises(ValueError):
            self.person.add_guardian_relationship("guardian1")

    def test_remove_guardian_relationship(self):
        """Test removing a guardian relationship from the Person."""
        self.person.add_guardian_relationship("guardian1")
        self.person.remove_guardian_relationship("guardian1")
        self.assertEqual(len(self.person.guardian_relationships), 0)

    def test_remove_guardian_relationship_not_found(self):
        """Test removing a non-existent guardian relationship from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_guardian_relationship("guardian1")

    def test_get_guardian_relationships(self):
        """Test getting guardian relationships from the Person."""
        self.person.add_guardian_relationship("guardian1")
        self.assertEqual(self.person.get_guardian_relationships(), ["guardian1"])

    def test_add_tribal_clan_affiliation(self):
        """Test adding a tribal/clan affiliation to the Person."""
        self.person.add_tribal_clan_affiliation("test_clan")
        self.assertEqual(len(self.person.tribal_clan_affiliations), 1)

    def test_remove_tribal_clan_affiliation(self):
        """Test removing a tribal/clan affiliation from the Person."""
        self.person.add_tribal_clan_affiliation("test_clan")
        self.person.remove_tribal_clan_affiliation("test_clan")
        self.assertEqual(len(self.person.tribal_clan_affiliations), 0)

    def test_get_tribal_clan_affiliations(self):
        """Test getting tribal/clan affiliations from the Person."""
        self.person.add_tribal_clan_affiliation("test_clan")
        self.assertEqual(self.person.get_tribal_clan_affiliations(), ["test_clan"])

    def test_set_family_tree(self):
        """Test setting the family tree of the Person."""
        self.person.set_family_tree("test_family_tree")
        self.assertEqual(self.person.family_tree, "test_family_tree")

    def test_set_profile_photo(self):
        """Test setting the profile photo of the Person."""
        self.person.set_profile_photo("test_url")
        self.assertEqual(self.person.profile_photo, "test_url")

    def test_get_profile_photo(self):
        """Test getting the profile photo of the Person."""
        self.person.set_profile_photo("test_url")
        self.assertEqual(self.person.get_profile_photo(), "test_url")

    def test_add_document(self):
        """Test adding a document to the Person."""
        self.person.add_document("test_document")
        self.assertEqual(len(self.person.documents), 1)

    def test_remove_document(self):
        """Test removing a document from the Person."""
        self.person.add_document("test_document")
        self.person.remove_document("test_document")
        self.assertEqual(len(self.person.documents), 0)

    def test_remove_document_not_found(self):
        """Test removing a non-existent document from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_document("test_document")

    def test_get_documents(self):
        """Test getting documents from the Person."""
        self.person.add_document("test_document")
        self.assertEqual(self.person.get_documents(), ["test_document"])

    def test_add_media(self):
        """Test adding media to the Person."""
        self.person.add_media("test_media")
        self.assertEqual(len(self.person.media), 1)

    def test_add_military_service_record(self):
        """Test adding a military service record to the Person."""
        self.person.add_military_service_record("test_record")
        self.assertEqual(len(self.person.military_service_records), 1)

    def test_add_military_service_record_duplicate(self):
        """Test adding a duplicate military service record to the Person, must raise a ValueError."""
        self.person.add_military_service_record("test_record")
        with self.assertRaises(ValueError):
            self.person.add_military_service_record("test_record")
    
    def test_remove_military_service_record(self):
        """Test removing a military service record from the Person."""
        self.person.add_military_service_record("test_record")
        self.person.remove_military_service_record("test_record")
        self.assertEqual(len(self.person.military_service_records), 0)

    def test_remove_military_service_record_not_found(self):
        """Test removing a non-existent military service record from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_military_service_record("test_record")

    def test_get_military_service_records(self):
        """Test getting military service records from the Person."""
        self.person.add_military_service_record("test_record")
        self.assertEqual(self.person.get_military_service_records(), ["test_record"])

    def test_add_educational_history(self):
        """Test adding an educational history record to the Person."""
        self.person.add_educational_history("test_record")
        self.assertEqual(len(self.person.educational_history), 1)

    def test_add_educational_history_duplicate(self):
        """Test adding a duplicate educational history record to the Person, must raise a ValueError."""
        self.person.add_educational_history("test_record")
        with self.assertRaises(ValueError):
            self.person.add_educational_history("test_record")

    def test_remove_educational_history(self):
        """Test removing an educational history record from the Person."""
        self.person.add_educational_history("test_record")
        self.person.remove_educational_history("test_record")
        self.assertEqual(len(self.person.educational_history), 0)

    def test_remove_educational_history_not_found(self):
        """Test removing a non-existent educational history record from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_educational_history("test_record")

    def test_get_educational_history(self):
        """Test getting educational history records from the Person."""
        self.person.add_educational_history("test_record")
        self.assertEqual(self.person.get_educational_history(), ["test_record"])

    def test_add_occupational_history(self):
        """Test adding an occupational history record to the Person."""
        self.person.add_occupational_history("test_record")
        self.assertEqual(len(self.person.occupational_history), 1)

    def test_add_occupational_history_duplicate(self):
        """Test adding a duplicate occupational history record to the Person, must raise a ValueError."""
        self.person.add_occupational_history("test_record")
        with self.assertRaises(ValueError):
            self.person.add_occupational_history("test_record")

    def test_remove_occupational_history(self):
        """Test removing an occupational history record from the Person."""
        self.person.add_occupational_history("test_record")
        self.person.remove_occupational_history("test_record")
        self.assertEqual(len(self.person.occupational_history), 0)

    def test_remove_occupational_history_not_found(self):
        """Test removing a non-existent occupational history record from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_occupational_history("test_record")

    def test_get_occupational_history(self):
        """Test getting occupational history records from the Person."""
        self.person.add_occupational_history("test_record")
        self.assertEqual(self.person.get_occupational_history(), ["test_record"])

    def test_add_medical_history(self):
        """Test adding a medical history record to the Person."""
        self.person.add_medical_history("test_record")
        self.assertEqual(len(self.person.medical_history), 1)

    def test_add_medical_history_duplicate(self):
        """Test adding a duplicate medical history record to the Person, must raise a ValueError."""
        self.person.add_medical_history("test_record")
        with self.assertRaises(ValueError):
            self.person.add_medical_history("test_record")

    def test_remove_medical_history(self):
        """Test removing a medical history record from the Person."""
        self.person.add_medical_history("test_record")
        self.person.remove_medical_history("test_record")
        self.assertEqual(len(self.person.medical_history), 0)

    def test_remove_medical_history_not_found(self):
        """Test removing a non-existent medical history record from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_medical_history("test_record")

    def test_get_medical_history(self):
        """Test getting medical history records from the Person."""
        self.person.add_medical_history("test_record")
        self.assertEqual(self.person.get_medical_history(), ["test_record"])

    def test_set_dna_haplogroups(self):
        """Test setting DNA haplogroups of the Person."""
        self.person.set_dna_haplogroups(["test_haplogroup"])
        self.assertEqual(self.person.dna_haplogroups, ["test_haplogroup"])

    def test_get_dna_haplogroups(self):
        """Test getting DNA haplogroups of the Person."""
        self.person.set_dna_haplogroups(["test_haplogroup"])
        self.assertEqual(self.person.get_dna_haplogroups(), ["test_haplogroup"])

    def test_add_physical_characteristic(self):
        """Test adding a physical characteristic to the Person."""
        self.person.add_physical_characteristic("test_characteristic")
        self.assertEqual(len(self.person.physical_characteristics), 1)

    def test_add_physical_characteristic_duplicate(self):
        """Test adding a duplicate physical characteristic to the Person, must raise a ValueError."""
        self.person.add_physical_characteristic("test_characteristic")
        with self.assertRaises(ValueError):
            self.person.add_physical_characteristic("test_characteristic")

    def test_remove_physical_characteristic(self):
        """Test removing a physical characteristic from the Person."""
        self.person.add_physical_characteristic("test_characteristic")
        self.person.remove_physical_characteristic("test_characteristic")
        self.assertEqual(len(self.person.physical_characteristics), 0)

    def test_remove_physical_characteristic_not_found(self):
        """Test removing a non-existent physical characteristic from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_physical_characteristic("test_characteristic")

    def test_get_physical_characteristics(self):
        """Test getting physical characteristics from the Person."""
        self.person.add_physical_characteristic("test_characteristic")
        self.assertEqual(self.person.get_physical_characteristics(), ["test_characteristic"])

    def test_add_language_spoken(self):
        """Test adding a language spoken to the Person."""
        self.person.add_language_spoken("test_language")
        self.assertEqual(len(self.person.languages_spoken), 1)

    def test_add_language_spoken_duplicate(self):
        """Test adding a duplicate language spoken to the Person, must raise a ValueError."""
        self.person.add_language_spoken("test_language")
        with self.assertRaises(ValueError):
            self.person.add_language_spoken("test_language")

    def test_remove_language_spoken(self):
        """Test removing a language spoken from the Person."""
        self.person.add_language_spoken("test_language")
        self.person.remove_language_spoken("test_language")
        self.assertEqual(len(self.person.languages_spoken), 0)

    def test_remove_language_spoken_not_found(self):
        """Test removing a non-existent language spoken from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_language_spoken("test_language")

    def test_get_languages_spoken(self):
        """Test getting languages spoken from the Person."""
        self.person.add_language_spoken("test_language")
        self.assertEqual(self.person.get_languages_spoken(), ["test_language"])

    def test_add_historical_context_relationship(self):
        """Test adding a historical context relationship to the Person."""
        self.person.add_historical_context_relationship("test_relationship", "test_context")
        self.assertEqual(len(self.person.historical_context_relationships), 1)

    def test_remove_historical_context_relationship(self):
        """Test removing a historical context relationship from the Person."""
        self.person.add_historical_context_relationship("test_relationship", "test_context")
        self.person.remove_historical_context_relationship("test_relationship", "test_context")
        self.assertEqual(len(self.person.historical_context_relationships), 0)

    def test_remove_historical_context_relationship_type_not_found(self):
        """Test removing a non-existent historical context relationship type from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_historical_context_relationship("test_relationship", "test_context")

    def test_remove_historical_context_relationship_context_not_found(self):
        """Test removing a non-existent historical context from a relationship from the Person, must raise a ValueError."""
        self.person.add_historical_context_relationship("test_relationship", "test_context")
        with self.assertRaises(ValueError):
            self.person.remove_historical_context_relationship("test_relationship", "nonexistent_context")

    def test_get_historical_context_relationships(self):
        """Test getting historical context relationships from the Person."""
        self.person.add_historical_context_relationship("test_relationship", "test_context")
        self.assertEqual(self.person.get_historical_context_relationships(), {"test_relationship": ["test_context"]})

    def test_add_relationship_event(self):
        """Test adding a relationship event to the Person."""
        self.person.add_relationship_event("person1", "test_event", "2023-01-01")
        self.assertEqual(len(self.person.relationship_timeline), 1)

    def test_get_relationship_timeline(self):
        """Test getting the relationship timeline from the Person."""
        self.person.add_relationship_event("person1", "test_event", "2023-01-01")
        self.assertEqual(self.person.get_relationship_timeline(), {"person1": [{"event": "test_event", "date": "2023-01-01"}]})

    def test_add_custom_relationship(self):
        """Test adding a custom relationship to the Person."""
        self.person.add_custom_relationship("test_relationship", "person1")
        self.assertEqual(len(self.person.custom_relationships), 1)

    def test_add_custom_relationship_duplicate(self):
        """Test adding a duplicate custom relationship to the Person, must raise a ValueError."""
        self.person.add_custom_relationship("test_relationship", "person1")
        with self.assertRaises(ValueError):
            self.person.add_custom_relationship("test_relationship", "person1")

    def test_remove_custom_relationship(self):
        """Test removing a custom relationship from the Person."""
        self.person.add_custom_relationship("test_relationship", "person1")
        self.person.remove_custom_relationship("test_relationship", "person1")
        self.assertEqual(len(self.person.custom_relationships), 0)

    def test_remove_custom_relationship_not_found(self):
        """Test removing a non-existent custom relationship from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_custom_relationship("test_relationship", "person1")
    
    def test_remove_custom_relationship_person_not_found(self):
        """Test removing a non-existent person from a custom relationship from the Person, must raise a ValueError."""
        self.person.add_custom_relationship("test_relationship", "person1")
        with self.assertRaises(ValueError):
            self.person.remove_custom_relationship("test_relationship", "person2")

    def test_get_custom_relationships(self):
        """Test getting custom relationships from the Person."""
        self.person.add_custom_relationship("test_relationship", "person1")
        self.assertEqual(self.person.get_custom_relationships(), {"test_relationship": ["person1"]})

    def test_add_immigration_naturalization_record(self):
        """Test adding an immigration/naturalization record to the Person."""
        self.person.add_immigration_naturalization_record("test_record")
        self.assertEqual(len(self.person.immigration_naturalization_records), 1)

    def test_add_immigration_naturalization_record_duplicate(self):
        """Test adding a duplicate immigration/naturalization record to the Person, must raise a ValueError."""
        self.person.add_immigration_naturalization_record("test_record")
        with self.assertRaises(ValueError):
            self.person.add_immigration_naturalization_record("test_record")

    def test_remove_immigration_naturalization_record(self):
        """Test removing an immigration/naturalization record from the Person."""
        self.person.add_immigration_naturalization_record("test_record")
        self.person.remove_immigration_naturalization_record("test_record")
        self.assertEqual(len(self.person.immigration_naturalization_records), 0)

    def test_remove_immigration_naturalization_record_not_found(self):
        """Test removing a non-existent immigration/naturalization record from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_immigration_naturalization_record("test_record")

    def test_get_immigration_naturalization_records(self):
        """Test getting immigration/naturalization records from the Person."""
        self.person.add_immigration_naturalization_record("test_record")
        self.assertEqual(self.person.get_immigration_naturalization_records(), ["test_record"])

    def test_set_privacy_setting(self):
        """Test setting a privacy setting."""
        self.person.set_privacy_setting("names", "private")
        self.assertEqual(self.person.privacy_settings["names"], "private")
    
    def test_get_privacy_setting(self):
        """Test getting a privacy setting."""
        self.person.set_privacy_setting("names", "private")
        self.assertEqual(self.person.get_privacy_setting("names"), "private")

    def test_data_encryption(self):
        """Test if data encryption is working."""
        # Add some data to the attributes
        self.person.biography = "Test biography"
        self.person.add_medical_history("test_medical_history")
        self.person.add_physical_characteristic("test_physical_characteristic")
        self.person.set_dna_haplogroups(["test_haplogroup"])
        self.person.add_immigration_naturalization_record("test_record")
        self.person.add_document("test_document")
        self.person.add_media("test_media")

        # Check that the data is encrypted
        self.assertNotEqual(self.person.biography, "Test biography")
        self.assertNotEqual(self.person.medical_history, ["test_medical_history"])
        self.assertNotEqual(self.person.physical_characteristics, ["test_physical_characteristic"])
        self.assertNotEqual(self.person.dna_haplogroups, ["test_haplogroup"])
        self.assertNotEqual(self.person.immigration_naturalization_records, ["test_record"])
        self.assertNotEqual(self.person.documents, ["test_document"])
        self.assertNotEqual(self.person.media, ["test_media"])

        # Get the info of the person
        person_info = self.person.get_person_info()

        # Check that the data is decrypted in the person_info
        self.assertEqual(person_info["biography"], "Test biography")
        self.assertEqual(person_info["medical_history"], ["test_medical_history"])
        self.assertEqual(person_info["physical_characteristics"], ["test_physical_characteristic"])
        self.assertEqual(person_info["dna_haplogroups"], ["test_haplogroup"])
        self.assertEqual(person_info["immigration_naturalization_records"], ["test_record"])
        self.assertEqual(person_info["documents"], ["test_document"])
        self.assertEqual(person_info["media"], ["test_media"])


if __name__ == "__main__":
    unittest.main()