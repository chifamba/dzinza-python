from src.person import Person
from src.relationship import Relationship
import os
import gedcom
import csv
import json
import xml.etree.ElementTree as ET
from gedcom.element.element import Element
from gedcom.parser import Parser
class FamilyTree:
    def __init__(self, root_person: Person = None):
        """
        Initializes the FamilyTree with an optional root person.

        Args:
            root_person (Person, optional): The root person of the family tree. Defaults to None.

        Attributes:
            root_person (Person): The root person of the family tree.
            person_nodes (dict): A dictionary to store each person's node information, keyed by user_id.
                Each node contains:
                    - person (Person): The Person object.
                    - parents (list): A list of parent Person objects.
                    - children (list): A list of child Person objects.
        """
        self.root_person = root_person
        self.person_nodes = {}
        if root_person:
            self.person_nodes[root_person.user_id] = {"person": root_person, "parent": None, "children": []}

    def add_person(self, person: Person, parents: list[Person] = None):
        if not self.root_person and parents:
            raise ValueError("Cannot add a person with parents if the tree is empty")        
        if person.user_id in self.person_nodes:
            raise ValueError("Person already exists in the family tree")

        if parents:
            for parent in parents:
                if parent.user_id not in self.person_nodes:
                    raise ValueError(f"Parent with ID {parent.user_id} not found in the family tree")

        if not self.root_person and not parents:
             self.root_person = person
        elif self.root_person and not parents:
            raise ValueError("Cannot add a root person if the tree already has a root")

        self.person_nodes[person.user_id] = {"person": person, "parents": parents or [], "children": []}

        if parents:
            for parent in parents:
                self.person_nodes[parent.user_id]["children"].append(person)

    def link_persons(self, person1_id, person2_id, relationship_type):
        person1 = self.get_person_by_id(person1_id)
        person2 = self.get_person_by_id(person2_id)

        if not person1 or not person2:
            raise ValueError("One or both persons not found in the family tree")
        
        if relationship_type == 'parent':
            person2.add_parent(person1_id)
            person1.add_child(person2_id)
        elif relationship_type == 'child':
            person1.add_parent(person2_id)
            person2.add_child(person1_id)


    def add_relationship(self, relationship: Relationship):
        person1 = relationship.person1
        person2 = relationship.person2

        if person1.user_id not in self.person_nodes or person2.user_id not in self.person_nodes:
            raise ValueError("One or both persons are not in the family tree")

        person1.add_relationship(relationship)
        person2.add_relationship(relationship)

    def get_person(self, person_id: int):
        person_data = self.person_nodes.get(person_id)
        return person_data["person"] if person_data else None
    
    def get_person_by_id(self, person_id: int):
        person_data = self.person_nodes.get(person_id)
        return person_data["person"] if person_data else None
    
    def display_tree(self, person_id=None, indent=0):
        """
        Displays the family tree in a hierarchical view, starting from the specified person or the root.

        Args:
            person_id (int, optional): The ID of the person to start displaying the tree from. 
                                        If None, starts from the root person. Defaults to None.
            indent (int, optional): The current indentation level for hierarchical display. Defaults to 0.
        """
        if person_id is None:
            if self.root_person is None:
                print("The family tree is empty.")
                return
            person_id = self.root_person.user_id

        person_data = self.person_nodes.get(person_id)
        if not person_data:
            return

        person = person_data["person"]
        print("  " * indent + f"ID: {person.user_id}, Name: {person.get_names()}")
        
        for child_person in person.get_children(self):
            self.display_tree(child_person.user_id, indent + 1)

    def import_gedcom(self, gedcom_file_path):
        """
        Imports data from a GEDCOM file, adding persons and relationships to the family tree.

        Args:
            gedcom_file_path (str): The path to the GEDCOM file.

        Raises:
            ImportError: If the `gedcom` library is not installed.
            ValueError: If the provided file is not a GEDCOM file or if there's an issue parsing the GEDCOM data.
        """
        if not os.path.exists(gedcom_file_path):
            raise FileNotFoundError(f"File not found: {gedcom_file_path}")
        
        try:
            import gedcom
        except ImportError:
            raise ImportError("The 'gedcom' library is required to parse GEDCOM files. Please install it.")

        if not gedcom_file_path.lower().endswith(".ged"):
            raise ValueError("The file is not a GEDCOM file (.ged)")

        try:
            with open(gedcom_file_path, 'r', encoding="utf-8") as ged_file:
                gedcom_data = gedcom.parse(ged_file)

                for record in gedcom_data:
                    if record.tag == 'INDI':
                        person_id = record.xref_id.replace("@", "")
                        first_name = ""
                        last_name = ""
                        for subrecord in record.sub_records:
                            if subrecord.tag == "NAME":
                                name_parts = subrecord.value.split("/")
                                if len(name_parts) >= 2:
                                    first_name = name_parts[0].strip()
                                    last_name = name_parts[1].strip()
                        person = Person(person_id, first_name, last_name, None, None)
                        self.add_person(person)
        except Exception as e:
            raise ValueError(f"Error parsing GEDCOM file: {e}")

    def export_gedcom(self, file_path:str):
        """
        Exports the family tree data to a GEDCOM file.

        Args:
            file_path (str): The path to save the GEDCOM file.

        Raises:
            ImportError: If the `gedcom` library is not installed.
            ValueError: If the file format is incorrect or if there's an issue creating the GEDCOM data.
        """
        if not file_path.lower().endswith(".ged"):
            raise ValueError("The file format is not .ged")

        try:
            gedcom_file = open(file_path, "w", encoding="utf-8")
        except ImportError:
            raise ImportError("The 'gedcom' library is required to export GEDCOM files. Please install it.")
        
        gedcom_file.write("0 HEAD\n")
        gedcom_file.write("1 SOUR Dzinza\n")
        gedcom_file.write("1 GEDC\n")
        gedcom_file.write("2 VERS 5.5.5\n")
        gedcom_file.write("2 FORM LINEAGE-LINKED\n")
        
        for user_id, node in self.person_nodes.items():
            person: Person = node["person"]
            gedcom_file.write(f"0 @{person.user_id}@ INDI\n")
            gedcom_file.write(f"1 NAME {person.get_names()[0].get('name', '')} /{person.get_names()[1].get('name', '')}/\n")
            gedcom_file.write(f"2 GIVN {person.get_names()[0].get('name', '')}\n")
            gedcom_file.write(f"2 SURN {person.get_names()[1].get('name', '')}\n")
            gedcom_file.write(f"1 SEX {person.gender or 'U'}\n")            
            gedcom_file.write(f"1 BIRT\n")
        gedcom_file.write("0 TRLR\n")
        gedcom_file.close()

    def import_json(self, file_path):
        """
        Imports family tree data from a JSON file.

        Args:
            file_path (str): The path to the JSON file.

        Raises:
            ImportError: If the `json` library is not available.
            ValueError: If the file format is not JSON or if there are issues with the JSON data.
        """
        if not file_path.lower().endswith(".json"):
            raise ValueError("File is not a JSON file")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON format")
        except ImportError:
            raise ImportError("The 'json' library is required to work with JSON files. Please install it.")
        
        for person_data in data.get("persons", []):
            person_id = person_data.get("person_id")
            first_name = person_data.get("first_name")
            last_name = person_data.get("last_name")
            date_of_birth = person_data.get("date_of_birth")
            place_of_birth = person_data.get("place_of_birth")
            
            if not person_id or not first_name or not last_name:
                raise ValueError("Missing required fields for person")

            person = Person(person_id, first_name, last_name, date_of_birth, place_of_birth)
            person.names = person_data.get("names", [])
            person.gender = person_data.get("gender")
            person.romanization = person_data.get("romanization")
            person.transliteration = person_data.get("transliteration")
            person.religious_affiliations = person_data.get("religious_affiliations", [])
            person.current_location = person_data.get("current_location")
            person.privacy_settings = person_data.get("privacy_settings")
            person.biography = person_data.get("biography", "")
            person.date_of_death = person_data.get("date_of_death")
            person.place_of_death = person_data.get("place_of_death")
            person.profile_photo = person_data.get("profile_photo")
            person.relationships = person_data.get("relationships", {})
            person.documents = person_data.get("documents", [])
            person.media = person_data.get("media", [])
            person.military_service_records = person_data.get("military_service_records", [])
            person.educational_history = person_data.get("educational_history", [])
            person.occupational_history = person_data.get("occupational_history", [])
            person.medical_history = person_data.get("medical_history", [])
            person.dna_haplogroups = person_data.get("dna_haplogroups", [])
            person.physical_characteristics = person_data.get("physical_characteristics", [])
            person.languages_spoken = person_data.get("languages_spoken", [])
            person.immigration_naturalization_records = person_data.get("immigration_naturalization_records", [])
            self.add_person(person)

    def export_json(self, file_path):
        """
        Exports the family tree data to a JSON file.

        Args:
            file_path (str): The path to save the JSON file.

        Raises:
            ImportError: If the `json` library is not available.
            ValueError: If the file format is incorrect or if there's an issue creating the JSON data.
        """
        if not file_path.lower().endswith(".json"):
            raise ValueError("The file format is not .json")
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                
                data = {"persons": []}
                for person_id, node in self.person_nodes.items():
                    person: Person = node["person"]
                    person_data = {
                        "person_id": person.user_id,
                        "first_name": person.get_names()[0].get("name"),
                        "last_name": person.get_names()[1].get("name"),
                        "names": person.names,
                        "gender": person.gender,
                        "romanization": person.romanization,
                        "transliteration": person.transliteration,
                        "religious_affiliations": person.religious_affiliations,
                        "current_location": person.current_location,
                        "privacy_settings": person.privacy_settings,
                        "biography": person.biography,
                        "date_of_birth": person.date_of_birth,
                        "place_of_birth": person.place_of_birth,
                        "date_of_death": person.date_of_death,
                        "place_of_death": person.place_of_death,
                        "profile_photo": person.profile_photo,
                        "relationships": person.relationships,
                        "documents": person.documents,
                        "media": person.media,
                        "military_service_records": person.military_service_records,
                        "educational_history": person.educational_history,
                        "occupational_history": person.occupational_history,
                        "medical_history": person.medical_history,
                        "dna_haplogroups": person.dna_haplogroups,
                        "physical_characteristics": person.physical_characteristics,
                        "languages_spoken": person.languages_spoken,
                        "immigration_naturalization_records": person.immigration_naturalization_records,
                    }
                    data["persons"].append(person_data)
                json.dump(data, file, indent=4, ensure_ascii=False)
        except ImportError:
            raise ImportError("The 'json' library is required to export JSON files. Please install it.")
    
    def import_csv(self, file_path):
        """
        Imports family tree data from a CSV file.
        Args:
            file_path (str): The path to the CSV file.
        Raises:
            ImportError: If the `csv` library is not available.
            ValueError: If the file format is not CSV or if there are issues with the CSV data.
        """
        if not file_path.lower().endswith(".csv"):
            raise ValueError("File is not a CSV file")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    person_id = row.get("person_id")
                    first_name = row.get("first_name")
                    last_name = row.get("last_name")
                    date_of_birth = row.get("date_of_birth")
                    place_of_birth = row.get("place_of_birth")

                    if not person_id or not first_name or not last_name:
                        raise ValueError("Missing required fields for person")

                    person = Person(person_id, first_name, last_name, date_of_birth, place_of_birth)
                    self.add_person(person)
        except ImportError:
            raise ImportError("The 'csv' library is required to work with CSV files. Please install it.")

    def export_csv(self, file_path):
        """
        Exports the family tree data to a CSV file.
        Args:
            file_path (str): The path to save the CSV file.
        Raises:
            ImportError: If the `csv` library is not available.
            ValueError: If the file format is not CSV or if there are issues creating the CSV data.
        """
        if not file_path.lower().endswith(".csv"):
            raise ValueError("File is not a CSV file")
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as file:
                fieldnames = ["person_id", "first_name", "last_name", "date_of_birth", "place_of_birth"]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for person_id, node in self.person_nodes.items():
                    person: Person = node["person"]
                    writer.writerow({
                        "person_id": person.user_id,
                        "first_name": person.get_names()[0].get("name"),
                        "last_name": person.get_names()[1].get("name"),
                        "date_of_birth": person.date_of_birth,
                        "place_of_birth": person.place_of_birth,
                    })
        except ImportError:
            raise ImportError("The 'csv' library is required to work with CSV files. Please install it.")

    def import_xml(self, file_path):
        """Imports family tree data from an XML file."""
        if not file_path.lower().endswith(".xml"):
            raise ValueError("File is not an XML file")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            for person_elem in root.findall("person"):
                person_id = person_elem.get("person_id")
                first_name = person_elem.get("first_name")
                last_name = person_elem.get("last_name")
                date_of_birth = person_elem.get("date_of_birth")
                place_of_birth = person_elem.get("place_of_birth")
                person = Person(person_id, first_name, last_name, date_of_birth, place_of_birth)
                self.add_person(person)
        except ImportError:
            raise ImportError("The 'xml.etree.ElementTree' library is required to work with XML files. Please install it.")
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}")

    def export_xml(self, file_path):
        """Exports the family tree data to an XML file."""
        if not file_path.lower().endswith(".xml"):
            raise ValueError("File is not an XML file")
        try:
            root = ET.Element("family_tree")
            for _, node in self.person_nodes.items():
                person = node["person"]
                person_elem = ET.SubElement(root, "person", person_id=person.user_id, first_name=person.get_names()[0].get("name"), last_name=person.get_names()[1].get("name"), date_of_birth=person.date_of_birth, place_of_birth=person.place_of_birth)
            tree = ET.ElementTree(root)
            tree.write(file_path, encoding="utf-8", xml_declaration=True)
        except ImportError:
            raise ImportError("The 'json' library is required to export JSON files. Please install it.")
    

