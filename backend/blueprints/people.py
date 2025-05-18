# backend/blueprints/people.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort

from ..decorators import require_tree_access
from ..services.person_service import (
    get_all_people_db, get_person_db, create_person_db,
    update_person_db, delete_person_db
)
from ..utils import get_pagination_params

logger = structlog.get_logger(__name__)
# The tree_id_param will be part of the URL prefix for these routes
# For example, a tree-specific people endpoint could be /api/trees/<uuid:tree_id_param>/people
# However, the current require_tree_access decorator uses active_tree_id from session
# if tree_id_param is not in the path.
# For clarity, it's better if tree-specific resources always have tree_id in the path.
# Let's assume for now that active_tree_id from session is primary,
# and specific tree_id in path can override or be used by decorator.

# If we want all people routes to be nested under a tree:
# people_bp = Blueprint('people_api', __name__, url_prefix='/api/trees/<uuid:tree_id_param>/people')
# Then the decorator would pick up tree_id_param.
# For now, using /api/people and relying on active_tree_id from session primarily.
people_bp = Blueprint('people_api', __name__, url_prefix='/api/people')


@people_bp.route('', methods=['GET'])
@require_tree_access('view') # Decorator uses g.active_tree_id set from session
def get_all_people_endpoint():
    db = g.db
    tree_id = g.active_tree_id # Set by require_tree_access
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "last_name"

    filters = {}
    is_living_filter = request.args.get('is_living', type=str)
    if is_living_filter is not None:
        filters['is_living'] = is_living_filter.lower() == 'true'
    
    name_contains_filter = request.args.get('name_contains', type=str)
    if name_contains_filter:
        filters['name_contains'] = name_contains_filter

    logger.info("Get all people request", tree_id=tree_id, page=page, per_page=per_page, filters=filters)
    try:
        people_page = get_all_people_db(db, tree_id, page, per_page, sort_by, sort_order, filters=filters)
        return jsonify(people_page), 200
    except Exception as e:
        logger.error("Unexpected error in get_all_people endpoint.", tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error fetching people.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['GET'])
@require_tree_access('view') # tree_id_param is not used by decorator here, relies on g.active_tree_id
def get_person_endpoint(person_id_param: uuid.UUID):
    db = g.db
    tree_id = g.active_tree_id # From decorator
    
    logger.info("Get person request", person_id=person_id_param, tree_id=tree_id)
    try:
        # Service function get_person_db needs tree_id to ensure person is in the correct tree
        person_details = get_person_db(db, person_id_param, tree_id)
        return jsonify(person_details), 200
    except Exception as e:
        logger.error("Unexpected error in get_person endpoint.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error fetching person details.")
        raise

@people_bp.route('', methods=['POST'])
@require_tree_access('edit')
def create_person_endpoint():
    data = request.get_json()
    if not data: abort(400, description="Request body cannot be empty.")
    
    user_id = uuid.UUID(session['user_id'])
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    logger.info("Create person request", tree_id=tree_id, user_id=user_id, data_keys=list(data.keys()))
    try:
        new_person_obj = create_person_db(db, user_id, tree_id, data)
        return jsonify(new_person_obj), 201
    except Exception as e:
        logger.error("Unexpected error in create_person endpoint.", tree_id=tree_id, user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error creating person.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['PUT'])
@require_tree_access('edit')
def update_person_endpoint(person_id_param: uuid.UUID):
    data = request.get_json()
    if not data: abort(400, description="Request body cannot be empty.")
    
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    logger.info("Update person request", person_id=person_id_param, tree_id=tree_id, data_keys=list(data.keys()))
    try:
        updated_person_obj = update_person_db(db, person_id_param, tree_id, data)
        return jsonify(updated_person_obj), 200
    except Exception as e:
        logger.error("Unexpected error in update_person endpoint.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error updating person.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['DELETE'])
@require_tree_access('edit')
def delete_person_endpoint(person_id_param: uuid.UUID):
    tree_id = g.active_tree_id # From decorator
    db = g.db
    
    logger.info("Delete person request", person_id=person_id_param, tree_id=tree_id)
    try:
        delete_person_db(db, person_id_param, tree_id)
        return '', 204
    except Exception as e:
        logger.error("Unexpected error in delete_person endpoint.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error deleting person.")
        raise
