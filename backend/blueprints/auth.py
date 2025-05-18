# backend/blueprints/auth.py
"""
This file defines the Flask blueprint for authentication-related API endpoints,
including login, registration, logout, session status, and password reset.
"""
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from werkzeug.exceptions import HTTPException # Import HTTPException

# Absolute imports from the app root
from extensions import limiter
from decorators import require_auth
from services.user_service import (
    register_user_db, authenticate_user_db, 
    request_password_reset_db, reset_password_db
)
# from models import User # Not directly used here, user_info comes from service

logger = structlog.get_logger(__name__)
auth_bp = Blueprint('auth_api', __name__, url_prefix='/api')

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login_endpoint():
    """
    Handles user login. Authenticates the user and sets session variables.
    Rate limited to 10 attempts per minute per IP.
    """
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        abort(400, "Username and password are required.")
    username_or_email = data['username']; password = data['password']
    db = g.db
    try:
        user = authenticate_user_db(db, username_or_email, password)
        if not user: abort(401, "Incorrect username or password.") # Service returns None on auth fail
        session['user_id'] = str(user['id'])
        session['username'] = user['username']
        session['role'] = user['role']
        logger.info("User logged in.", user_id=user['id'], username=user['username'])
        return jsonify({"message": "Login successful!", "user": user, "active_tree_id": session.get('active_tree_id')}), 200
    except HTTPException: raise # Re-raise aborts from service (e.g. inactive account)
    except Exception as e:
        logger.error("Login error.", exc_info=True)
        abort(500, "Login failed due to an unexpected error.")


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register_endpoint():
    """
    Handles user registration. Creates a new user account.
    Rate limited to 5 attempts per minute per IP.
    """
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        abort(400, "Username, email, and password are required.")
    db = g.db
    try:
        user_data = {'username': data['username'], 'email': data['email'], 'password': data['password'],
                     'full_name': data.get('full_name'), 'role': data.get('role')}
        user = register_user_db(db, user_data)
        logger.info("User registered.", user_id=user['id'], username=user['username'])
        return jsonify({"message": "Registration successful! Please log in.", 
                        "user": {"id": user["id"], "username": user["username"]}}), 201
    except HTTPException: raise
    except Exception as e:
        logger.error("Registration error.", exc_info=True)
        abort(500, "Registration failed due to an unexpected error.")

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout_endpoint():
    """
    Logs out the currently authenticated user by clearing the session.
    """
    user_id = session.get('user_id'); username = session.get('username')
    session.clear()
    logger.info("User logged out.", user_id=user_id, username=username)
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route('/session', methods=['GET'])
def session_status_endpoint():
    """
    Checks and returns the current user's authentication status and basic info.
    """
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
def request_password_reset_api_endpoint():
    """
    Handles requests to initiate a password reset flow.
    Rate limited to 5 attempts per 15 minutes per IP.
    """
    data = request.get_json()
    if not data or not data.get('email_or_username'): abort(400, "Email or username required.")
    email_or_username_input = data['email_or_username']
    db = g.db
    try:
        request_password_reset_db(db, email_or_username_input)
        return jsonify({"message": "If an account exists, a password reset link has been sent."}), 200
    except HTTPException: raise
    except Exception as e:
        logger.error("Request password reset error.", exc_info=True)
        abort(500, "Error processing password reset request.")


@auth_bp.route('/reset-password/<string:token>', methods=['POST'])
@limiter.limit("5 per 15minute")

def reset_password_api_endpoint(token: str):
    """
    Handles the password reset using a valid token.
    Rate limited to 5 attempts per 15 minutes per IP.
    """
    data = request.get_json()
    if not data or not data.get('new_password'): abort(400, "New password required.")
    new_password = data['new_password']
    db = g.db
    try:
        reset_password_db(db, token, new_password)
        return jsonify({"message": "Password has been reset successfully."}), 200
    except HTTPException: raise
    except Exception as e:
        logger.error("Reset password error.", token_prefix=token[:6], exc_info=True)
        abort(500, "Error resetting password.")
