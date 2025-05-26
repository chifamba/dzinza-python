# backend/blueprints/trees.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from werkzeug.exceptions import HTTPException

from decorators import require_auth, require_tree_access
from services.tree_service import (
    create_tree_db, get_user_trees_db,
    get_tree_data_for_visualization_db,
    upload_tree_cover_image_db,
    add_person_to_tree_db, remove_person_from_tree_db # Added new services
)
from services.media_service import get_media_for_entity_db # Added for tree media
from services.event_service import get_events_for_tree_db # Added for tree events
from utils import get_pagination_params
# werkzeug.utils.secure_filename is imported in service now
from extensions import limiter
from models import Tree, TreeAccess, TreePrivacySettingEnum # For direct query in set_active_tree, added TreePrivacySettingEnum explicitly

logger = structlog.get_logger(__name__)
trees_bp = Blueprint('trees_api', __name__, url_prefix='/api') # Base prefix /api

@trees_bp.route('/trees', methods=['POST'])
@require_auth
def create_tree_endpoint():
    data = request.get_json()
    if not data: abort(400, "Request body cannot be empty.")
    user_id = uuid.UUID(session['user_id']); db = g.db
    logger.info("Create tree", user_id=user_id, data_keys=list(data.keys()))
    try:
        new_tree = create_tree_db(db, user_id, data)
        session['active_tree_id'] = str(new_tree['id'])
        logger.info(f"New tree {new_tree['id']} set as active for user {user_id}")
        return jsonify(new_tree), 201
    except Exception as e:
        logger.error("Error creating tree.", user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error creating tree.")
        raise

@trees_bp.route('/trees', methods=['GET'])
@require_auth
def get_user_trees_endpoint():
    user_id = uuid.UUID(session['user_id']); db = g.db
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "name"; sort_order = sort_order or "asc"
    logger.info("Get user trees", user_id=user_id, page=page, per_page=per_page)
    try:
        return jsonify(get_user_trees_db(db, user_id, page, per_page, sort_by, sort_order)), 200
    except Exception as e:
        logger.error("Error fetching user trees.", user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching user's trees.")
        raise

@trees_bp.route('/session/active_tree', methods=['PUT'])
@require_auth
def set_active_tree_endpoint():
    data = request.get_json()
    if not data or 'tree_id' not in data: abort(400, "tree_id is required.")
    tree_id_str = data['tree_id']; user_id = uuid.UUID(session['user_id']); db = g.db
    try: tree_id_uuid = uuid.UUID(tree_id_str)
    except ValueError: abort(400, "Invalid UUID for tree_id.")
    tree = db.query(Tree).filter(Tree.id == tree_id_uuid).one_or_none() # Tree model should have privacy_setting now
    if not tree: abort(404, f"Tree with ID {tree_id_str} not found.")
    can_set_active = False
    # Updated to use privacy_setting
    if tree.created_by == user_id or tree.privacy_setting == TreePrivacySettingEnum.PUBLIC: 
        can_set_active = True
    else:
        if db.query(TreeAccess).filter(TreeAccess.tree_id == tree_id_uuid, TreeAccess.user_id == user_id).first():
            can_set_active = True
    if not can_set_active: abort(403, f"No permission to access tree {tree_id_str}.")
    session['active_tree_id'] = tree_id_str
    logger.info("Active tree set.", user_id=user_id, tree_id=tree_id_str)
    return jsonify({"message": "Active tree set.", "active_tree_id": tree_id_str}), 200

@trees_bp.route('/tree_data', methods=['GET'])
@require_tree_access('view')
@limiter.limit("600 per minute")  # Increased from 10 to 60 requests per minute
def get_tree_data_endpoint():
    db = g.db; tree_id = g.active_tree_id
    logger.info("Get tree_data for visualization", tree_id=tree_id)
    try:
        return jsonify(get_tree_data_for_visualization_db(db, tree_id)), 200
    except Exception as e:
        logger.error("Error fetching tree_data for viz.", tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching tree data for visualization.")
        raise

@trees_bp.route('/trees/<uuid:tree_id_param>/cover_image', methods=['POST'])
@require_auth 
# The service layer currently checks if user_id == tree.created_by.
# If more complex roles (e.g. admin from TreeAccess) should be allowed,
# @require_tree_access('edit') or similar would be more appropriate here,
# and the service layer check might need adjustment or removal.
def upload_tree_cover_image_endpoint(tree_id_param: uuid.UUID):
    if 'file' not in request.files:
        abort(400, description="No file part in the request.")
    file = request.files['file']
    if file.filename == '':
        abort(400, description="No selected file.")

    db_session = g.db # db session from global context
    
    if 'user_id' not in session:
        logger.warning("User ID not found in session for tree cover image upload.")
        abort(401, description="Authentication required.")
    try:
        current_user_id = uuid.UUID(session['user_id'])
    except ValueError:
        logger.error("Invalid user_id format in session.", session_user_id=session['user_id'])
        abort(400, description="Invalid user identifier in session.")

    logger.info("Upload tree cover image endpoint", tree_id=tree_id_param, user_id=current_user_id, filename=file.filename)
    try:
        updated_tree_dict = upload_tree_cover_image_db(
            db=db_session,
            tree_id=tree_id_param,
            user_id=current_user_id,
            file_stream=file.stream,
            filename=file.filename,
            content_type=file.content_type
        )
        return jsonify(updated_tree_dict), 200
    except HTTPException as e: # Re-raise HTTPExceptions (aborts from service or here)
        raise
    except Exception as e:
        logger.error("Error uploading tree cover image.", tree_id=tree_id_param, exc_info=True)
        abort(500, description="An error occurred while uploading the tree cover image.")
    return {} # Should be unreachable


@trees_bp.route('/trees/<uuid:tree_id_param>/media', methods=['GET'])
@require_auth
@require_tree_access('view')
def get_tree_media_endpoint(tree_id_param: uuid.UUID):
    db_session = g.db
    # active_tree_id from g should match tree_id_param due to @require_tree_access
    # but we use tree_id_param as it's the specific subject of this request.
    active_tree_id = uuid.UUID(g.active_tree_id)
    if active_tree_id != tree_id_param:
        logger.warning("Mismatch between active_tree_id in session and tree_id_param in URL for get_tree_media_endpoint.",
                       active_tree_id_session=str(active_tree_id), tree_id_url=str(tree_id_param))
        abort(400, "URL tree ID does not match active tree context.")


    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by if sort_by else "created_at"
    sort_order = sort_order if sort_order else "desc"

    logger.info("Get media for tree endpoint", tree_id=tree_id_param,
                page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
    try:
        media_list_dict = get_media_for_entity_db(
            db=db_session, 
            entity_type="Tree", 
            entity_id=tree_id_param, 
            page=page, per_page=per_page, 
            sort_by=sort_by, sort_order=sort_order,
            tree_id_context=tree_id_param # Pass tree_id_param as tree_id_context
        )
        return jsonify(media_list_dict), 200
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in get_tree_media_endpoint", exc_info=True)
        abort(500, description="Error fetching media for tree.")
    return {}

@trees_bp.route('/trees/<uuid:tree_id_param>/events', methods=['GET'])
@require_auth
@require_tree_access('view')
def get_tree_events_endpoint(tree_id_param: uuid.UUID):
    db_session = g.db
    active_tree_id = uuid.UUID(g.active_tree_id) # Ensure it's UUID
    
    if active_tree_id != tree_id_param: # Should be guaranteed by @require_tree_access if tree_id_param is used by it
        logger.warning("Mismatch between active_tree_id in session and tree_id_param in URL for get_tree_events_endpoint.",
                       active_tree_id_session=str(active_tree_id), tree_id_url=str(tree_id_param))
        abort(400, "URL tree ID does not match active tree context.")

    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by if sort_by else "date" 
    sort_order = sort_order if sort_order else "asc"
    
    # Example filter: by event_type
    filters = {}
    if 'event_type' in request.args:
        filters['event_type'] = request.args.get('event_type')

    logger.info("Get events for tree endpoint", tree_id=tree_id_param, page=page, per_page=per_page, 
                sort_by=sort_by, sort_order=sort_order, filters=filters)
    try:
        events_list_dict = get_events_for_tree_db(
            db_session, tree_id_param,
            page, per_page, sort_by, sort_order, filters=filters
        )
        return jsonify(events_list_dict), 200
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in get_tree_events_endpoint", exc_info=True)
        abort(500, description="Error fetching events for tree.")
    return {}


# --- New Endpoints for Person-Tree Association ---

@trees_bp.route('/trees/<uuid:tree_id_param>/persons', methods=['POST'])
@require_auth
@require_tree_access('edit') # Or 'admin' depending on desired permission level
def add_person_to_tree_route(tree_id_param: uuid.UUID):
    """Adds an existing global person to a specific tree."""
    db = g.db
    current_user_id = uuid.UUID(session['user_id'])
    active_tree_id = uuid.UUID(g.active_tree_id) # from @require_tree_access

    if active_tree_id != tree_id_param:
        abort(400, "URL tree ID does not match active tree context set by decorator.")

    data = request.get_json()
    if not data or 'person_id' not in data:
        abort(400, description="Missing 'person_id' in request body.")
    
    try:
        person_id_to_add = uuid.UUID(data['person_id'])
    except ValueError:
        abort(400, description="Invalid 'person_id' format.")

    logger.info("Adding person to tree", tree_id=tree_id_param, person_id_to_add=person_id_to_add, current_user_id=current_user_id)
    try:
        result = add_person_to_tree_db(db, person_id_to_add, tree_id_param, current_user_id)
        # The service returns a dict with message and possibly person_id, tree_id.
        # If it returns a specific "already associated" message, we might want a different status code like 200.
        if result.get("message") == "Person already associated with this tree.":
            return jsonify(result), 200 
        return jsonify(result), 201 # 201 Created for new association
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding person to tree.", tree_id=tree_id_param, person_id=person_id_to_add, exc_info=True)
        abort(500, "Could not add person to the tree.")

@trees_bp.route('/trees/<uuid:tree_id_param>/persons/<uuid:person_id_to_remove>', methods=['DELETE'])
@require_auth
@require_tree_access('edit') # Or 'admin'
def remove_person_from_tree_route(tree_id_param: uuid.UUID, person_id_to_remove: uuid.UUID):
    """Removes a person's association from a specific tree."""
    db = g.db
    current_user_id = uuid.UUID(session['user_id'])
    active_tree_id = uuid.UUID(g.active_tree_id) # from @require_tree_access

    if active_tree_id != tree_id_param:
        abort(400, "URL tree ID does not match active tree context set by decorator.")

    logger.info("Removing person from tree", tree_id=tree_id_param, person_id_to_remove=person_id_to_remove, current_user_id=current_user_id)
    try:
        if remove_person_from_tree_db(db, person_id_to_remove, tree_id_param, current_user_id):
            return '', 204 # No content, successful deletion
        else:
            # This path should ideally not be reached if service uses aborts for failures.
            abort(500, "Failed to remove person from tree for an unknown reason.") 
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error removing person from tree.", tree_id=tree_id_param, person_id=person_id_to_remove, exc_info=True)
        abort(500, "Could not remove person from the tree.")
