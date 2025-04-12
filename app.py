import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from src.user_management import UserManagement
from src.family_tree import FamilyTree
from src.db_utils import load_data, save_data
from src.audit_log import log_audit

# --- Configuration ---
# Use environment variable for secret key in production, fallback for development   LaunchInstanceID
#SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_default_dev_secret_key_change_me')
SECRET_KEY = os.environ.get('LaunchInstanceID', 'a_default_dev_secret_key_change_me')
if SECRET_KEY == 'a_default_dev_secret_key_change_me':
    print("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")

# --- Data Paths ---
# Ensure paths are relative to the project root where app.py is located
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
FAMILY_TREE_FILE = os.path.join(DATA_DIR, 'family_tree.json')
AUDIT_LOG_FILE = os.path.join(DATA_DIR, 'audit.log')

# --- Application Setup ---
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'src', 'templates'))
app.secret_key = SECRET_KEY # Needed for session management (flash messages, login status)

# --- Initialize Core Components ---
# Initialize UserManagement with the correct path to the users file and audit log
user_manager = UserManagement(USERS_FILE, AUDIT_LOG_FILE)

# Initialize FamilyTree with the correct path to the family tree file and audit log
family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)
# Load existing family tree data on startup
family_tree.load_tree()

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
    if 'user_id' in session:
        # If logged in, get people data to display (or pass the whole tree)
        # For now, just get a list of names/ids for simplicity
        people = family_tree.get_people_summary() # Assumes FamilyTree has this method
    return render_template('index.html', people=people)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('register'))

        user = user_manager.register_user(username, password)
        if user:
            flash('Registration successful! Please log in.', 'success')
            # Log audit event - Pass username, action, and status
            log_audit(AUDIT_LOG_FILE, username, 'register', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.', 'danger')
            # Log audit event - Pass username, action, and status
            log_audit(AUDIT_LOG_FILE, username, 'register', 'failure - username exists')
            return redirect(url_for('register'))
    # If GET request or registration failed, show the registration form again
    # Check if already logged in, redirect to index if so
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('index.html') # Assuming registration is part of index

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('login'))

        user = user_manager.login_user(username, password)
        if user:
            session['user_id'] = user.user_id # Store user ID in session
            session['username'] = user.username
            flash(f'Welcome back, {user.username}!', 'success')
            # Log audit event - Pass username, action, and status
            log_audit(AUDIT_LOG_FILE, username, 'login', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            # Log audit event - Pass username, action, and status
            log_audit(AUDIT_LOG_FILE, username, 'login', 'failure - invalid credentials')
            return redirect(url_for('login')) # Redirect back to login part of index
    # If GET request or login failed, show the login form again
    # Check if already logged in, redirect to index if so
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('index.html') # Assuming login is part of index

@app.route('/logout')
@login_required # Ensure user is logged in to log out
def logout():
    """Logs the user out."""
    username = session.get('username', 'unknown') # Get username for logging
    session.pop('user_id', None) # Remove user ID from session
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    # Log audit event - Pass username, action, and status
    log_audit(AUDIT_LOG_FILE, username, 'logout', 'success')
    return redirect(url_for('index'))

# --- Family Tree Routes ---

@app.route('/add_person', methods=['POST'])
@login_required # Protect this route
def add_person():
    """Handles adding a new person to the family tree."""
    try:
        # Get data from the form
        name = request.form.get('name')
        dob = request.form.get('dob') # Date of Birth
        dod = request.form.get('dod') # Date of Death (optional)
        gender = request.form.get('gender') # Optional gender field
        # Add more fields as needed (place of birth, etc.)

        if not name:
            flash('Person\'s name is required.', 'danger')
            return redirect(url_for('index'))

        # Call the FamilyTree method to add the person
        # Pass the currently logged-in username for audit logging purposes
        logged_in_username = session.get('username', 'unknown_user')
        person = family_tree.add_person(name=name, dob=dob, dod=dod, gender=gender, added_by=logged_in_username)

        if person:
            flash(f'Person "{name}" added successfully!', 'success')
            # Optionally log specific details if needed in audit log
            # log_audit(AUDIT_LOG_FILE, logged_in_username, 'add_person', f'success - id: {person.person_id}, name: {name}')
        else:
            # This case might occur if add_person implements checks (e.g., duplicate names)
            flash(f'Could not add person "{name}".', 'danger')
             # log_audit(AUDIT_LOG_FILE, logged_in_username, 'add_person', f'failure - name: {name}')


    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"Error adding person: {e}")
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'add_person', f'error: {e}')
        flash('An error occurred while adding the person.', 'danger')

    return redirect(url_for('index'))

# Add routes for add_relationship, edit, delete etc. here later

# --- Main Execution ---
if __name__ == '__main__':
    # Make sure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    # Run the Flask development server
    # Debug=True automatically reloads on code changes and provides detailed error pages
    # Use host='0.0.0.0' to make the server accessible on your network
    app.run(debug=True, host='0.0.0.0', port=5001)
