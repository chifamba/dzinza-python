# backend/blueprints/relationships.py
"""This module defines the Flask blueprint for API endpoints related to
relationships within a family tree, requiring tree access.
"""
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
    """
    Retrieves a paginated list of relationships for the active tree.
    Requires 'view' access to the tree. Supports filtering by person_id
    and relationship_type.
    """
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
    """
    Retrieves details of a specific relationship by ID within the active tree.
    Requires 'view' access to the tree.
    """
    db = g.db; tree_id = g.active_tree_id
    logger.info("Get relationship", relationship_id=relationship_id_param, tree_id=tree_id)
    try:
        return jsonify(get_relationship_db(db, relationship_id_param, tree_id)), 200
    except Exception as e:
        logger.error("Error in get_relationship.", relationship_id=relationship_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching relationship details.")
        raise

@relationships_bp.route('', methods=['POST'])
@require_tree_access('edit')
def create_relationship_endpoint():
    """
    Creates a new relationship in the active tree.
    Requires 'edit' access to the tree.
    """
    data = request.get_json(); user_id = uuid.UUID(session['user_id'])
    if not data: abort(400, "Request body cannot be empty.")
    db = g.db; tree_id = g.active_tree_id
    logger.info("Create relationship", tree_id=tree_id, user_id=user_id, data_keys=list(data.keys()))
    try:
        return jsonify(create_relationship_db(db, user_id, tree_id, data)), 201
    except Exception as e:
        logger.error("Error in create_relationship.", tree_id=tree_id, user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error creating relationship.")
        raise

@relationships_bp.route('/<uuid:relationship_id_param>', methods=['PUT'])
@require_tree_access('edit')
def update_relationship_endpoint(relationship_id_param: uuid.UUID):
    """
    Updates an existing relationship by ID within the active tree.
    Requires 'edit' access to the tree.
    """
    data = request.get_json()
    if not data: abort(400, "Request body cannot be empty.")
    db = g.db; tree_id = g.active_tree_id
    logger.info("Update relationship", relationship_id=relationship_id_param, tree_id=tree_id, data_keys=list(data.keys()))
    try:
        return jsonify(update_relationship_db(db, relationship_id_param, tree_id, data)), 200
    except Exception as e:
        logger.error("Error in update_relationship.", relationship_id=relationship_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error updating relationship.")
        raise

@relationships_bp.route('/<uuid:relationship_id_param>', methods=['DELETE'])
@require_tree_access('edit')
def delete_relationship_endpoint(relationship_id_param: uuid.UUID):
    """
    Deletes a relationship by ID from the active tree.
    Requires 'edit' access to the tree.
    """
    db = g.db; tree_id = g.active_tree_id
    logger.info("Delete relationship", relationship_id=relationship_id_param, tree_id=tree_id)
    try:
        delete_relationship_db(db, relationship_id_param, tree_id)
        return '', 204
    except Exception as e:
        logger.error("Error in delete_relationship.", relationship_id=relationship_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error deleting relationship.")
        raise
