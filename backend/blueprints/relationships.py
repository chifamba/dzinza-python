# backend/blueprints/relationships.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort

from ..decorators import require_tree_access
from ..services.relationship_service import (
    get_all_relationships_db, get_relationship_db, create_relationship_db,
    update_relationship_db, delete_relationship_db
)
from ..utils import get_pagination_params

logger = structlog.get_logger(__name__)
relationships_bp = Blueprint('relationships_api', __name__, url_prefix='/api/relationships')

@relationships_bp.route('', methods=['GET'])
@require_tree_access('view') # Relies on g.active_tree_id from session
def get_all_relationships_endpoint():
    db = g.db
    tree_id = g.active_tree_id
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "created_at"
    sort_order = sort_order or "desc"

    filters = {}
    person_id_filter = request.args.get('person_id', type=str)
    if person_id_filter: filters['person_id'] = person_id_filter
    rel_type_filter = request.args.get('relationship_type', type=str)
    if rel_type_filter: filters['relationship_type'] = rel_type_filter
    
    logger.info("Get all relationships request", tree_id=tree_id, page=page, per_page=per_page, filters=filters)
    try:
        relationships_page = get_all_relationships_db(db, tree_id, page, per_page, sort_by, sort_order, filters=filters)
        return jsonify(relationships_page), 200
    except Exception as e:
        logger.error("Unexpected error in get_all_relationships endpoint.", tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error fetching relationships.")
        raise

@relationships_bp.route('/<uuid:relationship_id_param>', methods=['GET'])
@require_tree_access('view')
def get_relationship_endpoint(relationship_id_param: uuid.UUID):
    db = g.db
    tree_id = g.active_tree_id
    logger.info("Get relationship request", relationship_id=relationship_id_param, tree_id=tree_id)
    try:
        relationship_details = get_relationship_db(db, relationship_id_param, tree_id)
        return jsonify(relationship_details), 200
    except Exception as e:
        logger.error("Unexpected error in get_relationship endpoint.", relationship_id=relationship_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error fetching relationship details.")
        raise

@relationships_bp.route('', methods=['POST'])
@require_tree_access('edit')
def create_relationship_endpoint():
    data = request.get_json()
    if not data: abort(400, description="Request body cannot be empty.")
    
    user_id = uuid.UUID(session['user_id'])
    tree_id = g.active_tree_id
    db = g.db
    
    logger.info("Create relationship request", tree_id=tree_id, user_id=user_id, data_keys=list(data.keys()))
    try:
        # Ensure payload keys match service expectations (e.g., person1_id, relationship_type)
        new_relationship_obj = create_relationship_db(db, user_id, tree_id, data)
        return jsonify(new_relationship_obj), 201
    except Exception as e:
        logger.error("Unexpected error in create_relationship endpoint.", tree_id=tree_id, user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error creating relationship.")
        raise

@relationships_bp.route('/<uuid:relationship_id_param>', methods=['PUT'])
@require_tree_access('edit')
def update_relationship_endpoint(relationship_id_param: uuid.UUID):
    data = request.get_json()
    if not data: abort(400, description="Request body cannot be empty.")
    
    tree_id = g.active_tree_id
    db = g.db
    
    logger.info("Update relationship request", relationship_id=relationship_id_param, tree_id=tree_id, data_keys=list(data.keys()))
    try:
        updated_relationship_obj = update_relationship_db(db, relationship_id_param, tree_id, data)
        return jsonify(updated_relationship_obj), 200
    except Exception as e:
        logger.error("Unexpected error in update_relationship endpoint.", relationship_id=relationship_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error updating relationship.")
        raise

@relationships_bp.route('/<uuid:relationship_id_param>', methods=['DELETE'])
@require_tree_access('edit')
def delete_relationship_endpoint(relationship_id_param: uuid.UUID):
    tree_id = g.active_tree_id
    db = g.db
    
    logger.info("Delete relationship request", relationship_id=relationship_id_param, tree_id=tree_id)
    try:
        delete_relationship_db(db, relationship_id_param, tree_id)
        return '', 204
    except Exception as e:
        logger.error("Unexpected error in delete_relationship endpoint.", relationship_id=relationship_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error deleting relationship.")
        raise
