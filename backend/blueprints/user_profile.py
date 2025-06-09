# backend/blueprints/user_profile.py
import structlog
from flask import Blueprint, request, jsonify, g, current_app, session # Added session
from werkzeug.utils import secure_filename
import os

# Absolute imports from the app root
from extensions import limiter
from decorators import require_auth
from services.user_service import (
    get_user_profile_by_id_db,
    update_user_profile_db,
    update_user_avatar_path_db,
    get_user_settings_db,
    update_user_settings_db
)
from schemas import UserResponseSchema, UserProfileUpdateSchema, UserSettingsSchema, PreferencesUpdateSchema

logger = structlog.get_logger(__name__)
user_profile_bp = Blueprint('user_profile_api', __name__, url_prefix='/api/users')

# Helper function to get current user_id from session
def get_current_user_id():
    return session.get('user_id') # Changed to use session

@user_profile_bp.route('/me', methods=['GET'])
@require_auth
def get_my_profile():
    user_id = get_current_user_id()
    if not user_id: # Should not happen if @require_auth is effective
        return jsonify({"message": "Authentication required."}), 401

    db_session = g.db
    try:
        user = get_user_profile_by_id_db(db_session, user_id)
        if not user:
            logger.warn("User profile not found for authenticated user.", user_id=user_id)
            return jsonify({"message": "User profile not found."}), 404

        user_data = UserResponseSchema.from_orm(user).dict()
        return jsonify(user_data), 200
    except Exception as e:
        logger.error("Error fetching user profile.", user_id=user_id, exc_info=True)
        return jsonify({"message": "Error fetching profile."}), 500

@user_profile_bp.route('/me', methods=['PUT'])
@require_auth
@limiter.limit("10 per minute")
def update_my_profile():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"message": "Authentication required."}), 401

    db_session = g.db
    json_data = request.get_json()

    if not json_data:
        return jsonify({"message": "Invalid input. JSON data required."}), 400

    try:
        profile_data = UserProfileUpdateSchema(**json_data)
    except Exception as e:
        logger.warn("User profile update validation failed.", user_id=user_id, errors=str(e)) # Pydantic v2 e.errors()
        return jsonify({"message": "Validation failed.", "errors": e.errors() if hasattr(e, 'errors') else str(e)}), 422

    try:
        update_data = profile_data.dict(exclude_unset=True)
        if not update_data:
            return jsonify({"message": "No data provided for update."}), 400

        updated_user = update_user_profile_db(db_session, user_id, update_data)
        if not updated_user:
            logger.warn("User profile not found for update.", user_id=user_id)
            return jsonify({"message": "User profile not found or update failed."}), 404

        user_response = UserResponseSchema.from_orm(updated_user).dict()
        return jsonify({"message": "Profile updated successfully.", "user": user_response}), 200
    except Exception as e:
        logger.error("Error updating user profile.", user_id=user_id, exc_info=True)
        return jsonify({"message": "Error updating profile."}), 500

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# UPLOAD_FOLDER will be read from app.config

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@user_profile_bp.route('/me/avatar', methods=['POST'])
@require_auth
@limiter.limit("5 per minute")
def upload_my_avatar():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"message": "Authentication required."}), 401

    db_session = g.db

    if 'avatar' not in request.files:
        return jsonify({"message": "No avatar file part in the request."}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"message": "No selected file."}), 400

    if file and allowed_file(file.filename):
        # Use a consistent subfolder for avatars, and user-specific filenames to avoid collisions
        # Filename can be just user_id + extension, or a hash. For simplicity:
        filename_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{user_id}_avatar.{filename_ext}")

        upload_folder_config = current_app.config.get('UPLOAD_FOLDER', 'uploads') # Default if not set
        # Avatars should go into a subfolder, e.g., 'avatars' within UPLOAD_FOLDER
        avatar_upload_dir = os.path.join(upload_folder_config, 'avatars')

        if not os.path.exists(avatar_upload_dir):
            os.makedirs(avatar_upload_dir, exist_ok=True)

        file_path = os.path.join(avatar_upload_dir, filename)

        try:
            file.save(file_path)
            # Path to be stored in DB: relative to a base URL or a specific serving path
            # e.g., 'avatars/user_id_avatar.png'
            avatar_storage_path = os.path.join('avatars', filename)

            updated_user = update_user_avatar_path_db(db_session, user_id, avatar_storage_path)
            if not updated_user:
                if os.path.exists(file_path): # Cleanup
                    os.remove(file_path)
                logger.error("Failed to update avatar path in DB.", user_id=user_id)
                return jsonify({"message": "Failed to update avatar information."}), 500

            user_response = UserResponseSchema.from_orm(updated_user).dict()
            return jsonify({
                "message": "Avatar uploaded successfully.",
                "user": user_response
            }), 200
        except Exception as e:
            if os.path.exists(file_path) and ('updated_user' not in locals() or not updated_user):
                 os.remove(file_path) # Cleanup if DB update failed or didn't happen
            logger.error("Error uploading avatar.", user_id=user_id, exc_info=True)
            return jsonify({"message": f"Error uploading avatar: {str(e)}"}), 500
    else:
        logger.warn("Avatar upload attempt with disallowed file type.", user_id=user_id, filename=file.filename)
        return jsonify({"message": "File type not allowed."}), 400

@user_profile_bp.route('/me/settings', methods=['GET'])
@require_auth
def get_my_settings():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"message": "Authentication required."}), 401

    db_session = g.db
    try:
        # The service function will fetch the User model and extract preferences
        user_settings = get_user_settings_db(db_session, user_id)
        if user_settings is None: # Check for None, as empty dict could be valid preferences
            logger.info("User settings not found or user has no preferences set.", user_id=user_id)
            # Return default settings schema or an empty dict based on desired behavior
            return jsonify(UserSettingsSchema().dict()), 200

        # user_settings should be a dict that can be parsed by UserSettingsSchema
        # or already a UserSettingsSchema object from the service layer.
        # Assuming service returns a dict that fits UserSettingsSchema:
        return jsonify(UserSettingsSchema(**user_settings).dict()), 200
    except Exception as e:
        logger.error("Error fetching user settings.", user_id=user_id, exc_info=True)
        return jsonify({"message": "Error fetching settings."}), 500

@user_profile_bp.route('/me/settings', methods=['PUT'])
@require_auth
@limiter.limit("10 per minute")
def update_my_settings():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"message": "Authentication required."}), 401

    db_session = g.db
    json_data = request.get_json()

    if not json_data:
        return jsonify({"message": "Invalid input. JSON data required."}), 400

    try:
        # Validate input using Pydantic schema for updating preferences
        # This schema allows partial updates (e.g., only notification_preferences)
        settings_data = PreferencesUpdateSchema(**json_data)
    except Exception as e: # Catches Pydantic validation errors
        logger.warn("User settings update validation failed.", user_id=user_id, errors=str(e))
        return jsonify({"message": "Validation failed.", "errors": e.errors() if hasattr(e, 'errors') else str(e)}), 422

    try:
        # Prepare data for service layer, excluding unset fields at the top level
        update_data = settings_data.dict(exclude_unset=True)

        if not update_data:
             return jsonify({"message": "No settings data provided for update."}), 400

        updated_settings = update_user_settings_db(db_session, user_id, update_data)
        if updated_settings is None:
            logger.warn("User settings update failed or user not found.", user_id=user_id)
            return jsonify({"message": "User not found or settings update failed."}), 404

        # Return the updated settings, parsed by UserSettingsSchema for consistency
        return jsonify({"message": "Settings updated successfully.", "settings": UserSettingsSchema(**updated_settings).dict()}), 200
    except Exception as e:
        logger.error("Error updating user settings.", user_id=user_id, exc_info=True)
        return jsonify({"message": "Error updating settings."}), 500
