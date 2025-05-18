import requests
import random
import json
import time
from datetime import datetime, timedelta, date

# --- Configuration ---
API_BASE_URL = "http://localhost:8090/api"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "01Admin_2025"
RETRY_DELAY = 60  # seconds to wait when rate limited

def api_request_with_retry(method, url, session, data=None, retries=3):
    """Generic API request function with retry logic for rate limiting."""
    while retries > 0:
        try:
            if method == "post":
                response = session.post(url, json=data)
            elif method == "put":
                response = session.put(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:  # Too Many Requests
                    print(f"Rate limited. Waiting {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                    retries -= 1
                    if retries > 0:
                        continue
            print(f"Request failed: {str(e)}")
            return None
    return None

def api_login(session):
    """Logs into the API and stores session cookies."""
    return api_request_with_retry(
        "post",
        f"{API_BASE_URL}/login",
        session,
        {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )

def api_create_tree(session, name):
    """Creates a new family tree."""
    return api_request_with_retry(
        "post",
        f"{API_BASE_URL}/trees",
        session,
        {
            "name": name,
            "description": f"Large demo tree generated on {datetime.now().isoformat()}",
            "is_public": True,
            "default_privacy_level": "public"
        }
    )

def api_set_active_tree(session, tree_id):
    """Sets the active tree for the current session."""
    return api_request_with_retry(
        "put",
        f"{API_BASE_URL}/session/active_tree",
        session,
        {"tree_id": tree_id}
    )

def api_create_person(session, person_data):
    """Creates a new person in the active tree."""
    result = api_request_with_retry(
        "post",
        f"{API_BASE_URL}/people",
        session,
        person_data
    )
    if result:
        print(f"Created {result['first_name']} {result['last_name']}")
    return result

def api_create_relationship(session, person1_id, person2_id, relationship_type):
    """Creates a relationship between two people."""
    result = api_request_with_retry(
        "post",
        f"{API_BASE_URL}/relationships",
        session,
        {
            "person1": person1_id,
            "person2": person2_id,
            "relationshipType": relationship_type
        }
    )
    if result:
        print(f"Created {relationship_type} between {person1_id} and {person2_id}")
    return result

def generate_person_data(birth_year, gender, last_name=None, is_founder=False):
    """Generate person data with realistic dates and attributes."""
    first_name = random.choice(MALE_NAMES if gender == "male" else FEMALE_NAMES)
    last_name = last_name or random.choice(LAST_NAMES)
    
    # Generate birth date in the given year
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    birth_date = date(birth_year, month, day)
    
    death_date = None
    is_living = True
    
    # Calculate death probability and date
    if is_founder and birth_year < 1920:
        death_prob = 0.9
    elif birth_year < 1950:
        death_prob = 0.7
    elif birth_year < 1970:
        death_prob = 0.3
    else:
        death_prob = 0.1
        
    if random.random() < death_prob:
        min_age = max(40, 2025 - birth_year - 50)
        max_age = min(95, 2025 - birth_year)
        if min_age < max_age:
            death_age = random.randint(min_age, max_age)
            death_year = birth_year + death_age
            death_date = date(death_year, random.randint(1, 12), random.randint(1, 28))
            is_living = False
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "birth_date": birth_date.isoformat(),
        "death_date": death_date.isoformat() if death_date else None,
        "is_living": is_living,
        "privacy_level": "public"
    }

def create_large_family_tree():
    """Creates a large family tree with multiple generations."""
    session = requests.Session()
    
    # Login
    if not api_login(session):
        return
    
    # Create tree
    tree_name = f"Large Family Tree - {random.choice(LAST_NAMES)} - {datetime.now().strftime('%Y%m%d_%H%M')}"
    tree = api_create_tree(session, tree_name)
    if not tree or not api_set_active_tree(session, tree['id']):
        return
    
    print(f"\nCreating large family tree: {tree_name}")
    all_people = {}
    
    # Create founding couples (2-3)
    founding_couples = []
    for _ in range(random.randint(2, 3)):
        husband_year = random.randint(1900, 1920)
        husband_ln = random.choice(LAST_NAMES)
        
        husband = api_create_person(session, generate_person_data(
            husband_year, "male", husband_ln, True))
        if not husband:
            continue
            
        wife = api_create_person(session, generate_person_data(
            husband_year + random.randint(-3, 3), "female", None, True))
        if not wife:
            continue
            
        if api_create_relationship(session, husband['id'], wife['id'], "spouse_current"):
            founding_couples.append((husband, wife))
            all_people.update({husband['id']: husband, wife['id']: wife})
            
    print(f"Created {len(founding_couples)} founding couples")
    
    # Generate subsequent generations
    current_couples = founding_couples
    generations = 5
    for gen in range(generations):
        print(f"\nGenerating Generation {gen + 1}")
        next_gen_couples = []
        
        for father, mother in current_couples:
            # Each couple has 3-6 children
            for _ in range(random.randint(3, 6)):
                child_birth_year = int(father['birth_date'][:4]) + random.randint(20, 35)
                child_gender = random.choice(["male", "female"])
                
                child = api_create_person(session, generate_person_data(
                    child_birth_year, child_gender, father['last_name']))
                if not child:
                    continue
                    
                all_people[child['id']] = child
                api_create_relationship(session, father['id'], child['id'], "biological_parent")
                api_create_relationship(session, mother['id'], child['id'], "biological_parent")
                
                # 80% chance for child to marry
                if gen < generations - 1 and random.random() < 0.8:
                    spouse = api_create_person(session, generate_person_data(
                        child_birth_year + random.randint(-5, 5),
                        "female" if child_gender == "male" else "male"))
                    if spouse and api_create_relationship(
                        session, child['id'], spouse['id'], "spouse_current"):
                        all_people[spouse['id']] = spouse
                        next_gen_couples.append(
                            (child, spouse) if child_gender == "male" else (spouse, child)
                        )
        
        if not next_gen_couples:
            break
        current_couples = next_gen_couples
        print(f"Generation {gen + 1} complete. Created {len(all_people)} people so far.")
        
        # Add small delay between generations to help with rate limiting
        time.sleep(5)
    
    print(f"\nFamily tree complete! Total people: {len(all_people)}")
    return len(all_people)

# Name data
MALE_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard",
    "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew",
    "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua"
]

FEMALE_NAMES = [
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
    "Jessica", "Sarah", "Karen", "Nancy", "Margaret", "Lisa", "Betty",
    "Sandra", "Ashley", "Kimberly", "Emily", "Donna", "Michelle"
]

LAST_NAMES = [
    "Smith", "Jones", "Williams", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
    "Martin", "Thompson", "Garcia", "Martinez", "Robinson", "Clark"
]

if __name__ == "__main__":
    create_large_family_tree()
