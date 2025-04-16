# Modify app.py to include admin user management and password reset routes

import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
# Removed CSRF imports
from src.user_management import UserManagement, VALID_ROLES # Import VALID_ROLES
from src.family_tree import FamilyTree
from src.relationship import VALID_RELATIONSHIP_TYPES as VALID_REL_TYPES # Alias to avoid clash
from src.db_utils import load_data, save_data
from src.audit_log import log_audit
import json
import logging # Import logging
from datetime import datetime # Import datetime for template

# --- Configuration & Setup (Keep existing) ---
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_dev_secret_key_39$@5_v2')
if SECRET_KEY == 'a_very_strong_dev_secret_key_39$@5_v2':
    print("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
FAMILY_TREE_FILE = os.path.join(DATA_DIR, 'family_tree.json')
AUDIT_LOG_FILE = os.path.join(DATA_DIR, 'audit.log')
TEMPLATE_FOLDER = os.path.join(APP_ROOT, 'src', 'templates')
app = Flask(__name__, template_folder=TEMPLATE_FOLDER)
app.secret_key = SECRET_KEY
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Add datetime to Jinja context
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

# --- Initialize Core Components (Keep existing) ---
os.makedirs(DATA_DIR, exist_ok=True)
user_manager = UserManagement(USERS_FILE, AUDIT_LOG_FILE)
family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)
try: family_tree.load_tree(loaded_by="system_startup")
except Exception as e: app.logger.error(f"Failed to load family tree on startup: {e}", exc_info=True); family_tree = FamilyTree(FAMILY_TREE_FILE, AUDIT_LOG_FILE)

# --- Decorators (Keep existing login_required, admin_required) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: flash('Please log in to access this page.', 'warning'); log_audit(AUDIT_LOG_FILE, 'anonymous', 'access_denied', f'login required for {request.endpoint}'); return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: flash('Please log in to access this page.', 'warning'); log_audit(AUDIT_LOG_FILE, 'anonymous', 'access_denied', f'admin required (not logged in) for {request.endpoint}'); return redirect(url_for('login', next=request.url))
        if session.get('user_role') != 'admin': flash('You do not have permission to access this page.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'access_denied', f'admin required (role: {session.get("user_role")}) for {request.endpoint}'); return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# --- Main Routes (Keep existing index, /) ---
@app.route('/')
def index():
    people = []; relationships = []
    is_admin = session.get('user_role') == 'admin'
    if 'user_id' in session:
        try: people = family_tree.get_people_summary(); relationships = family_tree.get_relationships_summary()
        except Exception as e: app.logger.error(f"Error getting tree summary data: {e}", exc_info=True); flash("Error loading family tree data.", "danger"); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'index_load_error', f'Error: {e}')
    return render_template('index.html', people=people, relationships=relationships, is_admin=is_admin)

# --- Auth Routes (Keep existing register, login, logout) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session: flash("You are already logged in.", "info"); return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username'); password = request.form.get('password')
        if not username or not password: flash('Username and password are required.', 'danger'); return render_template('index.html', show_register=True)
        user = user_manager.register_user(username, password)
        if user: flash('Registration successful! Please log in.', 'success'); log_audit(AUDIT_LOG_FILE, username, 'register', f'success - role: {user.role}'); return redirect(url_for('login'))
        else: flash('Registration failed. Username might already exist or an error occurred.', 'danger'); log_audit(AUDIT_LOG_FILE, username, 'register', 'failure - see previous logs'); return render_template('index.html', show_register=True, reg_username=username)
    return render_template('index.html', show_register=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: flash("You are already logged in.", "info"); return redirect(url_for('index'))
    next_url = request.args.get('next')
    if request.method == 'POST':
        username = request.form.get('username'); password = request.form.get('password')
        if not username or not password: flash('Username and password are required.', 'danger'); return render_template('index.html', show_login=True, login_username=username, next=next_url)
        user = user_manager.login_user(username, password)
        if user:
            session['user_id'] = user.user_id; session['username'] = user.username; session['user_role'] = user.role
            flash(f'Welcome back, {user.username}!', 'success'); log_audit(AUDIT_LOG_FILE, username, 'login', 'success')
            if next_url: app.logger.info(f"Redirecting logged in user to: {next_url}"); return redirect(next_url)
            else: return redirect(url_for('index'))
        else: flash('Invalid username or password.', 'danger'); log_audit(AUDIT_LOG_FILE, username, 'login', 'failure - invalid credentials or user not found'); return render_template('index.html', show_login=True, login_username=username, next=next_url)
    return render_template('index.html', show_login=True, next=next_url)

@app.route('/logout')
@login_required
def logout():
    username = session.get('username', 'unknown'); role = session.get('user_role', 'unknown')
    session.pop('user_id', None); session.pop('username', None); session.pop('user_role', None)
    flash('You have been logged out.', 'info'); log_audit(AUDIT_LOG_FILE, username, 'logout', f'success - role: {role}')
    return redirect(url_for('index'))

# --- Family Tree Modification Routes (Keep existing) ---
@app.route('/add_person', methods=['POST'])
@login_required
def add_person():
    # (Keep existing implementation)
    try:
        first_name=request.form.get('first_name'); last_name=request.form.get('last_name'); nickname=request.form.get('nickname')
        dob=request.form.get('dob'); dod=request.form.get('dod'); gender=request.form.get('gender')
        pob=request.form.get('pob'); pod=request.form.get('pod')
        if not first_name or not first_name.strip(): flash('Person\'s first name is required.', 'danger'); return redirect(url_for('index'))
        logged_in_username = session.get('username', 'unknown_user')
        person = family_tree.add_person(first_name=first_name, last_name=last_name, nickname=nickname, dob=dob, dod=dod, gender=gender, pob=pob, pod=pod, added_by=logged_in_username)
        if person: flash(f'Person "{person.get_display_name()}" added successfully!', 'success')
        else: flash(f'Could not add person. Please check the required fields and date formats.', 'danger')
    except Exception as e: app.logger.error(f"Error adding person: {e}", exc_info=True); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'add_person', f'error: {e}'); flash('An unexpected error occurred while adding the person.', 'danger')
    return redirect(url_for('index'))

@app.route('/edit_person/<person_id>', methods=['GET', 'POST'])
@login_required
def edit_person(person_id):
    # (Keep existing implementation)
    person = family_tree.find_person(person_id=person_id)
    if not person: flash(f'Person with ID {person_id} not found.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'edit_person_attempt', f'failure - person not found: {person_id}'); return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            updated_data = {'first_name': request.form.get('first_name'), 'last_name': request.form.get('last_name'), 'nickname': request.form.get('nickname'), 'birth_date': request.form.get('dob'), 'death_date': request.form.get('dod'), 'gender': request.form.get('gender'), 'place_of_birth': request.form.get('pob'), 'place_of_death': request.form.get('pod') }
            logged_in_username = session.get('username', 'unknown_user')
            success = family_tree.edit_person(person_id, updated_data, edited_by=logged_in_username)
            if success: flash(f'Person "{person.get_display_name()}" updated successfully!', 'success'); return redirect(url_for('index'))
            else: flash(f'Could not update person "{person.get_display_name()}". Please check the fields and date formats.', 'warning'); return render_template('edit_person.html', person=person)
        except Exception as e: app.logger.error(f"Error editing person {person_id}: {e}", exc_info=True); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'edit_person', f'error for id {person_id}: {e}'); flash('An unexpected error occurred while editing the person.', 'danger'); return redirect(url_for('index'))
    return render_template('edit_person.html', person=person)

@app.route('/delete_person/<person_id>', methods=['POST'])
@login_required # Keep as login_required for now, or change to @admin_required
def delete_person(person_id):
    # (Keep existing implementation)
    person = family_tree.find_person(person_id=person_id)
    if not person: flash(f'Person with ID {person_id} not found.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'delete_person_attempt', f'failure - person not found: {person_id}'); return redirect(url_for('index'))
    try:
        person_display_name = person.get_display_name(); logged_in_username = session.get('username', 'unknown_user')
        success = family_tree.delete_person(person_id, deleted_by=logged_in_username)
        if success: flash(f'Person "{person_display_name}" and related relationships deleted successfully!', 'success')
        else: flash(f'Could not delete person "{person_display_name}". An error occurred.', 'danger')
    except Exception as e: app.logger.error(f"Error deleting person {person_id}: {e}", exc_info=True); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'delete_person', f'error for id {person_id}: {e}'); flash('An unexpected error occurred while deleting the person.', 'danger')
    return redirect(url_for('index'))


@app.route('/add_relationship', methods=['POST'])
@login_required
def add_relationship():
    # (Keep existing implementation)
    try:
        person1_id = request.form.get('person1_id'); person2_id = request.form.get('person2_id'); relationship_type = request.form.get('relationship_type')
        logged_in_username = session.get('username', 'unknown_user')
        relationship = family_tree.add_relationship(person1_id=person1_id, person2_id=person2_id, relationship_type=relationship_type, added_by=logged_in_username)
        if relationship: p1 = family_tree.find_person(person_id=person1_id); p2 = family_tree.find_person(person_id=person2_id); p1_name = p1.get_display_name() if p1 else f"ID {person1_id[:8]}"; p2_name = p2.get_display_name() if p2 else f"ID {person2_id[:8]}"; flash(f'Relationship ({relationship_type}) added between "{p1_name}" and "{p2_name}"!', 'success')
        else: flash('Could not add relationship. Check persons selected, type, and ensure it doesn\'t already exist or link a person to themselves.', 'danger')
    except Exception as e: app.logger.error(f"Error adding relationship: {e}", exc_info=True); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'add_relationship', f'error: {e}'); flash('An unexpected error occurred while adding the relationship.', 'danger')
    return redirect(url_for('index'))


@app.route('/edit_relationship/<relationship_id>', methods=['GET', 'POST'])
@login_required
def edit_relationship(relationship_id):
    # (Keep existing implementation)
    rel = family_tree.relationships.get(relationship_id)
    if not rel: flash(f'Relationship with ID {relationship_id} not found.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'edit_rel_attempt', f'failure - relationship not found: {relationship_id}'); return redirect(url_for('index'))
    person1 = family_tree.people.get(rel.person1_id); person2 = family_tree.people.get(rel.person2_id)
    if not person1 or not person2: flash(f'Cannot edit relationship {relationship_id} as one or both persons involved are missing.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'edit_rel_attempt', f'failure - person missing for rel {relationship_id}'); return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            new_type = request.form.get('relationship_type'); updated_data = {'rel_type': new_type}
            logged_in_username = session.get('username', 'unknown_user')
            success = family_tree.edit_relationship(relationship_id, updated_data, edited_by=logged_in_username)
            if success: flash(f'Relationship between "{person1.get_display_name()}" and "{person2.get_display_name()}" updated successfully!', 'success'); return redirect(url_for('index'))
            else: flash(f'Could not update relationship. Check the relationship type.', 'warning'); return render_template('edit_relationship.html', relationship=rel, person1=person1, person2=person2, valid_types=VALID_REL_TYPES)
        except Exception as e: app.logger.error(f"Error editing relationship {relationship_id}: {e}", exc_info=True); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'edit_relationship', f'error for id {relationship_id}: {e}'); flash('An unexpected error occurred while editing the relationship.', 'danger'); return redirect(url_for('index'))
    return render_template('edit_relationship.html', relationship=rel, person1=person1, person2=person2, valid_types=VALID_REL_TYPES)

@app.route('/delete_relationship/<relationship_id>', methods=['POST'])
@login_required
def delete_relationship(relationship_id):
    # (Keep existing implementation)
    rel = family_tree.relationships.get(relationship_id)
    if not rel: flash(f'Relationship with ID {relationship_id} not found.', 'danger'); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'delete_rel_attempt', f'failure - relationship not found: {relationship_id}'); return redirect(url_for('index'))
    try:
        p1 = family_tree.people.get(rel.person1_id); p2 = family_tree.people.get(rel.person2_id); p1_name = p1.get_display_name() if p1 else f"ID {rel.person1_id[:8]}"; p2_name = p2.get_display_name() if p2 else f"ID {rel.person2_id[:8]}"; rel_type = rel.rel_type; logged_in_username = session.get('username', 'unknown_user')
        success = family_tree.delete_relationship(relationship_id, deleted_by=logged_in_username)
        if success: flash(f'Relationship ({rel_type}) between "{p1_name}" and "{p2_name}" deleted successfully!', 'success')
        else: flash(f'Could not delete relationship. An error occurred.', 'danger')
    except Exception as e: app.logger.error(f"Error deleting relationship {relationship_id}: {e}", exc_info=True); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'delete_relationship', f'error for id {relationship_id}: {e}'); flash('An unexpected error occurred while deleting the relationship.', 'danger')
    return redirect(url_for('index'))


# --- Search Route (Keep existing) ---
@app.route('/search')
@login_required
def search():
    # (Keep existing implementation)
    query = request.args.get('q', '').strip(); dob_start = request.args.get('dob_start', '').strip(); dob_end = request.args.get('dob_end', '').strip(); location = request.args.get('location', '').strip()
    results = []; search_performed = bool(query or dob_start or dob_end or location)
    if search_performed:
        try: results = family_tree.search_people(query=query, dob_start=dob_start, dob_end=dob_end, location=location); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'search_people', f'query: "{query}", dob_start: "{dob_start}", dob_end: "{dob_end}", location: "{location}", results: {len(results)}')
        except Exception as e: app.logger.error(f"Error during search: {e}", exc_info=True); flash("An error occurred during the search.", "danger"); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'search_people', f'error: {e}')
    return render_template('search_results.html', query=query, dob_start=dob_start, dob_end=dob_end, location=location, results=results, search_performed=search_performed)

# --- API Endpoint (Keep existing) ---
@app.route('/api/tree_data')
@login_required
def tree_data():
    # (Keep existing implementation)
    try: data = family_tree.get_nodes_links_data(); return jsonify(data)
    except Exception as e: app.logger.error(f"Error generating tree data: {e}", exc_info=True); log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'get_tree_data', f'error: {e}'); return jsonify({"error": "Failed to generate tree data"}), 500

# --- NEW: Admin User Management Routes ---
@app.route('/admin/users')
@admin_required
def manage_users():
    """Display the list of users in the admin area."""
    try:
        # Sort users by username for consistent display
        all_users = sorted(list(user_manager.users.values()), key=lambda u: u.username.lower() if u.username else "")
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'view_admin_users', 'success')
        return render_template('admin_users.html', users=all_users, valid_roles=VALID_ROLES)
    except Exception as e:
        app.logger.error(f"Error retrieving users for admin page: {e}", exc_info=True)
        log_audit(AUDIT_LOG_FILE, session.get('username', 'unknown'), 'view_admin_users', f'error: {e}')
        flash("Error loading user list.", "danger")
        return redirect(url_for('index'))


@app.route('/admin/set_role/<user_id>', methods=['POST'])
@admin_required
def set_user_role(user_id):
    """Handle setting a user's role via POST request from admin."""
    new_role = request.form.get('role')
    actor_username = session.get('username', 'unknown_admin')

    # Basic validation
    target_user = user_manager.find_user_by_id(user_id)
    if not target_user:
        flash(f"User with ID {user_id} not found.", "danger")
        return redirect(url_for('manage_users'))

    if not new_role or new_role not in VALID_ROLES:
        flash(f"Invalid role specified: '{new_role}'.", "danger")
        log_audit(AUDIT_LOG_FILE, actor_username, 'set_user_role_attempt', f"failure - invalid role '{new_role}' for user {user_id}")
        return redirect(url_for('manage_users'))

    # Prevent admin from changing their own role via this form? (Optional)
    # if user_id == session.get('user_id'):
    #     flash("Administrators cannot change their own role via this interface.", "warning")
    #     return redirect(url_for('manage_users'))

    success = user_manager.set_user_role(user_id, new_role, actor_username=actor_username)

    if success:
        flash(f"Role for user '{target_user.username}' successfully updated to '{new_role}'.", "success")
    else:
        # Specific error logged by user_manager.set_user_role
        flash(f"Failed to update role for user '{target_user.username}'.", "danger")

    return redirect(url_for('manage_users'))


@app.route('/admin/delete_user/<user_id>', methods=['POST'])
@admin_required
def delete_user_admin(user_id):
    """Handle deleting a user via POST request from admin."""
    actor_username = session.get('username', 'unknown_admin')
    target_user = user_manager.find_user_by_id(user_id) # Get user details before deletion

    if not target_user:
        flash(f"User with ID {user_id} not found.", "danger")
        return redirect(url_for('manage_users'))

    # Prevent admin from deleting themselves
    if user_id == session.get('user_id'):
        flash("Administrators cannot delete their own account.", "danger")
        log_audit(AUDIT_LOG_FILE, actor_username, 'delete_user_admin', f"failure - attempted self-deletion: {user_id}")
        return redirect(url_for('manage_users'))

    deleted_username = target_user.username # Store username for flash message

    success = user_manager.delete_user(user_id, actor_username=actor_username)

    if success:
        flash(f"User '{deleted_username}' deleted successfully.", "success")
    else:
        # Specific error logged by user_manager.delete_user
        flash(f"Failed to delete user '{deleted_username}'.", "danger")

    return redirect(url_for('manage_users'))

# --- NEW: Password Reset Routes ---

@app.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    """Shows form and handles request to initiate password reset."""
    if 'user_id' in session:
        # Logged-in users shouldn't typically need this flow
        flash("You are already logged in. Use profile settings to change password (if available).", "info")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        if not username:
            flash("Please enter your username.", "warning")
            return render_template('request_reset.html')

        token = user_manager.generate_reset_token(username)

        if token:
            # !! INSECURE !! Display token directly because no email
            flash(f"Password reset requested for '{username}'. In a real app, a link would be emailed.", "info")
            app.logger.warning(f"PASSWORD RESET TOKEN (DISPLAYED FOR DEV ONLY): User={username}, Token={token}")
            # In a real app, you'd show a generic success message here.
            # For this demo, redirect to a page showing the token (highly insecure)
            # or just show it in the flash message and redirect to login.
            # Redirecting to login is slightly better than showing a dedicated token page.
            log_audit(AUDIT_LOG_FILE, username, 'request_password_reset', 'success (token generated)')
            # Maybe pass token to template ONLY FOR DEV/DEMO? NO - flash is enough warning.
            return redirect(url_for('login'))
        else:
            # Avoid confirming if user exists - show generic message
            flash("If a user with that username exists, a password reset process has been initiated (check logs for token in this demo).", "info")
            log_audit(AUDIT_LOG_FILE, username, 'request_password_reset', 'failure or user not found')
            return redirect(url_for('login'))

    # GET request
    return render_template('request_reset.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_with_token(token):
    """Shows form and handles the actual password reset using a token."""
    if 'user_id' in session:
        flash("You are already logged in.", "info")
        return redirect(url_for('index'))

    # Verify token validity for GET request (to show the form)
    user = user_manager.verify_reset_token(token)
    if not user:
        flash("Invalid or expired password reset token.", "danger")
        log_audit(AUDIT_LOG_FILE, f'token: {token[:8]}...', 'reset_password_view', 'failure - invalid/expired token')
        return redirect(url_for('request_password_reset'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or not confirm_password:
            flash("Both password fields are required.", "warning")
            return render_template('reset_password.html', token=token) # Show form again

        if new_password != confirm_password:
            flash("Passwords do not match.", "warning")
            return render_template('reset_password.html', token=token)

        # Attempt password reset (verify_reset_token called again inside reset_password)
        success = user_manager.reset_password(token, new_password)

        if success:
            flash("Your password has been reset successfully. Please log in.", "success")
            # Audit log handled by reset_password method
            return redirect(url_for('login'))
        else:
            # Handle potential race condition where token expires between GET and POST,
            # or other errors during reset_password.
            flash("Could not reset password. The token might have expired, or an error occurred.", "danger")
            # Audit log handled by reset_password method
            return redirect(url_for('request_password_reset'))

    # GET request: Show the reset form if token is valid
    log_audit(AUDIT_LOG_FILE, f'user: {user.username}', 'reset_password_view', 'success - token valid')
    return render_template('reset_password.html', token=token)


# --- Main Execution (Keep existing, ensure admin setup logic is appropriate) ---
if __name__ == '__main__':
    # Ensure first user becomes admin if no admin exists
    if user_manager.users and not any(user.role == 'admin' for user in user_manager.users.values()):
         first_user_id = next(iter(user_manager.users))
         app.logger.warning(f"No admin user found. Making first user '{user_manager.users[first_user_id].username}' an admin for initial setup.")
         user_manager.set_user_role(first_user_id, 'admin', actor_username='system_startup')
    elif not user_manager.users:
         app.logger.info("No users found in user file.")


    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))