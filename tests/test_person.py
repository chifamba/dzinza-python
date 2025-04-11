import unittest
from src.person import Person

class TestPerson(unittest.TestCase):
    def setUp(self):
        """Set up a Person object and a DataEncryptor object for testing."""
        self.encryption_key = "test_encryption_key"
        self.person = Person(
            person_id="test_person",
            user_id="test_user",
            first_name="Test",
            last_name="Person",
            date_of_birth="1990-01-01",
            place_of_birth="Test Place",
        )
        self.person.physical_characteristics = []
        self.person.custom_relationships = {}
        self.person.historical_context_relationships = {}


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
            self.person.add_cultural_relationship(
                "test_relationship", "person1")

    def test_remove_cultural_relationship_not_found(self):
        """Test removing a non-existent cultural relationship from the Person, must raise a ValueError."""
        with self.assertRaises(ValueError):
            self.person.remove_cultural_relationship("test_relationship", "person1")

    def test_get_cultural_relationships(self):
        """Test getting cultural relationships from the Person."""
        self.person.add_cultural_relationship(
            "test_relationship", "person1")
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
        self.assertEqual(
            self.person.get_relationship_timeline(), 
            {
                "person1": [{"event": "test_event", "date": "2023-01-01"}]
            }
        )

    def test_add_custom_relationship(self):
        """Test adding a custom relationship to the Person."""
        self.person.add_custom_relationship("test_relationship", "person1")
        self.assertEqual(len(self.person.custom_relationships), 1)

    def test_add_custom_relationship_duplicate(self):
        """Test adding a duplicate custom relationship to the Person, must raise a ValueError."""
        self.person.add_custom_relationship("test_relationship", "person1")
        with self.assertRaises(ValueError):
            self.person.add_custom_relationship("test_relationship", "person1")

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
        self.person.add_custom_relationship(
            "test_relationship", "person1")
        self.assertEqual(self.person.get_custom_relationships(),
                         {"test_relationship": ["person1"]})





    def test_set_privacy_setting(self):
        """Test setting a privacy setting."""
        self.person.set_privacy_setting("names", "private")
        self.assertEqual(self.person.privacy_settings["names"], "private")
    
    def test_get_privacy_setting(self):
        """Test getting a privacy setting."""
        self.person.set_privacy_setting("names", "private")
        self.assertEqual(self.person.get_privacy_setting("names"), "private")

if __name__ == "__main__":
    unittest.main()