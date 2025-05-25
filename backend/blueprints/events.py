# backend/blueprints/events.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from werkzeug.exceptions import HTTPException

from decorators import require_auth, require_tree_access
from services.event_service import (
    create_event_db, get_event_db, update_event_db, delete_event_db,
    get_events_for_person_db, get_events_for_tree_db # Ensure these are available if routes are added
)
from utils import get_pagination_params

logger = structlog.get_logger(__name__)
events_bp = Blueprint('events_api', __name__, url_prefix='/api/events')

# Helper to safely convert string to UUID, can be moved to a shared utils if used often
def _to_uuid_or_abort(s_uuid: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(s_uuid)
    except ValueError:
        abort(400, description=f"Invalid UUID format for {field_name}: {s_uuid}")
    # This line is unreachable due to abort but satisfies type checker if needed
    raise # Should not happen

@events_bp.route('', methods=['POST'])
@require_auth
@require_tree_access('edit')
def create_event_endpoint():
    data = request.get_json()
    if not data:
        abort(400, description="Request body cannot be empty.")

    db_session = g.db
    user_id = _to_uuid_or_abort(session['user_id'], "user_id in session")
    active_tree_id = _to_uuid_or_abort(g.active_tree_id, "active_tree_id in g")

    logger.info("Create event endpoint", user_id=user_id, active_tree_id_context=active_tree_id, data_keys=list(data.keys()))
    # active_tree_id is available from @require_tree_access for context if needed (e.g. validating person_id in data belongs to this tree)
    # However, create_event_db service function no longer takes tree_id as Event is global.
    # Authorization to create an event for a person might depend on user's access to that person (via any tree).
    
    try:
        # Ensure person_id in data is valid and user has rights to create event for them (complex auth for Phase 4)
        # For now, service create_event_db takes (db, user_id, event_data)
        event_dict = create_event_db(db_session, user_id, data)
        return jsonify(event_dict), 201
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in create_event_endpoint", exc_info=True)
        abort(500, description="Error creating event.")
    return {} # Should be unreachable

@events_bp.route('/<uuid:event_id_param>', methods=['GET'])
@require_auth
@require_tree_access('view')
def get_event_endpoint(event_id_param: uuid.UUID):
    db_session = g.db
    active_tree_id = _to_uuid_or_abort(g.active_tree_id, "active_tree_id in g") # Context for auth
    
    logger.info("Get event endpoint", event_id=event_id_param, active_tree_id_context=active_tree_id)
    # Event is global, but @require_tree_access ensures user has some tree context.
    # Actual authorization: can user view this specific event? (Phase 4)
    # For now, service get_event_db fetches globally.
    try:
        event_dict = get_event_db(db_session, event_id_param)
        return jsonify(event_dict), 200
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in get_event_endpoint", exc_info=True)
        abort(500, description="Error fetching event details.")
    return {}

@events_bp.route('/<uuid:event_id_param>', methods=['PUT'])
@require_auth
@require_tree_access('edit')
def update_event_endpoint(event_id_param: uuid.UUID):
    data = request.get_json()
    if not data:
        abort(400, description="Request body cannot be empty.")

    db_session = g.db
    active_tree_id = _to_uuid_or_abort(g.active_tree_id, "active_tree_id in g") # Context for auth
    # user_id from session could be used for auditing if needed in service layer for update (service should take it)
    # current_user_id = _to_uuid_or_abort(session['user_id'], "user_id in session")

    logger.info("Update event endpoint", event_id=event_id_param, active_tree_id_context=active_tree_id, data_keys=list(data.keys()))
    # Event is global. @require_tree_access provides a tree context for authorization.
    # Authorization: Can user edit this event? (Phase 4)
    # Service update_event_db takes (db, event_id, event_data)
    try:
        # Pass actor_user_id to service if service supports it for auditing
        event_dict = update_event_db(db_session, event_id_param, data) # Removed active_tree_id
        return jsonify(event_dict), 200
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in update_event_endpoint", exc_info=True)
        abort(500, description="Error updating event.")
    return {}

@events_bp.route('/<uuid:event_id_param>', methods=['DELETE'])
@require_auth
@require_tree_access('edit')
def delete_event_endpoint(event_id_param: uuid.UUID):
    db_session = g.db
    active_tree_id = _to_uuid_or_abort(g.active_tree_id, "active_tree_id in g") # Context for auth
    # user_id from session could be used for auditing if needed in service layer for delete
    # current_user_id = _to_uuid_or_abort(session['user_id'], "user_id in session")

    logger.info("Delete event endpoint", event_id=event_id_param, active_tree_id_context=active_tree_id)
    # Event is global. @require_tree_access provides a tree context for authorization.
    # Authorization: Can user delete this event? (Phase 4)
    # Service delete_event_db takes (db, event_id)
    try:
        # Pass actor_user_id to service if service supports it for auditing
        success = delete_event_db(db_session, event_id_param) # Removed active_tree_id
        if success:
            return '', 204
        else:
            # This path should ideally not be reached if service layer aborts on failure
            logger.warning("delete_event_db returned False without aborting", event_id=event_id_param)
            abort(500, description="Deletion failed for an unknown reason.")
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("Error in delete_event_endpoint", exc_info=True)
        abort(500, description="Error deleting event.")
    return {}
