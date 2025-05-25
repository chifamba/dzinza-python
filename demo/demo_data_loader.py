import requests
import json
import time
import random
import logging
from faker import Faker
from datetime import datetime, timedelta

# --- Configuration ---
CONFIG_FILE_PATH = "load_config.json"
CRED_FILE_PATH = "cred.json"

# --- Global Variables ---
fake = Faker()
logger = logging.getLogger(__name__)

# --- Default Configuration ---
DEFAULT_CONFIG = {
    "api_base_url": "http://127.0.0.1:8090/api",
    "num_users_to_process": None,
    "users_to_process": [],
    "num_trees_per_user": 1,
    "tree_base_name": "Generated Family Tree",
    "num_generations": 3,
    "initial_couples_per_tree": 1,
    "min_children_per_couple": 1,
    "max_children_per_couple": 3,
    "chance_of_marriage_in_generation": 0.8,
    "max_retries": 3,
    "retry_delay_seconds": 5,
    "log_level": "INFO"
}

# --- Helper Functions ---
def load_json_file(file_path, error_msg_prefix):
    """Loads a JSON file and returns its content."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{error_msg_prefix}: File not found at {file_path}")
        return None
    except json.JSONDecodeError:
        logger.error(f"{error_msg_prefix}: Error decoding JSON from {file_path}")
        return None

def setup_logging(log_level_str):
    """Configures basic logging."""
    numeric_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level,
                        format='%(asctime)s - %(levelname)s - %(message)s')

def generate_random_date(start_year=1900, end_year=2023):
    """Generates a random date string."""
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date.strftime("%Y-%m-%d")

# --- API Client Class ---
class APIClient:
    """
    A client to interact with the backend API.
    Handles authentication and retries for API calls.
    """
    def __init__(self, base_url, username, password, email=None, max_retries=3, retry_delay=5):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.email = email if email else f"{username.split('@')[0]}@example.com" # Default email if not provided
        self.session = requests.Session()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.user_id = None # Will be set after successful login/registration

    def _request(self, method, endpoint, **kwargs):
        """Makes an HTTP request with retries."""
        url = f"{self.base_url}{endpoint}"
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                return response
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP error on {method} {url}: {e.response.status_code} {e.response.text}")
                if e.response.status_code == 401 and endpoint != "/auth/login" and endpoint != "/auth/register":
                    logger.info("Authentication error (401). Attempting to re-login...")
                    if not self.login(): # Try to re-login
                        logger.error("Re-login failed. Aborting this request.")
                        return None # Or raise the error
                
                # Retry for 429 (Too Many Requests) or 5xx server errors
                if e.response.status_code == 429 or 500 <= e.response.status_code <= 599:
                    if attempt < self.max_retries:
                        logger.info(f"Rate limit or server error. Retrying in {self.retry_delay}s... (Attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(self.retry_delay * (attempt + 1)) # Exponential backoff could be better
                    else:
                        logger.error(f"Max retries reached for {method} {url}.")
                        raise  # Re-raise the last error if all retries fail
                else: # For other client errors (4xx), don't retry unless it's a 401 handled above
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {method} {url}: {e}")
                if attempt == self.max_retries:
                    raise
                time.sleep(self.retry_delay)
        return None # Should not be reached if raise is used properly

    def register_and_login(self):
        """Attempts to log in. If login fails (e.g. user not found), tries to register then log in."""
        if self.login():
            return True
        
        logger.info(f"Login failed for {self.username}. Attempting to register...")
        if self.register():
            logger.info(f"Registration successful for {self.username}. Attempting to login again...")
            return self.login()
        else:
            logger.error(f"Registration failed for {self.username}.")
            return False

    def register(self):
        """Registers the user."""
        payload = {"username": self.username, "email": self.email, "password": self.password}
        try:
            response = self._request("POST", "/register", json=payload)
            if response and response.status_code == 201: # Assuming 201 Created for registration
                logger.info(f"User {self.username} registered successfully.")
                return True
            elif response:
                logger.warning(f"Registration for {self.username} failed. Status: {response.status_code}, Response: {response.text}")
            return False
        except requests.exceptions.HTTPError as e:
            # It's possible a 409 Conflict (or similar) means user already exists
            if e.response and e.response.status_code in [400, 409]: # Adjust status codes as per your API
                 logger.warning(f"Registration for {self.username} possibly failed due to existing user or bad data: {e.response.text}")
            else:
                logger.error(f"An error occurred during registration for {self.username}: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during registration for {self.username}: {e}")
            return False


    def login(self):
        """Logs in the user and stores the session."""
        payload = {"username": self.username, "password": self.password}
        try:
            response = self._request("POST", "/login", json=payload) # JSON data for login
            if response and response.status_code == 200:
                login_data = response.json()
                self.user_id = login_data.get("user", {}).get("id")
                if not self.user_id: # Fallback if user_id is not directly in response
                    # Try to get user_id from a /users/me endpoint if available, or parse from token
                    # For now, assume login response includes user info or we can fetch it.
                    # This part might need adjustment based on actual API response for login.
                    logger.warning("User ID not found directly in login response. Tree/Person creation might require it explicitly.")

                logger.info(f"User {self.username} logged in successfully. User ID: {self.user_id}")
                return True
            elif response:
                 logger.warning(f"Login failed for {self.username}. Status: {response.status_code}, Response: {response.text}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"Login HTTP error for {self.username}: {e.response.status_code} {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during login for {self.username}: {e}")
            return False

    def create_person(self, first_name, last_name, birth_date, gender, death_date=None, notes=""):
        """
        Creates a person in the active tree.
        The backend automatically associates the person with the active tree in the session.
        """
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": birth_date,
            "gender": gender,
            "death_date": death_date,
            "notes": notes
        }
        try:
            response = self._request("POST", "/people", json=payload)
            if response and response.status_code == 201:
                person_data = response.json()
                logger.info(f"Person '{first_name} {last_name}' created with ID: {person_data.get('id')}")
                return person_data
            elif response:
                logger.error(f"Failed to create person {first_name} {last_name}. Status: {response.status_code}, Response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating person {first_name} {last_name}: {e}")
            return None

    def create_tree(self, name, description=""):
        """
        Creates a family tree and sets it as the active tree in the session.
        The backend automatically sets the created tree as active.
        """
        payload = {"name": name, "description": description}
        try:
            response = self._request("POST", "/trees", json=payload)
            if response and response.status_code == 201:
                tree_data = response.json()
                logger.info(f"Tree '{name}' created with ID: {tree_data.get('id')}")
                return tree_data
            elif response:
                 logger.error(f"Failed to create tree {name}. Status: {response.status_code}, Response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating tree {name}: {e}")
            return None
            
    def set_active_tree(self, tree_id):
        """Sets the active tree in the session."""
        payload = {"tree_id": tree_id}
        try:
            response = self._request("PUT", "/session/active_tree", json=payload)
            if response and response.status_code == 200:
                logger.info(f"Active tree set to ID: {tree_id}")
                return True
            elif response:
                logger.error(f"Failed to set active tree {tree_id}. Status: {response.status_code}, Response: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Error setting active tree {tree_id}: {e}")
            return False

    def create_relationship(self, tree_id, person1_id, person2_id, relationship_type, start_date=None, end_date=None):
        """Creates a relationship between two people within a tree."""
        payload = {
            "person1_id": person1_id,
            "person2_id": person2_id,
            "relationship_type": relationship_type, # e.g., "SPOUSE", "PARENT_OF", "CHILD_OF"
            "tree_id": tree_id
        }
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date
        
        try:
            response = self._request("POST", "/relationships", json=payload)
            if response and response.status_code == 201:
                rel_data = response.json()
                logger.info(f"Relationship '{relationship_type}' created between {person1_id} and {person2_id} in tree {tree_id}. ID: {rel_data.get('id')}")
                return rel_data
            elif response:
                logger.error(f"Failed to create relationship. Status: {response.status_code}, Response: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return None

# --- Data Generation Logic ---
def generate_person_details(generation_num, base_year=1950, year_span_per_gen=25):
    """Generates realistic details for a person."""
    first_name = fake.first_name()
    last_name = fake.last_name() # Could be inherited or new
    gender = random.choice(["MALE", "FEMALE", "OTHER"]) # Match backend enum if specific
    
    birth_year_start = base_year - (generation_num * year_span_per_gen) - 10
    birth_year_end = base_year - (generation_num * year_span_per_gen) + 10
    birth_date = generate_random_date(birth_year_start, birth_year_end)
    
    death_date = None
    # Assume people from older generations might be deceased
    if generation_num > 1 and random.random() < 0.5: # 50% chance for older gens
        birth_dt = datetime.strptime(birth_date, "%Y-%m-%d")
        # Ensure death is after birth and they lived a reasonable lifespan
        death_year_start = birth_dt.year + random.randint(40, 90) 
        death_year_end = death_year_start + 10
        if death_year_start < datetime.now().year: # Only if they could have died by now
             death_date = generate_random_date(death_year_start, min(death_year_end, datetime.now().year -1))

    return first_name, last_name, birth_date, gender, death_date


def create_family_tree_for_user(api_client, config, user_num, tree_num_for_user):
    """Creates a full family tree with multiple generations for the logged-in user."""
    tree_name = f"{config['tree_base_name']} for {api_client.username} #{tree_num_for_user}"
    logger.info(f"--- Creating Tree: {tree_name} ---")
    
    tree = api_client.create_tree(name=tree_name, description=f"Generated by demo script for {api_client.username}")
    if not tree:
        logger.error(f"Failed to create tree '{tree_name}'. Skipping this tree.")
        return
    
    tree_id = tree.get("id")
    all_people_in_tree = {} # Store person_id: person_data
    
    # Ensure the tree is set as active
    if not api_client.set_active_tree(tree_id):
        logger.error(f"Failed to set tree '{tree_name}' as active. Skipping this tree.")
        return

    # Generation 0: Initial Couple(s)
    current_generation_couples = []
    for _ in range(config.get("initial_couples_per_tree", 1)):
        # Husband
        h_first, h_last, h_bdate, h_gender, h_ddate = generate_person_details(generation_num=config['num_generations'])
        husband = api_client.create_person(h_first, h_last, h_bdate, "MALE", h_ddate) # Force MALE for this role
        if husband:
            all_people_in_tree[husband['id']] = husband
        
        # Wife
        w_first, w_last, w_bdate, w_gender, w_ddate = generate_person_details(generation_num=config['num_generations'], base_year=datetime.strptime(h_bdate, "%Y-%m-%d").year + random.randint(-2, 5))
        wife = api_client.create_person(w_first, h_last, w_bdate, "FEMALE", w_ddate) # Share last name, force FEMALE
        if wife:
            all_people_in_tree[wife['id']] = wife

        if husband and wife:
            marriage_date = generate_random_date(max(datetime.strptime(h_bdate, "%Y-%m-%d").year, datetime.strptime(w_bdate, "%Y-%m-%d").year) + 18,
                                                 max(datetime.strptime(h_bdate, "%Y-%m-%d").year, datetime.strptime(w_bdate, "%Y-%m-%d").year) + 30)
            api_client.create_relationship(tree_id, husband['id'], wife['id'], "spouse_current", start_date=marriage_date)
            current_generation_couples.append({'husband': husband, 'wife': wife, 'gen_num': config['num_generations']})
            logger.info(f"Created initial couple: {h_first} {h_last} & {w_first} {w_last}")

    # Subsequent Generations
    for gen_idx_from_top in range(config['num_generations'] -1, -1, -1): # Iterate from oldest gen (e.g., 2) down to youngest (0)
        logger.info(f"--- Processing Generation (from top): {config['num_generations'] - gen_idx_from_top} (index {gen_idx_from_top}) ---")
        next_generation_couples = []
        
        # For each couple in the current generation, create children
        for couple_info in current_generation_couples:
            parent1 = couple_info['husband']
            parent2 = couple_info['wife']
            gen_num_of_parents = couple_info['gen_num'] # This is gen_num from perspective of oldest being N

            if not parent1 or not parent2:
                logger.warning("Skipping child generation for incomplete couple.")
                continue

            num_children = random.randint(config['min_children_per_couple'], config['max_children_per_couple'])
            logger.info(f"Couple {parent1['first_name']} & {parent2['first_name']} will have {num_children} children.")

            # Base birth year for children: ~20-30 years after parents' average birth year
            p1_birth_year = datetime.strptime(parent1['birth_date'], "%Y-%m-%d").year
            p2_birth_year = datetime.strptime(parent2['birth_date'], "%Y-%m-%d").year
            children_base_birth_year = ((p1_birth_year + p2_birth_year) // 2) + random.randint(20, 35)

            for i in range(num_children):
                child_first, child_last, child_bdate, child_gender, child_ddate = generate_person_details(
                    generation_num=gen_num_of_parents -1, # Children are one generation "younger" (closer to 0)
                    base_year=children_base_birth_year + random.randint(-2, i*2) # Stagger birth dates slightly
                )
                
                # Inherit last name from one of the parents (e.g. husband)
                child = api_client.create_person(child_first, parent1['last_name'], child_bdate, child_gender, child_ddate)
                if child:
                    all_people_in_tree[child['id']] = child
                    
                    # Add PARENT_OF relationships
                    # Backend might enforce PARENT_OF from parent to child, or CHILD_OF from child to parent
                    # Let's assume PARENT_OF is the primary one to create.
                    # The relationship service should ideally handle creating the inverse.
                    api_client.create_relationship(tree_id, parent1['id'], child['id'], "biological_parent")
                    api_client.create_relationship(tree_id, parent2['id'], child['id'], "biological_parent")
                    logger.info(f"Created child: {child_first} {parent1['last_name']} for {parent1['first_name']} & {parent2['first_name']}")

                    # Chance for this child to marry and form a new couple for the *next* generation's processing
                    # (unless this is the youngest generation being created)
                    if gen_num_of_parents -1 > 0 and random.random() < config['chance_of_marriage_in_generation']:
                        # Create a spouse for this child
                        spouse_first, spouse_last, spouse_bdate, spouse_gender, spouse_ddate = generate_person_details(
                            generation_num=gen_num_of_parents -1, # Spouse is same generation as child
                            base_year=datetime.strptime(child_bdate, "%Y-%m-%d").year + random.randint(-3, 3)
                        )
                        spouse = api_client.create_person(spouse_first, spouse_last, # Spouse can have different last name
                                                          spouse_bdate, spouse_gender, spouse_ddate)
                        if spouse:
                            all_people_in_tree[spouse['id']] = spouse
                            
                            marriage_date = generate_random_date(
                                max(datetime.strptime(child_bdate, "%Y-%m-%d").year, datetime.strptime(spouse_bdate, "%Y-%m-%d").year) + 18,
                                max(datetime.strptime(child_bdate, "%Y-%m-%d").year, datetime.strptime(spouse_bdate, "%Y-%m-%d").year) + 30
                            )
                            api_client.create_relationship(tree_id, child['id'], spouse['id'], "SPOUSE", start_date=marriage_date)
                            
                            # Add this new couple to the list for the next generation's processing
                            # Ensure correct gender assignment for 'husband' and 'wife' roles in the couple dict
                            new_couple = {}
                            if child_gender == "MALE":
                                new_couple = {'husband': child, 'wife': spouse, 'gen_num': gen_num_of_parents -1}
                            elif child_gender == "FEMALE":
                                new_couple = {'husband': spouse, 'wife': child, 'gen_num': gen_num_of_parents -1}
                            else: # Handle 'OTHER' or if one is MALE/FEMALE and other is OTHER
                                # Defaulting child as P1, spouse as P2 for couple structure
                                new_couple = {'husband': child, 'wife': spouse, 'gen_num': gen_num_of_parents -1}

                            if new_couple.get('husband') and new_couple.get('wife'): # Ensure both exist
                                next_generation_couples.append(new_couple)
                                logger.info(f"Child {child_first} married {spouse_first} {spouse_last}. They form a new couple.")
        
        current_generation_couples = next_generation_couples # Move to the next generation down

    logger.info(f"--- Finished creating Tree: {tree_name} with {len(all_people_in_tree)} people ---")


# --- Main Execution ---
def main():
    """Main function to drive the data loading process."""
    
    # Load configuration
    config_data = load_json_file(CONFIG_FILE_PATH, "Config loading")
    if not config_data:
        logger.info("Using default configuration as load_config.json was not found or was invalid.")
        config = DEFAULT_CONFIG.copy()
    else:
        config = DEFAULT_CONFIG.copy()
        config.update(config_data) # Override defaults with file contents

    setup_logging(config.get("log_level", "INFO"))
    logger.info("Starting demo data loader script...")
    logger.debug(f"Using configuration: {json.dumps(config, indent=2)}")

    # Load credentials
    credentials = load_json_file(CRED_FILE_PATH, "Credentials loading")
    if not credentials or not isinstance(credentials.get("users"), list):
        logger.error(f"Could not load credentials or 'users' array not found/valid in {CRED_FILE_PATH}. Exiting.")
        return

    users_to_process_config = config.get("users_to_process", [])
    num_users_to_process_config = config.get("num_users_to_process")

    # Filter users based on config
    if users_to_process_config:
        active_users = [u for u in credentials["users"] if u.get("username") in users_to_process_config]
        logger.info(f"Processing specific users from config: {[u['username'] for u in active_users]}")
    elif num_users_to_process_config is not None:
        active_users = credentials["users"][:num_users_to_process_config]
        logger.info(f"Processing first {num_users_to_process_config} users from cred.json: {[u['username'] for u in active_users]}")
    else:
        active_users = credentials["users"]
        logger.info(f"Processing all {len(active_users)} users from cred.json.")


    for i, user_creds in enumerate(active_users):
        username = user_creds.get("username")
        password = user_creds.get("password")
        email = user_creds.get("email") # Optional email from cred.json

        if not username or not password:
            logger.warning(f"Skipping user entry due to missing username or password: {user_creds}")
            continue

        logger.info(f"Processing User {i+1}/{len(active_users)}: {username}")

        api_client = APIClient(
            base_url=config["api_base_url"],
            username=username,
            password=password,
            email=email, # Pass email if available
            max_retries=config["max_retries"],
            retry_delay=config["retry_delay_seconds"]
        )

        if not api_client.register_and_login():
            logger.error(f"Could not login or register user {username}. Skipping this user.")
            continue
        
        # User is logged in, now create data for them
        num_trees = config.get("num_trees_per_user", 1)
        for tree_idx in range(num_trees):
            logger.info(f"User {username}: Creating tree {tree_idx + 1}/{num_trees}")
            create_family_tree_for_user(api_client, config, i, tree_idx + 1)
            time.sleep(1) # Small delay between creating trees for the same user

    logger.info("Demo data loading process finished.")

if __name__ == "__main__":
    main()
