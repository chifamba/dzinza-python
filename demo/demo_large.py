import requests
import random
import json
import time
from datetime import datetime, timedelta, date

# --- Configuration ---
API_BASE_URL = "http://localhost:8090/api"  # Adjust if your API runs elsewhere
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "01Admin_2025"  # As specified in the request

# --- Synthetic Data Generation ---
MALE_FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard",
    "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew",
    "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua"
]

FEMALE_FIRST_NAMES = [
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
    "Jessica", "Sarah", "Karen", "Nancy", "Margaret", "Lisa", "Betty",
    "Sandra", "Ashley", "Kimberly", "Emily", "Donna", "Michelle"
]

LAST_NAMES = [
    "Smith", "Jones", "Williams", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
    "Martin", "Thompson", "Garcia", "Martinez", "Robinson", "Clark",
    "Rodriguez", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young",
    "King", "Wright", "Scott"
]

def get_random_name(gender):
    """Generates a random first name based on gender."""
    if gender == "male":
        return random.choice(MALE_FIRST_NAMES)
    return random.choice(FEMALE_FIRST_NAMES)

def get_random_last_name():
    """Generates a random last name."""
    return random.choice(LAST_NAMES)

def generate_birth_date(start_year, end_year=None):
    """Generates a random birth date within a given year or range."""
    year = random.randint(start_year, end_year) if end_year else start_year
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Keep it simple for days
    return date(year, month, day)

def generate_person_data(gender, birth_year, last_name_param=None, is_founder=False):
    """Generates a dictionary of data for creating a person."""
    first_name = get_random_name(gender)
    last_name = last_name_param if last_name_param else get_random_last_name()

    birth_date_obj = generate_birth_date(birth_year)
    is_living = True
    death_date_obj = None

    # Higher chance of being deceased for older generations
    if (is_founder and birth_year < 1900 and random.random() < 0.8) or \
       (not is_founder and birth_year < 1990 and random.random() < 0.4):

        min_death_year = birth_date_obj.year + random.randint(40, 60)
        max_death_year = birth_date_obj.year + random.randint(70, 120)

        current_year = datetime.now().year
        if max_death_year > current_year:
            max_death_year = current_year

        if min_death_year < max_death_year:
            death_year = random.randint(min_death_year, max_death_year)
            death_date_obj = generate_birth_date(death_year)
            if death_date_obj <= birth_date_obj:
                death_date_obj = birth_date_obj + timedelta(days=random.randint(365 * 40, 365 * 90))
                if death_date_obj.year > current_year:
                    death_date_obj = None

        if death_date_obj and death_date_obj.year <= current_year:
            is_living = False
        else:
            death_date_obj = None
            is_living = True

    return {
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "birth_date": birth_date_obj.isoformat() if birth_date_obj else None,
        "death_date": death_date_obj.isoformat() if death_date_obj and not is_living else None,
        "is_living": is_living,
        "privacy_level": "public"
    }

# --- API Interaction Functions ---
def api_login(session):
    """Logs into the API and stores session cookies."""
    login_url = f"{API_BASE_URL}/login"
    credentials = {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    try:
        response = session.post(login_url, json=credentials)
        response.raise_for_status()
        print("Login successful.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response content: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Response content: {e.response.text}")
        return None

def api_create_tree(session, tree_name):
    """Creates a new family tree."""
    tree_url = f"{API_BASE_URL}/trees"
    tree_data = {
        "name": tree_name,
        "description": f"Large demo family tree generated on {datetime.now().isoformat()}",
        "is_public": True,
        "default_privacy_level": "public"
    }
    try:
        response = session.post(tree_url, json=tree_data)
        response.raise_for_status()
        created_tree = response.json()
        print(f"Tree '{created_tree['name']}' created successfully with ID: {created_tree['id']}")
        return created_tree
    except requests.exceptions.RequestException as e:
        print(f"Failed to create tree: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.json()}")
        return None

def api_set_active_tree(session, tree_id):
    """Sets the active tree for the current session."""
    active_tree_url = f"{API_BASE_URL}/session/active_tree"
    try:
        response = session.put(active_tree_url, json={"tree_id": tree_id})
        response.raise_for_status()
        print(f"Active tree set to: {tree_id}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to set active tree: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.json()}")
        return False

def api_create_person(session, person_data, retry_delay=60):
    """Creates a new person in the active tree."""
    people_url = f"{API_BASE_URL}/people"
    retries = 3
    
    while retries > 0:
        try:
            response = session.post(people_url, json=person_data)
            response.raise_for_status()
            created_person = response.json()
            print(f"Person '{created_person['first_name']} {created_person['last_name']}' created")
            return created_person
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:  # Too Many Requests
                    print(f"Rate limited. Waiting {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retries -= 1
                    continue
            print(f"Failed to create person {person_data.get('first_name')}")
            return None
    return None
    except requests.exceptions.RequestException as e:
        print(f"Failed to create person {person_data.get('first_name')}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response content: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Response content: {e.response.text}")
        return None

def api_create_relationship(session, person1_id, person2_id, relationship_type, retry_delay=60):
    """Creates a relationship between two people."""
    relationships_url = f"{API_BASE_URL}/relationships"
    relationship_data = {
        "person1": person1_id,
        "person2": person2_id,
        "relationshipType": relationship_type
    }
    retries = 3
    
    while retries > 0:
        try:
            response = session.post(relationships_url, json=relationship_data)
            response.raise_for_status()
            created_relationship = response.json()
            print(f"Created {relationship_type} between {person1_id} and {person2_id}")
            return created_relationship
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:  # Too Many Requests
                    print(f"Rate limited. Waiting {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retries -= 1
                    continue
            print(f"Failed to create relationship between {person1_id} and {person2_id}")
            return None
    return None
    except requests.exceptions.RequestException as e:
        print(f"Failed to create relationship {relationship_type} between {person1_id} and {person2_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response content: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Response content: {e.response.text}")
        return None

def load_large_demo_data():
    """Main function to load a large demo family tree."""
    req_session = requests.Session()

    # 1. Login
    login_info = api_login(req_session)
    if not login_info:
        return

    # 2. Create a new Tree
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tree_name = f"Large Demo Family - {get_random_last_name()} - {timestamp}"
    tree = api_create_tree(req_session, tree_name)
    if not tree:
        return

    # 3. Set Active Tree
    if not api_set_active_tree(req_session, tree['id']):
        return

    print(f"\n--- Populating Large Tree: {tree_name} ({tree['id']}) ---")

    # 4. Generate and Load Family Data

    # Generation 0: Multiple Founding Couples (2-3 couples to start with)
    num_founding_couples = random.randint(2, 3)
    founding_couples = []
    all_people_created = {}

    for _ in range(num_founding_couples):
        founder_birth_year = random.randint(1900, 1920)  # Earlier birth years for more generations
        husband_ln = get_random_last_name()

        husband_data = generate_person_data("male", founder_birth_year, husband_ln, is_founder=True)
        wife_data = generate_person_data("female", founder_birth_year + random.randint(-2, 2), 
                                       get_random_last_name(), is_founder=True)

        husband = api_create_person(req_session, husband_data)
        wife = api_create_person(req_session, wife_data)

        if husband and wife:
            api_create_relationship(req_session, husband['id'], wife['id'], "spouse_current")
            founding_couples.append((husband, wife))
            all_people_created.update({husband['id']: husband, wife['id']: wife})

    if not founding_couples:
        print("Failed to create founding couples. Aborting.")
        return

    current_generation_couples = founding_couples
    num_generations_to_create = random.randint(5, 7)  # More generations for larger families

    for gen_num in range(num_generations_to_create):
        print(f"\n--- Generating Generation {gen_num + 1} ---")
        next_generation_couples = []

        for father, mother in current_generation_couples:
            num_children = random.randint(3, 6)  # More children per couple

            try:
                father_birth_year = int(father['birth_date'][:4])
            except (TypeError, ValueError, KeyError):
                print(f"Warning: Could not parse father's birth year. Skipping children.")
                continue

            children_start_birth_year = father_birth_year + random.randint(20, 30)

            for i in range(num_children):
                child_gender = random.choice(["male", "female"])
                child_birth_year = children_start_birth_year + random.randint(i * 2, i * 2 + 3)
                child_data = generate_person_data(child_gender, child_birth_year, father['last_name'])
                child = api_create_person(req_session, child_data)

                if child:
                    all_people_created[child['id']] = child
                    api_create_relationship(req_session, father['id'], child['id'], "biological_parent")
                    api_create_relationship(req_session, mother['id'], child['id'], "biological_parent")

                    # Higher chance to marry and have kids (80%)
                    if gen_num < num_generations_to_create - 1 and random.random() < 0.8:
                        spouse_birth_year = child_birth_year + random.randint(-2, 2)
                        spouse_gender = "female" if child_gender == "male" else "male"
                        spouse_data = generate_person_data(spouse_gender, spouse_birth_year, 
                                                         get_random_last_name())
                        spouse = api_create_person(req_session, spouse_data)

                        if spouse:
                            all_people_created[spouse['id']] = spouse
                            api_create_relationship(req_session, child['id'], spouse['id'], 
                                                 "spouse_current")
                            if child_gender == "male":
                                next_generation_couples.append((child, spouse))
                            else:
                                next_generation_couples.append((spouse, child))

        if not next_generation_couples:
            print("No couples formed for next generation. Stopping.")
            break

        current_generation_couples = next_generation_couples

    print("\n--- Large Demo Data Loading Complete ---")
    print(f"Total people created: {len(all_people_created)}")

if __name__ == "__main__":
    load_large_demo_data()
