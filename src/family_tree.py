from src.person import Person
from src.relationship import Relationship
from src.encryption import DataEncryptor
from urllib.parse import urlparse
import os
import gedcom
import csv
import json
import xml.etree.ElementTree as ET
from gedcom.element.element import Element
from gedcom.parser import Parser
from datetime import datetime


class FamilyTree:
    def __init__(self, root_person: Person = None, encryption_key:str="default_key"):
        
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
        self.encryption_key = encryption_key
        self.data_encryptor = DataEncryptor()
        self.person_nodes = {}
        if root_person:
            self.person_nodes[root_person.user_id] = {"person": root_person, "parent": None, "children": []}

    def add_person(self, person: Person, parents: list[Person] = None):
        """
        Adds a person to the family tree.
        
        """

        

        errors = self.validate_person_data(person)
        if errors:
            raise ValueError(f"Invalid person data: {', '.join(errors)}")

                
        if person.user_id in self.person_nodes:
            raise ValueError("Person already exists in the family tree")

        
        if not self.root_person and not parents:
            self.root_person = person
        elif self.root_person and not parents and len(self.person_nodes) > 0:
            raise ValueError("Cannot add a root person if the tree already has a root")
        elif not self.root_person and parents:
            raise ValueError("Cannot add a person with parents if the tree is empty")

        self.person_nodes[person.user_id] = {"person": person, "relationships": []}
        if parents:
            for parent in parents:
                self.link_persons(Relationship(person.user_id, parent.user_id, "child"))
                
        if parents and self.person_nodes.get(parent.user_id):
            for parent in parents:
                self.person_nodes[parent.user_id]["children"].append(person)
        
        relationship_errors = self.check_relationship_consistency(person.user_id)
        if relationship_errors:
            raise ValueError(f"Invalid relationships data: {', '.join(relationship_errors)}")



    def validate_person_data(self, person: Person):
        """Validate the person data."""
        errors = []
        if not person.get_names():
            errors.append("Names cannot be empty")
        if not isinstance(person.date_of_birth, datetime):
            errors.append("Date of birth is not valid")
        if person.date_of_death and (not isinstance(person.date_of_death, datetime) ):
            try:
                person.date_of_death = datetime.strptime(person.date_of_death, "%Y-%m-%d %H:%M:%S")
            except:
            errors.append("Date of death is not valid")
        if person.profile_photo and not urlparse(person.profile_photo).scheme:
            errors.append("Profile photo is not a valid URL")
        if any(doc and not urlparse(doc).scheme for doc in person.documents):
            errors.append("One or more documents are not valid URLs")
        if any(media and not urlparse(media).scheme for media in person.media):
            errors.append("One or more media entries are not valid URLs")
        if not person.biography:
            errors.append("Biography cannot be empty")
        if person.gender not in ["male", "female", None]:
            errors.append("Gender must be male or female")
        return errors


    def link_persons(self, relationship: Relationship):
        person1 = self.get_person_by_id(relationship.person1_id)
        person2 = self.get_person_by_id(relationship.person2_id)

        if not person1 or not person2:
            raise ValueError("One or both persons not found in the family tree")
        
        person1.add_relationship(relationship)
        person2.add_relationship(relationship)
        
        relationship_errors = self.check_relationship_consistency(person1_id)
        relationship_errors += self.check_relationship_consistency(person2_id)
        if relationship_errors:
            raise ValueError(f"Invalid relationships data: {', '.join(relationship_errors)}")


    def add_relationship(self, relationship: Relationship):
        person1 = relationship.person1
        person2 = relationship.person2

        if person1.user_id not in self.person_nodes or person2.user_id not in self.person_nodes:
            raise ValueError("One or both persons are not in the family tree")

        relationship_errors = self.check_relationship_consistency(person1.user_id)
        relationship_errors += self.check_relationship_consistency(person2.user_id)
        if relationship_errors:
            raise ValueError(f"Invalid relationships data: {', '.join(relationship_errors)}")

        person1.add_relationship(relationship)
        person2.add_relationship(relationship)


    def check_relationship_consistency(self, person_id: str):
        errors = []
        person = self.get_person_by_id(person_id)
        if not person:
            raise ValueError(f"Person with ID {person_id} not found")
        
        # Check Parents
        for parent_id in person.relationships.get("parent", []):
            for rel in person.relationships:
                if rel.relationship_type == "parent":
                    parent = self.get_person_by_id(rel.person2_id)
                    if not parent or not any(r.person1_id == person_id and r.relationship_type == "child" for r in parent.relationships):
                        errors.append(f"Inconsistent parent relationship with parent {parent.user_id}")

            # Check Children
            for rel in person.relationships:
                if rel.relationship_type == "child":
                    child = self.get_person_by_id(rel.person1_id)                        
                    if not child or not any(r.person2_id == person_id and r.relationship_type == "parent" for r in child.relationships):
                        errors.append(f"Inconsistent child relationship with child {child.user_id}")                
            # Check Spouses
            for rel in person.relationships:
                if rel.relationship_type == "spouse":
                    spouse = self.get_person_by_id(rel.person1_id)
                    if not spouse or rel.person2_id not in spouse.relationships.get("spouse", []):
                        errors.append(f"Inconsistent spouse relationship with spouse {spouse.user_id}")

            # Check Siblings
            for rel in person.relationships:
                if rel.relationship_type == "sibling" and rel.person1_id != person_id:
                    sibling = self.get_person_by_id(rel.person1_id)
                    if not sibling:
                        errors.append(f"Inconsistent sibling relationship with sibling {sibling.user_id}")
                    else:
                        person_parents = set(r.person2_id for r in person.relationships if r.relationship_type == "parent")
                        sibling_parents = set(r.person2_id for r in sibling.relationships if r.relationship_type == "parent")
                        if not person_parents.intersection(sibling_parents) or len(person_parents.intersection(sibling_parents)) == 0:
                            errors.append(f"Inconsistent sibling relationship with sibling {sibling.user_id}: Different parents")
        return errors
    def get_person(self, person_id: int):
        person_data = self.person_nodes.get(person_id)
        return person_data["person"] if person_data else None
    
    def check_all_relationship_consistency(self):
        errors = []
        for person_id in self.person_nodes.keys():
            errors.extend(self.check_relationship_consistency(person_id))
        return errors




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
        
        for rel in person.relationships:
            if rel.relationship_type == "child":
                self.display_tree(rel.person1_id, indent + 1)



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

                persons = {}
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
                        birth_date = None
                        birth_place = None
                        for subrecord in record.sub_records:
                            if subrecord.tag == "BIRT":
                                for sub_subrecord in subrecord.sub_records:
                                    if sub_subrecord.tag == "DATE":
                                        birth_date = sub_subrecord.value
                                    if sub_subrecord.tag == "PLAC":
                                        birth_place = sub_subrecord.value

                        person = Person(person_id, first_name, last_name, birth_date, birth_place)
                        self.add_person(person)                        
                        persons[person_id] = person

                    elif record.tag == 'FAM':
                        husband = ""
                        wife = ""
                        children = []
                        for subrecord in record.sub_records:
                            if subrecord.tag == 'HUSB':
                                husband = subrecord.value.replace("@", "")
                            if subrecord.tag == 'WIFE':
                                wife = subrecord.value.replace("@", "")
                            if subrecord.tag == 'CHIL':
                                children.append(subrecord.value.replace("@", ""))

                        if husband and wife and persons.get(husband) and persons.get(wife):
                            self.link_persons(Relationship(husband, wife, "spouse"))                            
                        for child in children:                            
                            if persons.get(child) and persons.get(husband) and persons.get(wife):
                                
                            self.link_persons(Relationship(child, husband, "child"))
                            self.link_persons(Relationship(child, wife, "child"))
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
                    encrypted_data = json.load(file)
                    decrypted_data = self.data_encryptor.decrypt_data(encrypted_data["data"], self.encryption_key)
                    data = json.loads(decrypted_data)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON format")
        except ImportError:
            raise ImportError("The 'json' library is required to work with JSON files. Please install it.")
        except ValueError as e:
            raise ValueError(f"Error decrypting data: {e}")
        





        for person_data in data.get("persons", []):
            

            if "encryption_key" in person_data:
                person_data.pop("encryption_key")

            person_id = person_data.get("person_id")
            first_name = person_data.get("first_name")
            last_name = person_data.get("last_name")
            date_of_birth = person_data.get("date_of_birth")
            place_of_birth = person_data.get("place_of_birth")
            
            if not person_id or not first_name or not last_name:
                raise ValueError("Missing required fields for person")

            if not person_id or not first_name or not last_name:
                raise ValueError("Missing required fields for person")

            person = Person(person_id, first_name, last_name, date_of_birth, place_of_birth)
            
            person_names = person_data.get("names", [])
            person.names = person_names
            
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

            errors = self.validate_person_data(person)
            if errors:
                raise ValueError(f"Invalid person data in {person_id}: {', '.join(errors)}")
            for rel in person.relationships:
                rel_obj = Relationship(rel["person1_id"], rel["person2_id"], rel["relationship_type"])
                self.link_persons(rel_obj)

            
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
                persons_data = []
                for person_id, node in self.person_nodes.items():
                    person: Person = node["person"]

                    # Get person information
                    person_info = person.get_person_info()

                    person_data = {
                    "person_id": person_info["person_id"],
                    "first_name": person_info["names"][0]["name"],
                    "last_name": person_info["names"][1]["name"],
                    "names": person_info["names"],
                    "gender": person_info["gender"],
                    "romanization": person_info["romanization"],
                    "transliteration": person_info["transliteration"],
                    "religious_affiliations": person_info["religious_affiliations"],
                    "current_location": person_info["current_location"],
                    "privacy_settings": person_info["privacy_settings"],
                    "biography": person_info["biography"],
                    "date_of_birth": person_info["date_of_birth"],
                    "place_of_birth": person_info["place_of_birth"],
                    "date_of_death": person_info["date_of_death"],
                    "place_of_death": person_info["place_of_death"],
                    "profile_photo": person_info["profile_photo"],
                    "relationships": person_info["relationships"],
                    "documents": person_info["documents"],
                    "media": person_info["media"],
                    "military_service_records": person_info["military_service_records"],
                    "educational_history": person_info["educational_history"],
                    "occupational_history": person_info["occupational_history"],
                    "medical_history": person_info["medical_history"],
                    "dna_haplogroups": person_info["dna_haplogroups"],
                    "physical_characteristics": person_info["physical_characteristics"],
                    "languages_spoken": person_info["languages_spoken"],
                    "immigration_naturalization_records": person_info["immigration_naturalization_records"]
                }
                    persons_data.append(person_data)
                data_to_encrypt = {"persons": persons_data}
                json_data = json.dumps(data_to_encrypt)
                
                encrypted_data = self.data_encryptor.encrypt_data(json_data, self.encryption_key)

                json.dump({"data": encrypted_data}, file, indent=4, ensure_ascii=False)
                

        except ImportError:
            raise ImportError("The 'json' library is required to export JSON files. Please install it.")
    
    def find_duplicates(self):
        """
        Finds and returns a list of lists containing possible duplicate persons in the family tree.
        
        Duplicates are determined by comparing names, date of birth, and place of birth.

        Returns:
            list: A list of lists, where each inner list contains potential duplicate Person objects.
        """
        duplicates = []
        checked_pairs = set()

        for id1, node1 in self.person_nodes.items():
            for id2, node2 in self.person_nodes.items():
                if id1 != id2 and (id1, id2) not in checked_pairs and (id2, id1) not in checked_pairs:
                    person1:Person = node1["person"]
                    person2:Person = node2["person"]
                    checked_pairs.add((id1, id2))
                    
                    name1 = person1.get_names()
                    name2 = person2.get_names()
                    
                    if not name1 or not name2:
                        continue
                    if person1.date_of_birth == person2.date_of_birth and person1.place_of_birth == person2.place_of_birth:
                         if name1[0].get("name") == name2[0].get("name") and name1[1].get("name") == name2[1].get("name"):
                            duplicates.append([person1, person2])

        return duplicates
    
    def merge_persons(self, person1: Person, person2: Person):
        """Merges the data of person2 into person1 and removes person2 from the tree."""
        if person1.user_id not in self.person_nodes or person2.user_id not in self.person_nodes:
            raise ValueError("One of the persons not found")

        person1.names = person2.names
        person1.gender = person2.gender
        person1.romanization = person2.romanization
        person1.transliteration = person2.transliteration
        person1.religious_affiliations = person2.religious_affiliations
        person1.profile_photo = person2.profile_photo
        person1.relationships = person2.relationships

        for relationship in person2.relationships:
            if relationship.person1_id != person1.user_id:
                self.link_persons(relationship)
                
        self.person_nodes.pop(person2.user_id)

    def check_all_relationship_consistency(self):
        errors = []
        for person_id in self.person_nodes.keys():
            errors.extend(self.check_relationship_consistency(person_id))
        return errors
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

                    errors = self.validate_person_data(person)
                    if errors:
                        raise ValueError(f"Invalid person data: {', '.join(errors)}")

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
                
                errors = self.validate_person_data(person)
                if errors:
                    raise ValueError(f"Invalid person data: {', '.join(errors)}")

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
    

    def generate_family_tree_report(self):
        """
        Generates a text-based report of the family tree.

        Returns:
            str: A string containing the family tree report.
        """
        report = "Family Tree Report:\n\n"
        
        def build_tree_string(person_id=None, indent=0):
            tree_string = ""
            if person_id is None:
                if self.root_person is None:
                    return "The family tree is empty."
                person_id = self.root_person.user_id

            person_data = self.person_nodes.get(person_id)
            if not person_data:
                return ""

            person = person_data["person"]
            tree_string += "  " * indent + f"ID: {person.user_id}, Name: {person.get_names()}\n"
            
            for rel in person.relationships:
                if rel.relationship_type == "child":
                    tree_string += build_tree_string(rel.person1_id, indent + 1)
            return tree_string

        report += build_tree_string()
        return report

    def search_person(self, query: str, fields: list[str]):
        """
        Searches for persons in the family tree that match the given query in the specified fields.

        Args:
            query (str): The query string to search for.
            fields (list[str]): A list of fields (attributes of the Person class) to search within.

        Returns:
            list[Person]: A list of Person objects that match the query in the specified fields.
        """
        results = []
        for node in self.person_nodes.values():
            person:Person = node["person"]
            if any(query.lower() in str(getattr(person, field, "")).lower() for field in fields):
                results.append(person)
        return results
    def generate_person_summary_report(self, person_id):
        """Generates a summary report for a specific person."""
        person = self.get_person_by_id(person_id)
        if not person:
            raise ValueError("Person not found")
        return f"""
        Person Summary Report for ID: {person_id}
        Name: {person.get_names()}
        Date of Birth: {person.date_of_birth}
        """


