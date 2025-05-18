# backend/blueprints/auth.py
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from ..extensions import limiter # Import limiter instance
from ..decorators import require_auth
from ..services.user_service import register_user_db, authenticate_user_db, request_password_reset_db, reset_password_db
from ..models import User # For user_info structure if needed

logger = structlog.get_logger(__name__)
auth_bp = Blueprint('auth_api', __name__, url_prefix='/api') # Base prefix /api

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute") # Specific limit for login
def login_endpoint():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        abort(400, description="Username and password are required.")
    
    username_or_email = data['username']
    password = data['password']
    db = g.db

    user = authenticate_user_db(db, username_or_email, password)
    if not user: # authenticate_user_db returns None on auth failure or aborts for other issues
        abort(401, description="Incorrect username or password.")

    session['user_id'] = str(user['id'])
    session['username'] = user['username']
    session['role'] = user['role']
    # session.permanent = True # If using permanent sessions with lifetime

    logger.info("User logged in successfully", user_id=user['id'], username=user['username'])
    return jsonify({"message": "Login successful!", "user": user, "active_tree_id": session.get('active_tree_id')}), 200

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute") # Specific limit for registration
def register_endpoint():
    data = request.get_json()
    # Basic check, service layer does more thorough validation
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        abort(400, description="Username, email, and password are required.")
    
    db = g.db
    try:
        user_data = {
            'username': data['username'], 'email': data['email'], 'password': data['password'],
            'full_name': data.get('full_name'), 'role': data.get('role')
        }
        user = register_user_db(db, user_data) # Service handles validation and integrity errors
        logger.info("User registered successfully", user_id=user['id'], username=user['username'])
        # Do not log in user immediately, require them to log in.
        return jsonify({"message": "Registration successful! Please log in.", "user": {"id": user["id"], "username": user["username"]}}), 201
    except HTTPException:
        raise # Re-raise aborts from service layer
    except Exception as e:
        logger.error("Unexpected error in /register endpoint", exc_info=True)
        abort(500, description="An unexpected error occurred during registration.")

@auth_bp.route('/logout', methods=['POST'])
@require_auth # User must be logged in to log out
def logout_endpoint():
    user_id = session.get('user_id')
    username = session.get('username')
    session.clear()
    logger.info("User logged out successfully", user_id=user_id, username=username)
    response = jsonify({"message": "Logout successful"})
    return response, 200

@auth_bp.route('/session', methods=['GET'])
def session_status_endpoint():
    if 'user_id' in session and 'username' in session and 'role' in session:
        user_info = {"id": session['user_id'], "username": session['username'], "role": session['role']}
        active_tree_id = session.get('active_tree_id')
        logger.debug("Session status: authenticated", user_id=user_info['id'], active_tree_id=active_tree_id)
        return jsonify({"isAuthenticated": True, "user": user_info, "active_tree_id": active_tree_id}), 200
    else:
        logger.debug("Session status: not authenticated")
        return jsonify({"isAuthenticated": False, "user": None, "active_tree_id": None}), 200

@auth_bp.route('/request-password-reset', methods=['POST'])
@limiter.limit("5 per 15minute")
def request_password_reset_api_endpoint(): # Renamed for clarity
    data = request.get_json()
    if not data or not data.get('email_or_username'):
        abort(400, description="Email or username is required.")
    
    email_or_username_input = data['email_or_username']
    db = g.db
    request_password_reset_db(db, email_or_username_input) # Service handles logic and aborts
    return jsonify({"message": "If an account exists for this identifier and is active, a password reset link has been sent."}), 200

@auth_bp.route('/reset-password/<string:token>', methods=['POST'])
@limiter.limit("5 per 15minute")
def reset_password_api_endpoint(token: str): # Renamed for clarity
    data = request.get_json()
    if not data or not data.get('new_password'):
        abort(400, description="New password is required.")
    
    new_password = data['new_password']
    db = g.db
    reset_password_db(db, token, new_password) # Service handles logic and aborts
    return jsonify({"message": "Password has been reset successfully."}), 200
