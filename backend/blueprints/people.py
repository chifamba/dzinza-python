# backend/blueprints/people.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from werkzeug.exceptions import HTTPException

from decorators import require_tree_access, require_auth # require_auth might be implicitly handled by require_tree_access depending on its impl.
from services.person_service import (
    get_all_people_db, get_person_db, create_person_db,
    update_person_db, delete_person_db,
    upload_profile_picture_db
)
from services.media_service import get_media_for_entity_db # Added for person media
from utils import get_pagination_params
# werkzeug.utils.secure_filename is imported in service now

logger = structlog.get_logger(__name__)
people_bp = Blueprint('people_api', __name__, url_prefix='/api/people')

@people_bp.route('', methods=['GET'])
@require_tree_access('view')
def get_all_people_endpoint():
    db = g.db; tree_id = g.active_tree_id
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "last_name"
    filters = {}
    if request.args.get('is_living') is not None: filters['is_living'] = request.args.get('is_living', type=str).lower() == 'true'
    if request.args.get('name_contains'): filters['name_contains'] = request.args.get('name_contains', type=str)
    logger.info("Get all people", tree_id=tree_id, page=page, per_page=per_page, filters=filters)
    try:
        return jsonify(get_all_people_db(db, tree_id, page, per_page, sort_by, sort_order, filters=filters)), 200
    except Exception as e:
        logger.error("Error in get_all_people.", tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching people.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['GET'])
@require_tree_access('view')
def get_person_endpoint(person_id_param: uuid.UUID):
    db = g.db; tree_id = g.active_tree_id
    logger.info("Get person", person_id=person_id_param, tree_id=tree_id)
    try:
        return jsonify(get_person_db(db, person_id_param, tree_id)), 200
    except Exception as e:
        logger.error("Error in get_person.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching person details.")
        raise

@people_bp.route('', methods=['POST'])
@require_tree_access('edit')
def create_person_endpoint():
    data = request.get_json(); user_id = uuid.UUID(session['user_id'])
    if not data: abort(400, "Request body cannot be empty.")
    db = g.db; tree_id = g.active_tree_id
    logger.info("Create person", tree_id=tree_id, user_id=user_id, data_keys=list(data.keys()))
    try:
        return jsonify(create_person_db(db, user_id, tree_id, data)), 201
    except Exception as e:
        logger.error("Error in create_person.", tree_id=tree_id, user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error creating person.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['PUT'])
@require_tree_access('edit')
def update_person_endpoint(person_id_param: uuid.UUID):
    data = request.get_json()
    if not data: abort(400, "Request body cannot be empty.")
    db = g.db; tree_id = g.active_tree_id
    logger.info("Update person", person_id=person_id_param, tree_id=tree_id, data_keys=list(data.keys()))
    try:
        return jsonify(update_person_db(db, person_id_param, tree_id, data)), 200
    except Exception as e:
        logger.error("Error in update_person.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error updating person.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['DELETE'])
@require_tree_access('edit')
def delete_person_endpoint(person_id_param: uuid.UUID):
    db = g.db; tree_id = g.active_tree_id
    logger.info("Delete person", person_id=person_id_param, tree_id=tree_id)
    try:
        delete_person_db(db, person_id_param, tree_id)
        return '', 204
    except Exception as e:
        logger.error("Error in delete_person.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error deleting person.")
        raise

@people_bp.route('/<uuid:person_id_param>/profile_picture', methods=['POST'])
@require_auth # Ensure user is logged in
@require_tree_access('edit') # Ensures user has edit rights for the tree this person belongs to
def upload_person_profile_picture_endpoint(person_id_param: uuid.UUID):
    if 'file' not in request.files:
        abort(400, description="No file part in the request.") # Use description for consistency
    file = request.files['file']
    if file.filename == '':
        abort(400, description="No selected file.")

    # db session and tree_id are set by @require_tree_access or a general before_request hook
    db_session = g.db
    active_tree_id = g.active_tree_id 
    
    # Ensure user_id is available in session and convert to UUID
    if 'user_id' not in session:
        logger.warning("User ID not found in session for profile picture upload.")
        abort(401, description="Authentication required.")
    try:
        current_user_id = uuid.UUID(session['user_id'])
    except ValueError:
        logger.error("Invalid user_id format in session.", session_user_id=session['user_id'])
        abort(400, description="Invalid user identifier in session.")


    logger.info("Upload profile picture endpoint", person_id=person_id_param, tree_id=active_tree_id, user_id=current_user_id, filename=file.filename)
    try:
        updated_person_dict = upload_profile_picture_db(
            db=db_session,
            person_id=person_id_param,
            tree_id=active_tree_id,
            user_id=current_user_id, 
            file_stream=file.stream, 
            filename=file.filename, # Filename is used by service for extension and sanitization
            content_type=file.content_type
        )
        return jsonify(updated_person_dict), 200
    except HTTPException as e: # Re-raise HTTPExceptions (aborts from service or here)
        raise
    except Exception as e:
        logger.error("Error uploading profile picture.", person_id=person_id_param, exc_info=True)
        abort(500, description="An error occurred while uploading the profile picture.")
    return {} # Should be unreachable


@people_bp.route('/<uuid:person_id_param>/media', methods=['GET'])
@require_auth
@require_tree_access('view')
def get_person_media_endpoint(person_id_param: uuid.UUID):
    db_session = g.db
    active_tree_id = uuid.UUID(g.active_tree_id) # Ensure it's UUID

    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by if sort_by else "created_at"
    sort_order = sort_order if sort_order else "desc"

    logger.info("Get media for person endpoint", tree_id=active_tree_id, person_id=person_id_param,
                page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
    try:
        media_list_dict = get_media_for_entity_db(
            db_session, active_tree_id, "Person", person_id_param,
            page, per_page, sort_by, sort_order
        )
        return jsonify(media_list_dict), 200
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in get_person_media_endpoint", exc_info=True)
        abort(500, description="Error fetching media for person.")
    return {}
