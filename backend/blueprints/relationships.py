# backend/blueprints/relationships.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from werkzeug.exceptions import HTTPException

from decorators import require_tree_access
from services.relationship_service import (
    get_all_relationships_db, get_relationship_db, create_relationship_db,
    update_relationship_db, delete_relationship_db
)
from utils import get_pagination_params

logger = structlog.get_logger(__name__)
relationships_bp = Blueprint('relationships_api', __name__, url_prefix='/api/relationships')

@relationships_bp.route('', methods=['GET'])
@require_tree_access('view')
def get_all_relationships_endpoint():
    db = g.db; tree_id = g.active_tree_id
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "created_at"; sort_order = sort_order or "desc"
    filters = {}
    if request.args.get('person_id'): filters['person_id'] = request.args.get('person_id', type=str)
    if request.args.get('relationship_type'): filters['relationship_type'] = request.args.get('relationship_type', type=str)
    logger.info("Get all relationships", tree_id=tree_id, page=page, per_page=per_page, filters=filters)
    try:
        return jsonify(get_all_relationships_db(db, tree_id, page, per_page, sort_by, sort_order, filters=filters)), 200
    except Exception as e:
        logger.error("Error in get_all_relationships.", tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching relationships.")
        raise

@relationships_bp.route('/<uuid:relationship_id_param>', methods=['GET'])
@require_tree_access('view')
def get_relationship_endpoint(relationship_id_param: uuid.UUID):
    db = g.db
    active_tree_id = g.active_tree_id # For context/authorization via decorator
    logger.info("Get relationship", relationship_id=relationship_id_param, active_tree_id_context=active_tree_id)
    # Relationship is global, service fetches by ID. Tree context is for auth.
    try:
        return jsonify(get_relationship_db(db, relationship_id_param)), 200
    except Exception as e:
        logger.error("Error in get_relationship.", relationship_id=relationship_id_param, active_tree_id_context=active_tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching relationship details.")
        raise

@relationships_bp.route('', methods=['POST'])
@require_tree_access('edit')
def create_relationship_endpoint():
    data = request.get_json(); user_id = uuid.UUID(session['user_id'])
    if not data: abort(400, "Request body cannot be empty.")
    db = g.db
    active_tree_id = g.active_tree_id # Context for auth (e.g. are persons in this tree?)
    logger.info("Create relationship", active_tree_id_context=active_tree_id, user_id=user_id, data_keys=list(data.keys()))
    # Service create_relationship_db is global. Authorization to link persons might depend on active_tree_id.
    try:
        # Auth check: Ensure persons in data are part of active_tree_id before creating global relationship.
        # This logic should ideally be in the service or a shared auth layer.
        # For now, assume service handles validation if persons exist.
        return jsonify(create_relationship_db(db, user_id, data)), 201
    except Exception as e:
        logger.error("Error in create_relationship.", active_tree_id_context=active_tree_id, user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error creating relationship.")
        raise

@relationships_bp.route('/<uuid:relationship_id_param>', methods=['PUT'])
@require_tree_access('edit')
def update_relationship_endpoint(relationship_id_param: uuid.UUID):
    data = request.get_json()
    if not data: abort(400, "Request body cannot be empty.")
    db = g.db
    active_tree_id = g.active_tree_id # Context for auth
    logger.info("Update relationship", relationship_id=relationship_id_param, active_tree_id_context=active_tree_id, data_keys=list(data.keys()))
    # Service update_relationship_db is global. Auth check needed.
    try:
        return jsonify(update_relationship_db(db, relationship_id_param, data)), 200
    except Exception as e:
        logger.error("Error in update_relationship.", relationship_id=relationship_id_param, active_tree_id_context=active_tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error updating relationship.")
        raise

@relationships_bp.route('/<uuid:relationship_id_param>', methods=['DELETE'])
@require_tree_access('edit')
def delete_relationship_endpoint(relationship_id_param: uuid.UUID):
    db = g.db
    active_tree_id = g.active_tree_id # Context for auth
    logger.info("Delete relationship", relationship_id=relationship_id_param, active_tree_id_context=active_tree_id)
    # Service delete_relationship_db is global. Auth check needed.
    try:
        delete_relationship_db(db, relationship_id_param)
        return '', 204
    except Exception as e:
        logger.error("Error in delete_relationship.", relationship_id=relationship_id_param, active_tree_id_context=active_tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error deleting relationship.")
        raise
