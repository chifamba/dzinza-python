import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
# Import necessary classes from your project structure
from src.user_management import UserManagement
from src.family_tree import FamilyTree
from src.db_utils import load_data, save_data # Assuming these are still used for something, maybe users?
from src.audit_log import log_audit

# --- Configuration ---
# Use environment variable for secret key in production, fallback for development
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_default_dev_secret_key_change_me')
if SECRET_KEY == 'a_default_dev_secret_key_change_me':
    print("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")

# --- Data Paths ---
# Ensure paths are relative to the project root where app.py is located
# Use os.path.abspath and os.path.dirname to make paths more robust
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
FAMILY_TREE_FILE = os.path.join(DATA_DIR, 'family_tree.json')
AUDIT_LOG_FILE = os.path.join(DATA_DIR, 'audit.log')

# --- Application Setup ---
# Define template folder relative to app.py location
TEMPLATE_FOLDER = os.path.join(APP_ROOT, 'src', 'templates')
app = Flask(__name__, template_folder=TEMPLATE_FOLDER)
app.secret_key = SECRET_KEY # Needed for session management (flash messages, login status)

# --- Initialize Core Components ---
# Ensure data directory exists before initializing components that might use it
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize UserManagement with the correct path to the users file and audit log
user_manager = UserManagement(USERS_FILE, AUDIT_LOG_FILE)

# Initialize FamilyTree with the correct path to the family tree file and audit log
family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)
# Load existing family tree data on startup
family_tree.load_tree(loaded_by="system_startup")

# --- Decorators ---
def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a route.
    Redirects to the login page if the user is not logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        # Add user object to g maybe? Or just fetch username from session when needed.
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def index():
    """
    Renders the main page.
    Displays login/register forms if not logged in.
    Displays family tree info and actions if logged in.
    """
    people = []
    relationships = [] # Initialize relationships list
    if 'user_id' in session:
        # If logged in, get people data for display and forms
        # get_people_summary now returns 'display_name' including nickname
        people = family_tree.get_people_summary()
        # get_relationships_summary now returns display names including nicknames
        relationships = family_tree.get_relationships_summary()

    # Pass both people and relationships lists to the template
    return render_template('index.html', people=people, relationships=relationships)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            # Redirect back to the same page, which should show the form again
            return render_template('index.html') # Or redirect(url_for('index'))

        user = user_manager.register_user(username, password)
        if user:
            flash('Registration successful! Please log in.', 'success')
            log_audit(AUDIT_LOG_FILE, username, 'register', 'success')
            return redirect(url_for('index')) # Redirect to index, which will show login form
        else:
            # Check if failure was due to existing username or other error
            # user_manager.register_user prints messages, we just flash generic one here
            flash('Registration failed. Username might already exist or an error occurred.', 'danger')
            log_audit(AUDIT_LOG_FILE, username, 'register', 'failure - see console/logs')
            return render_template('index.html') # Show form again

    # If GET request or already logged in
    if 'user_id' in session:
        return redirect(url_for('index'))
    # Show the index page which contains the registration form when not logged in
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('index.html') # Show form again

        user = user_manager.login_user(username, password)
        if user:
            session['user_id'] = user.user_id
            session['username'] = user.username
            flash(f'Welcome back, {user.username}!', 'success')
            log_audit(AUDIT_LOG_FILE, username, 'login', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            log_audit(AUDIT_LOG_FILE, username, 'login', 'failure - invalid credentials')
            return render_template('index.html') # Show form again

    # If GET request or already logged in
    if 'user_id' in session:
        return redirect(url_for('index'))
    # Show the index page which contains the login form when not logged in
    return render_template('index.html')

@app.route('/logout')
@login_required
def logout():
    """Logs the user out."""
    username = session.get('username', 'unknown')
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    log_audit(AUDIT_LOG_FILE, username, 'logout', 'success')
    return redirect(url_for('index'))

# --- Family Tree Routes ---

@app.route('/add_person', methods=['POST'])
@login_required
def add_person():
    """Handles adding a new person to the family tree."""
    try:
        # --- Updated to get separate name fields ---
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        nickname = request.form.get('nickname') # Get nickname
        dob = request.form.get('dob')
        dod = request.form.get('dod')
        gender = request.form.get('gender')

        # Basic validation (first name is required)
        if not first_name:
            flash('Person\'s first name is required.', 'danger')
            return redirect(url_for('index'))

        logged_in_username = session.get('username', 'unknown_user')

        # --- Updated call to family_tree.add_person ---
        person = family_tree.add_person(
            first_name=first_name,
            last_name=last_name,
            nickname=nickname, # Pass nickname
            dob=dob,
            dod=dod,
            gender=gender,
            added_by=logged_in_username
        )

        if person:
            # Use get_display_name for flash message
            flash(f'Person "{person.get_display_name()}" added successfully!', 'success')
        else:
            # add_person method in FamilyTree should print/log specific errors
            flash(f'Could not add person. Check logs for details.', 'danger')

    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"Error adding person: {e}", exc_info=True) # Log traceback
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'add_person', f'error: {e}')
        flash('An unexpected error occurred while adding the person.', 'danger')

    return redirect(url_for('index'))


@app.route('/add_relationship', methods=['POST'])
@login_required
def add_relationship():
    """Handles adding a new relationship between two people."""
    try:
        person1_id = request.form.get('person1_id')
        person2_id = request.form.get('person2_id')
        relationship_type = request.form.get('relationship_type')

        if not person1_id or not person2_id or not relationship_type:
            flash('Please select both people and a relationship type.', 'danger')
            return redirect(url_for('index'))

        if person1_id == person2_id:
            flash('Cannot add a relationship between a person and themselves.', 'danger')
            return redirect(url_for('index'))

        logged_in_username = session.get('username', 'unknown_user')
        relationship = family_tree.add_relationship(
            person1_id=person1_id,
            person2_id=person2_id,
            relationship_type=relationship_type,
            added_by=logged_in_username
        )

        if relationship:
            # Get display names (including nicknames) for the flash message
            p1 = family_tree.find_person(person_id=person1_id)
            p2 = family_tree.find_person(person_id=person2_id)
            p1_name = p1.get_display_name() if p1 else "Unknown"
            p2_name = p2.get_display_name() if p2 else "Unknown"
            flash(f'Relationship ({relationship_type}) added between "{p1_name}" and "{p2_name}"!', 'success')
        else:
            # add_relationship method in FamilyTree should print/log specific errors
            flash('Could not add relationship. Check if both persons exist.', 'danger')

    except Exception as e:
        app.logger.error(f"Error adding relationship: {e}", exc_info=True) # Log traceback
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'add_relationship', f'error: {e}')
        flash('An unexpected error occurred while adding the relationship.', 'danger')

    return redirect(url_for('index'))


# Add routes for edit, delete etc. here later

# --- Main Execution ---
if __name__ == '__main__':
    # Run the Flask development server
    # Debug=True enables auto-reload and detailed error pages
    # host='0.0.0.0' makes it accessible on the network
    # port=5001 is commonly used for Flask dev servers
    app.run(debug=True, host='0.0.0.0', port=5001)

