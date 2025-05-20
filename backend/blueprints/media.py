# backend/blueprints/media.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from werkzeug.exceptions import HTTPException

# Assuming your decorators and services are importable
from decorators import require_auth, require_tree_access 
from services.media_service import (
    get_media_item_db,
    upload_media_item_db, # Renamed from create_media_item_record_db
    delete_media_item_db, # Added
    get_media_for_entity_db
)
from models import MediaTypeEnum # For parsing optional file_type from form
from utils import get_pagination_params

logger = structlog.get_logger(__name__)
media_bp = Blueprint('media_api', __name__, url_prefix='/api/media')

# Helper to safely convert string to UUID
def _to_uuid(s_uuid: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(s_uuid)
    except ValueError:
        abort(400, description=f"Invalid UUID format for {field_name}: {s_uuid}")
    return uuid.uuid4() # Should be unreachable due to abort

@media_bp.route('/<uuid:media_id_param>', methods=['GET'])
@require_auth
@require_tree_access('view') # Requires tree_id context, ensure decorator handles it or it's set in g
def get_media_item_endpoint(media_id_param: uuid.UUID):
    db_session = g.db
    active_tree_id = g.active_tree_id # Assuming require_tree_access sets this
    logger.info("Get media item endpoint", media_id=media_id_param, tree_id=active_tree_id)
    try:
        media_item_dict = get_media_item_db(db_session, media_id_param, active_tree_id)
        return jsonify(media_item_dict), 200
    except HTTPException as e: # Propagate HTTP exceptions (like 404 from _get_or_404)
        raise
    except Exception as e:
        logger.error("Error in get_media_item_endpoint", exc_info=True)
        abort(500, description="Error fetching media item.")
    return {} # Should be unreachable

@media_bp.route('', methods=['POST'])
@require_auth
@require_tree_access('edit') 
def upload_media_item_endpoint():
    if 'file' not in request.files:
        abort(400, description="No file part in the request.")
    file = request.files['file']
    if file.filename == '':
        abort(400, description="No selected file.")

    # Get form data
    linked_entity_type = request.form.get('linked_entity_type')
    linked_entity_id_str = request.form.get('linked_entity_id')
    caption = request.form.get('caption')
    file_type_str = request.form.get('file_type') # Optional, service will infer if not provided

    if not linked_entity_type:
        abort(400, description="Missing required form field: linked_entity_type")
    if not linked_entity_id_str:
        abort(400, description="Missing required form field: linked_entity_id")

    linked_entity_id = _to_uuid(linked_entity_id_str, "linked_entity_id")
    
    file_type_enum: MediaTypeEnum | None = None
    if file_type_str:
        try:
            file_type_enum = MediaTypeEnum(file_type_str)
        except ValueError:
            abort(400, description=f"Invalid file_type: {file_type_str}. Valid values: {[e.value for e in MediaTypeEnum]}")

    db_session = g.db
    uploader_user_id = _to_uuid(session['user_id'], "user_id in session")
    active_tree_id = _to_uuid(g.active_tree_id, "active_tree_id in g")


    logger.info("Upload media item endpoint", user_id=uploader_user_id, tree_id=active_tree_id, 
                linked_entity_type=linked_entity_type, linked_entity_id=linked_entity_id, filename=file.filename)
    
    try:
        media_item_dict = upload_media_item_db(
            db=db_session,
            user_id=uploader_user_id,
            tree_id=active_tree_id,
            linked_entity_type=linked_entity_type,
            linked_entity_id=linked_entity_id,
            file_stream=file.stream,
            filename=file.filename,
            content_type=file.content_type or 'application/octet-stream', # Default content_type
            caption=caption,
            file_type_enum_provided=file_type_enum
        )
        return jsonify(media_item_dict), 201
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in upload_media_item_endpoint", exc_info=True)
        abort(500, description="Error uploading media item.")
    return {}


@media_bp.route('/<uuid:media_id_param>', methods=['DELETE'])
@require_auth
@require_tree_access('edit') # Or more granular (e.g. uploader or tree admin) checked in service
def delete_media_item_endpoint(media_id_param: uuid.UUID):
    db_session = g.db
    current_user_id = _to_uuid(session['user_id'], "user_id in session")
    active_tree_id = _to_uuid(g.active_tree_id, "active_tree_id in g") # For consistency, service uses it

    logger.info("Delete media item endpoint", media_id=media_id_param, user_id=current_user_id, tree_id=active_tree_id)
    try:
        success = delete_media_item_db(db_session, media_id_param, current_user_id, active_tree_id)
        if success:
            return '', 204
        else:
            # This case should ideally be handled by aborts in the service layer
            logger.warning("delete_media_item_db returned False without aborting", media_id=media_id_param)
            abort(500, description="Deletion failed for an unknown reason.") 
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in delete_media_item_endpoint", exc_info=True)
        abort(500, description="Error deleting media item.")
    return {}


@media_bp.route('/entity/<string:entity_type>/<uuid:entity_id_param>', methods=['GET'])
@require_auth
@require_tree_access('view')
def get_media_for_entity_endpoint(entity_type: str, entity_id_param: uuid.UUID):
    db_session = g.db
    active_tree_id = g.active_tree_id
    
    page, per_page, sort_by, sort_order = get_pagination_params()
    # Default sort_by for media, could be 'created_at' or 'file_name'
    sort_by = sort_by if sort_by else "created_at" 
    sort_order = sort_order if sort_order else "desc"

    logger.info("Get media for entity endpoint", tree_id=active_tree_id, entity_type=entity_type, entity_id=entity_id_param,
                page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
    try:
        media_list_dict = get_media_for_entity_db(
            db_session, active_tree_id, entity_type, entity_id_param,
            page, per_page, sort_by, sort_order
        )
        return jsonify(media_list_dict), 200
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in get_media_for_entity_endpoint", exc_info=True)
        abort(500, description="Error fetching media for entity.")
    return {} # Should be unreachable
