# backend/services/user_service.py

# Standard Library Imports
import uuid
import copy
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Third-Party Imports
import structlog
from sqlalchemy.orm import Session as DBSession # Renamed to avoid conflict
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_
from flask import abort
from werkzeug.exceptions import HTTPException

# Local Application Imports
from models import User, UserRole
from utils import (
    _validate_password_complexity,
    _hash_password,
    _verify_password,
    _get_or_404,
    _handle_sqlalchemy_error,
    paginate_query
)
import config as app_config_module
import extensions # For metrics and get_fernet
from services.activity_service import log_activity # For audit logging
from email_utils import send_email  # For sending password reset emails

logger = structlog.get_logger(__name__)

def register_user_db(db: DBSession, 
                     user_data: Dict[str, Any],
                     ip_address: Optional[str] = None,
                     user_agent: Optional[str] = None
                     ) -> Dict[str, Any]:
    username = user_data.get('username'); email = user_data.get('email'); password = user_data.get('password')
    logger.info("Registering user", username=username, email=email, ip_address=ip_address)
    if not all([username, email, password]): abort(400, "Username, email, and password are required.")
    try: _validate_password_complexity(password)
    except ValueError as e: abort(400, str(e))
    hashed_password = _hash_password(password)
    try: user_role_enum = UserRole(user_data.get('role', UserRole.user.value))
    except ValueError: abort(400, f"Invalid role. Valid: {[r.value for r in UserRole]}.")
    try:
        new_user = User(username=username, email=email.lower(), password_hash=hashed_password,
            full_name=user_data.get('full_name'), role=user_role_enum, is_active=True, email_verified=False)
        db.add(new_user); db.commit(); db.refresh(new_user)
        user_dict = new_user.to_dict() # Get dict after refresh
        if extensions.user_registration_counter: extensions.user_registration_counter.add(1, {"status": "success"})
        logger.info("User registered.", user_id=new_user.id, username=new_user.username)

        # Audit Log (user themselves is the actor)
        log_activity(db=db, actor_user_id=new_user.id, action_type="REGISTER",
                     entity_type="USER", entity_id=new_user.id,
                     new_state={"username": user_dict["username"], "email": user_dict["email"], "role": user_dict["role"]},
                     ip_address=ip_address, user_agent=user_agent)
        
        return user_dict
    except IntegrityError as e:
        if extensions.user_registration_counter: extensions.user_registration_counter.add(1, {"status": "failure", "reason": "integrity_error"})
        _handle_sqlalchemy_error(e, "registering user", db)
    except SQLAlchemyError as e:
        if extensions.user_registration_counter: extensions.user_registration_counter.add(1, {"status": "failure", "reason": "db_error"})
        _handle_sqlalchemy_error(e, "registering user", db)
    except Exception as e:
        db.rollback()
        if extensions.user_registration_counter: extensions.user_registration_counter.add(1, {"status": "failure", "reason": "unknown_error"})
        logger.error("Unexpected error registering user.", username=username, exc_info=True)
        abort(500, "Error during registration.")
    return {} # Should be unreachable

def authenticate_user_db(db: DBSession, 
                         username_or_email: str, 
                         password: str,
                         ip_address: Optional[str] = None,
                         user_agent: Optional[str] = None
                         ) -> Optional[Dict[str, Any]]:
    logger.info("Authenticating user", identifier=username_or_email, ip_address=ip_address)
    if not username_or_email or not password: return None
    try:
        normalized_identifier = username_or_email.lower()
        user = db.query(User).filter(or_(User.username == username_or_email, User.email == normalized_identifier)).one_or_none()
        if not user:
            if extensions.auth_failure_counter: extensions.auth_failure_counter.add(1, {"reason": "user_not_found"})
            return None
        if not user.is_active:
            if extensions.auth_failure_counter: extensions.auth_failure_counter.add(1, {"reason": "inactive_account", "user_id": str(user.id)})
            abort(401, "Account is inactive.")
        if not _verify_password(password, user.password_hash):
            if extensions.auth_failure_counter: extensions.auth_failure_counter.add(1, {"reason": "incorrect_password", "user_id": str(user.id)})
            return None
        user.last_login = datetime.utcnow() 
        db.commit() 
        db.refresh(user) # Ensure last_login is refreshed before to_dict
        user_dict = user.to_dict(include_sensitive=False) # Get dict after refresh
        logger.info("Auth successful", user_id=user.id, username=user.username)

        # Audit Log
        log_activity(db=db, actor_user_id=user.id, action_type="LOGIN",
                     entity_type="USER", entity_id=user.id,
                     new_state={"last_login": user_dict.get("last_login")},
                     ip_address=ip_address, user_agent=user_agent)
        
        return user_dict
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "authenticating user", db)
    except HTTPException: raise
    except Exception as e:
        logger.error("Unexpected error during auth.", identifier=username_or_email, exc_info=True)
        abort(500, "Error during authentication.")
    return None # Should be unreachable

def get_all_users_db(db: DBSession, page: int = -1, per_page: int = -1,
                     sort_by: Optional[str] = "username", sort_order: Optional[str] = "asc"
                     ) -> Dict[str, Any]:
    cfg_pagination = app_config_module.config.PAGINATION_DEFAULTS
    if page == -1: page = cfg_pagination["page"]
    if per_page == -1: per_page = cfg_pagination["per_page"]
    logger.info("Fetching all users", page=page, per_page=per_page)
    try:
        query = db.query(User)
        if not hasattr(User, sort_by or ""): # Check if sort_by is a valid attribute
            logger.warning(f"Invalid sort_by column '{sort_by}' for User. Defaulting to 'username'.")
            sort_by = "username"
        return paginate_query(query, User, page, per_page, cfg_pagination["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "fetching all users", db)
    except Exception as e:
        logger.error("Unexpected error fetching all users", exc_info=True)
        abort(500, "Error fetching users.")
    return {} # Should be unreachable

def request_password_reset_db(db: DBSession, email_or_username: str) -> bool:
    logger.info("Password reset request", identifier=email_or_username)
    
    normalized_identifier = email_or_username.lower()
    user = db.query(User).filter(or_(User.username == email_or_username, User.email == normalized_identifier)).one_or_none()
    if not user or not user.is_active:
        logger.warning("Pwd reset for non-existent/inactive user.", identifier_prefix=email_or_username[:5])
        return True # Pretend success to prevent user enumeration
    try:
        raw_token = secrets.token_urlsafe(32)
        user.password_reset_token = raw_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        reset_link = f"{app_config_module.config.FRONTEND_APP_URL}/reset-password/{raw_token}"
        
        html_body = f"""
        <p>Hello {user.username or 'user'},</p>
        <p>You requested a password reset for your Dzinza account.</p>
        <p>Please click the link below to reset your password:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p>If you did not request this, please ignore this email.</p>
        <p>This link will expire in 1 hour.</p>
        <p>Thanks,<br>The Dzinza Team</p>
        """
        subject = "Password Reset Request for Dzinza"
        email_cfg = app_config_module.config
        if not all([email_cfg.EMAIL_SERVER, email_cfg.MAIL_SENDER_EMAIL]):
            logger.warning("Email server or sender email not configured. Cannot send password reset email.", 
                           user_id=user.id, reset_link_for_log=reset_link)
            logger.info("Password reset token generated, but email not sent due to missing configuration.", user_id=user.id)
            return True

        email_sent = send_email(to_email=user.email, subject=subject, html_body=html_body)
        
        if email_sent:
            logger.info("Password reset email sent successfully.", user_id=user.id, email=user.email)
        else:
            logger.error("Failed to send password reset email.", user_id=user.id, email=user.email, reset_link_for_log=reset_link)
        
        logger.info("Password reset token generated and email processed.", user_id=user.id)
        return True
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "requesting password reset", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error during pwd reset request.", user_id=getattr(user, 'id', None), exc_info=True)
        abort(500, "Error during password reset.")
    return False

def reset_password_db(db: DBSession, token: str, new_password: str) -> bool:
    logger.info("Resetting password with token", token_prefix=token[:8])
    if not token or not new_password: abort(400, "Token and new password required.")
    try:
        user = db.query(User).filter(User.password_reset_token == token, User.password_reset_expires > datetime.utcnow()).one_or_none()
        if not user: abort(400, "Invalid or expired password reset token.")
        _validate_password_complexity(new_password)
        user.password_hash = _hash_password(new_password)
        user.password_reset_token = None; user.password_reset_expires = None
        user.email_verified = True
        db.commit()
        logger.info("Password reset successful.", user_id=user.id)
        return True
    except ValueError as ve: abort(400, str(ve))
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "resetting password", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error resetting password.", exc_info=True)
        abort(500, "Error resetting password.")
    return False

def update_user_role_db(db: DBSession, 
                          user_id: uuid.UUID,
                          new_role_str: str,
                          actor_user_id: Optional[uuid.UUID] = None,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None
                          ) -> Dict[str, Any]:
    logger.info("Updating user role", target_user_id=user_id, new_role=new_role_str, actor_user_id=actor_user_id)
    try: new_role_enum = UserRole(new_role_str)
    except ValueError: abort(400, f"Invalid role: {new_role_str}. Valid: {[r.value for r in UserRole]}.")
    
    user = _get_or_404(db, User, user_id)
    previous_state = {"role": user.role.value if user.role else None}

    if user.role == new_role_enum: 
        logger.info("User role is already set to target role. No update performed.", user_id=user.id)
        return user.to_dict()
    
    user.role = new_role_enum
    try:
        db.commit(); db.refresh(user)
        updated_user_dict = user.to_dict()
        if extensions.role_change_counter: extensions.role_change_counter.add(1, {"target_user_id": str(user_id), "new_role": new_role_str})
        logger.info("User role updated.", user_id=user.id, new_role=user.role.value, actor_user_id=actor_user_id)

        log_activity(db=db, actor_user_id=actor_user_id, action_type="ROLE_CHANGE",
                     entity_type="USER", entity_id=user.id,
                     previous_state=previous_state, new_state={"role": updated_user_dict["role"]},
                     ip_address=ip_address, user_agent=user_agent)
        
        return updated_user_dict
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "updating user role", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error updating user role.", user_id=user_id, actor_user_id=actor_user_id, exc_info=True)
        abort(500, "Error updating user role.")
    return {}

def delete_user_db(db: DBSession, 
                     user_id: uuid.UUID,
                     actor_user_id: Optional[uuid.UUID] = None,
                     ip_address: Optional[str] = None,
                     user_agent: Optional[str] = None
                     ) -> None:
    logger.info("Deleting user", target_user_id=user_id, actor_user_id=actor_user_id)
    user = _get_or_404(db, User, user_id)
    previous_state = user.to_dict(include_sensitive=False)

    try:
        db.delete(user); db.commit()
        logger.info("User deleted.", user_id=user_id, actor_user_id=actor_user_id)

        log_activity(db=db, actor_user_id=actor_user_id, action_type="DELETE_USER",
                     entity_type="USER", entity_id=user_id,
                     previous_state=previous_state,
                     ip_address=ip_address, user_agent=user_agent)
        
    except IntegrityError as ie:
        db.rollback()
        if "violates foreign key constraint" in str(ie.orig).lower():
            abort(409, "Cannot delete user: user owns data (e.g., trees). Reassign or delete their data first.")
        _handle_sqlalchemy_error(ie, "deleting user (integrity)", db)
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "deleting user", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error deleting user.", target_user_id=user_id, actor_user_id=actor_user_id, exc_info=True)
        abort(500, "Error deleting user.")

# --- User Profile and Settings Functions ---

def get_user_profile_by_id_db(db: DBSession, user_id: uuid.UUID) -> Optional[User]:
    '''
    Retrieves a user profile by their ID.
    The blueprint will convert this User object to a Pydantic schema.
    '''
    logger.info("Fetching user profile by ID", user_id=str(user_id))
    try:
        user = _get_or_404(db, User, user_id)
        return user
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, "fetching user profile by ID", db)
    except Exception as e:
        logger.error("Unexpected error fetching user profile by ID.", user_id=str(user_id), exc_info=True)
        abort(500, f"An unexpected error occurred while fetching user profile {user_id}.")
    return None

def update_user_profile_db(db: DBSession,
                           user_id: uuid.UUID,
                           update_data: Dict[str, Any],
                           actor_user_id: Optional[uuid.UUID] = None,
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None
                           ) -> Optional[User]:
    '''
    Updates a user's profile (full_name, email).
    If email is changed, email_verified is set to False.
    '''
    logger.info("Updating user profile", user_id=str(user_id), update_data=update_data)
    user = _get_or_404(db, User, user_id)

    actual_actor_id = actor_user_id if actor_user_id else user_id
    previous_state = {
        "full_name": user.full_name,
        "email": user.email,
        "email_verified": user.email_verified
    }
    changed_fields = {}

    if "full_name" in update_data and user.full_name != update_data["full_name"]:
        user.full_name = update_data["full_name"]
        changed_fields["full_name"] = user.full_name

    if "email" in update_data and user.email != update_data["email"].lower():
        user.email = update_data["email"].lower()
        user.email_verified = False
        changed_fields["email"] = user.email
        changed_fields["email_verified"] = user.email_verified

    if not changed_fields:
        logger.info("No changes detected for user profile update.", user_id=str(user_id))
        return user

    try:
        db.commit()
        db.refresh(user)
        logger.info("User profile updated successfully.", user_id=str(user.id), changed_fields=changed_fields)

        log_activity(db=db, actor_user_id=actual_actor_id, action_type="UPDATE_PROFILE",
                     entity_type="USER", entity_id=user.id,
                     previous_state=previous_state, new_state=changed_fields,
                     ip_address=ip_address, user_agent=user_agent)
        return user
    except IntegrityError as e:
        _handle_sqlalchemy_error(e, "updating user profile (integrity)", db)
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, "updating user profile", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error updating user profile.", user_id=str(user_id), exc_info=True)
        abort(500, f"An unexpected error occurred while updating profile for user {user_id}.")
    return None

def update_user_avatar_path_db(db: DBSession,
                               user_id: uuid.UUID,
                               avatar_path: str,
                               actor_user_id: Optional[uuid.UUID] = None,
                               ip_address: Optional[str] = None,
                               user_agent: Optional[str] = None
                               ) -> Optional[User]:
    '''Updates the user's profile_image_path.'''
    logger.info("Updating user avatar path", user_id=str(user_id), new_path=avatar_path)
    user = _get_or_404(db, User, user_id)

    actual_actor_id = actor_user_id if actor_user_id else user_id
    previous_state = {"profile_image_path": user.profile_image_path}

    if user.profile_image_path == avatar_path:
        logger.info("Avatar path is the same. No update performed.", user_id=str(user_id))
        return user

    user.profile_image_path = avatar_path

    try:
        db.commit()
        db.refresh(user)
        logger.info("User avatar path updated successfully.", user_id=str(user.id))

        log_activity(db=db, actor_user_id=actual_actor_id, action_type="UPDATE_AVATAR",
                     entity_type="USER", entity_id=user.id,
                     previous_state=previous_state, new_state={"profile_image_path": avatar_path},
                     ip_address=ip_address, user_agent=user_agent)
        return user
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, "updating user avatar path", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error updating avatar path.", user_id=str(user_id), exc_info=True)
        abort(500, f"An unexpected error occurred while updating avatar for user {user_id}.")
    return None

def get_user_settings_db(db: DBSession, user_id: uuid.UUID) -> Dict[str, Any]:
    '''Retrieves user preferences/settings.'''
    logger.info("Fetching user settings", user_id=str(user_id))
    user = _get_or_404(db, User, user_id)
    return user.preferences if user.preferences is not None else {}

def _deep_update_dict(original_dict: Dict[Any, Any], update_with: Dict[Any, Any]) -> Dict[Any, Any]:
    '''
    Recursively updates a dictionary.
    Items in update_with override items in original_dict.
    If a value in update_with is a dictionary, it recursively updates the corresponding value in original_dict.
    '''
    updated = copy.deepcopy(original_dict)
    for key, value in update_with.items():
        if isinstance(value, dict) and isinstance(updated.get(key), dict):
            updated[key] = _deep_update_dict(updated[key], value)
        else:
            updated[key] = value
    return updated

def update_user_settings_db(db: DBSession,
                            user_id: uuid.UUID,
                            settings_data: Dict[str, Any],
                            actor_user_id: Optional[uuid.UUID] = None,
                            ip_address: Optional[str] = None,
                            user_agent: Optional[str] = None
                            ) -> Optional[Dict[str, Any]]:
    '''
    Updates user preferences (JSONB field).
    Performs a deep merge of the new settings_data into existing preferences.
    '''
    logger.info("Updating user settings", user_id=str(user_id), new_settings_data=settings_data)
    user = _get_or_404(db, User, user_id)

    actual_actor_id = actor_user_id if actor_user_id else user_id
    previous_preferences = copy.deepcopy(user.preferences) if user.preferences is not None else {}

    if user.preferences is None:
        user.preferences = {}

    current_prefs = copy.deepcopy(user.preferences)
    updated_prefs = _deep_update_dict(current_prefs, settings_data)

    if updated_prefs == previous_preferences:
        logger.info("No changes detected for user settings update.", user_id=str(user_id))
        return updated_prefs

    user.preferences = updated_prefs
    try:
        db.commit()
        db.refresh(user)
        logger.info("User settings updated successfully.", user_id=str(user.id))

        log_activity(db=db, actor_user_id=actual_actor_id, action_type="UPDATE_SETTINGS",
                     entity_type="USER", entity_id=user.id,
                     previous_state={"preferences": previous_preferences},
                     new_state={"preferences": user.preferences},
                     ip_address=ip_address, user_agent=user_agent)
        return user.preferences if user.preferences is not None else {}
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, "updating user settings", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error updating user settings.", user_id=str(user_id), exc_info=True)
        abort(500, f"An unexpected error occurred while updating settings for user {user_id}.")
    return None
