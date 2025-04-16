import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify # Import jsonify
# Import necessary classes from your project structure
from src.user_management import UserManagement
from src.family_tree import FamilyTree
from src.db_utils import load_data, save_data
from src.audit_log import log_audit
import json

# --- Configuration ---
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_default_dev_secret_key_change_me')
if SECRET_KEY == 'a_default_dev_secret_key_change_me':
    print("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")

# --- Data Paths ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
FAMILY_TREE_FILE = os.path.join(DATA_DIR, 'family_tree.json')
AUDIT_LOG_FILE = os.path.join(DATA_DIR, 'audit.log')

# --- Application Setup ---
TEMPLATE_FOLDER = os.path.join(APP_ROOT, 'src', 'templates')
app = Flask(__name__, template_folder=TEMPLATE_FOLDER)
app.secret_key = SECRET_KEY

# --- Initialize Core Components ---
os.makedirs(DATA_DIR, exist_ok=True)
user_manager = UserManagement(USERS_FILE, AUDIT_LOG_FILE)
family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)
family_tree.load_tree(loaded_by="system_startup")

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Main Routes ---
@app.route('/')
def index():
    """Renders the main page."""
    people = []
    relationships = []
    if 'user_id' in session:
        people = family_tree.get_people_summary()
        relationships = family_tree.get_relationships_summary()
    return render_template('index.html', people=people, relationships=relationships)

# --- Auth Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    # (Keep existing register logic)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('index.html')

        user = user_manager.register_user(username, password)
        if user:
            flash('Registration successful! Please log in.', 'success')
            log_audit(AUDIT_LOG_FILE, username, 'register', 'success')
            return redirect(url_for('index'))
        else:
            flash('Registration failed. Username might already exist or an error occurred.', 'danger')
            log_audit(AUDIT_LOG_FILE, username, 'register', 'failure - see console/logs')
            return render_template('index.html')

    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
     # (Keep existing login logic)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('index.html')

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
            return render_template('index.html')

    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/logout')
@login_required
def logout():
    # (Keep existing logout logic)
    username = session.get('username', 'unknown')
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    log_audit(AUDIT_LOG_FILE, username, 'logout', 'success')
    return redirect(url_for('index'))

# --- Family Tree Modification Routes ---
@app.route('/add_person', methods=['POST'])
@login_required
def add_person():
    # (Keep existing add_person logic using separate name fields)
    try:
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        nickname = request.form.get('nickname')
        dob = request.form.get('dob')
        dod = request.form.get('dod')
        gender = request.form.get('gender')

        if not first_name:
            flash('Person\'s first name is required.', 'danger')
            return redirect(url_for('index'))

        logged_in_username = session.get('username', 'unknown_user')
        person = family_tree.add_person(
            first_name=first_name, last_name=last_name, nickname=nickname,
            dob=dob, dod=dod, gender=gender, added_by=logged_in_username
        )

        if person:
            flash(f'Person "{person.get_display_name()}" added successfully!', 'success')
        else:
            flash(f'Could not add person. Check logs for details.', 'danger')
    except Exception as e:
        app.logger.error(f"Error adding person: {e}", exc_info=True)
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'add_person', f'error: {e}')
        flash('An unexpected error occurred while adding the person.', 'danger')
    return redirect(url_for('index'))


@app.route('/add_relationship', methods=['POST'])
@login_required
def add_relationship():
    # (Keep existing add_relationship logic)
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
            person1_id=person1_id, person2_id=person2_id,
            relationship_type=relationship_type, added_by=logged_in_username
        )

        if relationship:
            p1 = family_tree.find_person(person_id=person1_id)
            p2 = family_tree.find_person(person_id=person2_id)
            p1_name = p1.get_display_name() if p1 else "Unknown"
            p2_name = p2.get_display_name() if p2 else "Unknown"
            flash(f'Relationship ({relationship_type}) added between "{p1_name}" and "{p2_name}"!', 'success')
        else:
            flash('Could not add relationship. Check if both persons exist.', 'danger')
    except Exception as e:
        app.logger.error(f"Error adding relationship: {e}", exc_info=True)
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'add_relationship', f'error: {e}')
        flash('An unexpected error occurred while adding the relationship.', 'danger')
    return redirect(url_for('index'))


# --- API Endpoint for Tree Data ---
@app.route('/api/tree_data')
@login_required
def tree_data():
    """
    Provides family tree data (nodes and links) as JSON for D3 visualization.
    """
    try:
        # Get data formatted for D3
        data = family_tree.get_nodes_links_data()
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error generating tree data: {e}", exc_info=True)
        # Return an error response
        return jsonify({"error": "Failed to generate tree data"}), 500


# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

