# app.py

import logging
import os
from flask import Flask, jsonify, request, g, render_template # Added render_template

# Import your classes and utilities
from src.user_management import UserManager
from src.family_tree import FamilyTree
from src.person import Person
from src.user import User
from src.audit_log import SimpleAuditLog # Use SimpleAuditLog
from src.encryption import PlaceholderDataEncryptor, hash_password # Keep hash_password
from src.db_utils import init_app as init_db # Import the init_app function

# --- Flask App Initialization ---
app = Flask(__name__, template_folder='src/templates') # Point to templates folder

# --- Configuration ---
# Secret key is needed for session management (authentication) later
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev') # Use environment variable in production

# --- Logging Setup ---
# Configure Flask's logger or use standard logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
app.logger.setLevel(logging.INFO) # Use Flask's logger

# --- Initialize Core Components ---
# These can be initialized once when the app starts.
# For scalability, consider factory pattern or dependency injection.
audit_log = SimpleAuditLog()
encryptor = PlaceholderDataEncryptor() # Use placeholder for now
user_manager = UserManager(audit_log=audit_log)
family_tree = FamilyTree(audit_log=audit_log)

# --- Initialize Database ---
# Registers the teardown function to close DB connections
init_db(app)

# --- API Routes ---

@app.route('/')
def index():
    """Serves a simple HTML index page."""
    # Renders src/templates/index.html
    # You can pass data to the template, e.g., list of users or persons
    try:
        persons = family_tree.get_all_persons()
        users = user_manager.get_all_users()
        return render_template('index.html', persons=persons, users=users)
    except Exception as e:
        app.logger.error(f"Error rendering index page: {e}")
        return "An error occurred loading the page.", 500


# == User API Endpoints ==

@app.route('/api/users', methods=['POST'])
def create_user_api():
    """API endpoint to create a new user."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    user_id = data.get('user_id')
    email = data.get('email')
    password = data.get('password') # Expect plaintext password

    if not all([user_id, email, password]):
        return jsonify({"error": "Missing required fields: user_id, email, password"}), 400

    try:
        # Hash the password before creating the User object
        password_hash = hash_password(password)
        new_user = User(user_id=user_id, email=email, password_hash=password_hash, role=data.get('role', 'guest'))

        if user_manager.add_user(new_user, actor_user_id="api_request"):
            return jsonify(new_user.to_dict()), 201 # Return created user data (without hash)
        else:
            # add_user logs the specific reason (e.g., duplicate ID)
            return jsonify({"error": "User creation failed (e.g., duplicate ID or validation error)"}), 400
    except ValueError as ve: # Catch validation errors from User class
        return jsonify({"error": f"Validation error: {ve}"}), 400
    except Exception as e:
        app.logger.error(f"Error creating user via API: {e}")
        return jsonify({"error": "Internal server error during user creation"}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user_api(user_id):
    """API endpoint to get a specific user."""
    user = user_manager.get_user(user_id)
    if user:
        return jsonify(user.to_dict()), 200 # Excludes hash by default
    else:
        return jsonify({"error": "User not found"}), 404

@app.route('/api/users', methods=['GET'])
def get_all_users_api():
    """API endpoint to get all users."""
    try:
        users = user_manager.get_all_users()
        # Convert users to dictionaries (excluding password hash)
        users_data = [user.to_dict() for user in users]
        return jsonify(users_data), 200
    except Exception as e:
        app.logger.error(f"Error getting all users via API: {e}")
        return jsonify({"error": "Internal server error retrieving users"}), 500


# == Person API Endpoints ==

@app.route('/api/persons', methods=['POST'])
def create_person_api():
    """API endpoint to create a new person."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    person_id = data.get('person_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    if not person_id: # Minimal requirement
        return jsonify({"error": "Missing required field: person_id"}), 400

    try:
        # Create Person object from request data
        person = Person.from_dict(data) # Use from_dict for flexibility
        family_tree.add_person(person, user="api_request")
        return jsonify(person.to_dict()), 201
    except ValueError as ve: # Catch duplicate ID or other validation errors
        return jsonify({"error": f"{ve}"}), 400
    except Exception as e:
        app.logger.error(f"Error creating person via API: {e}")
        return jsonify({"error": "Internal server error during person creation"}), 500


@app.route('/api/persons/<person_id>', methods=['GET'])
def get_person_api(person_id):
    """API endpoint to get a specific person."""
    person = family_tree.get_person(person_id)
    if person:
        return jsonify(person.to_dict()), 200
    else:
        return jsonify({"error": "Person not found"}), 404

@app.route('/api/persons', methods=['GET'])
def get_all_persons_api():
    """API endpoint to get all persons."""
    try:
        persons = family_tree.get_all_persons()
        persons_data = [person.to_dict() for person in persons]
        return jsonify(persons_data), 200
    except Exception as e:
        app.logger.error(f"Error getting all persons via API: {e}")
        return jsonify({"error": "Internal server error retrieving persons"}), 500


# --- Add more API endpoints as needed ---
# - Update/Delete Users
# - Update/Delete Persons
# - Add/Get/Update/Delete Relationships
# - Authentication endpoints (Login/Logout)
# - Tree visualization data endpoints

# --- Main Execution ---
if __name__ == '__main__':
    # Use waitress or gunicorn for production instead of Flask's dev server
    port = int(os.environ.get('PORT', 5000)) # Use PORT environment variable if available
    app.logger.info(f"Starting Flask server on port {port}")
    # Enable debug mode for development ONLY (auto-reloads, detailed errors)
    # Set debug=False for production
    app.run(debug=True, host='0.0.0.0', port=port)
