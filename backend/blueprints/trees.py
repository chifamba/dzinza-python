# backend/blueprints/trees.py
"""
This file defines the Flask blueprint for API endpoints related to family trees.
Requires user authentication and/or specific tree access.
"""
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from werkzeug.exceptions import HTTPException

from decorators import require_auth, require_tree_access
from services.tree_service import (
    create_tree_db, get_user_trees_db,
    get_tree_data_for_visualization_db
)
from utils import get_pagination_params
from extensions import limiter
from models import Tree, TreeAccess # For direct query in set_active_tree

logger = structlog.get_logger(__name__)
trees_bp = Blueprint('trees_api', __name__, url_prefix='/api') # Base prefix /api

@trees_bp.route('/trees', methods=['POST'])
@require_auth
def create_tree_endpoint():
    """
    POST /api/trees
    Creates a new family tree for the authenticated user. Requires authentication.
    """
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
    """
    GET /api/trees
    Retrieves a paginated list of trees that the authenticated user has access to. Requires authentication.
    """
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
    """
    PUT /api/session/active_tree
    Sets the active tree for the current session. Requires authentication and access to the specified tree.
    """
    data = request.get_json()
    if not data or 'tree_id' not in data: abort(400, "tree_id is required.")
    tree_id_str = data['tree_id']; user_id = uuid.UUID(session['user_id']); db = g.db
    try: tree_id_uuid = uuid.UUID(tree_id_str)
    except ValueError: abort(400, "Invalid UUID for tree_id.")
    tree = db.query(Tree).filter(Tree.id == tree_id_uuid).one_or_none()
    if not tree: abort(404, f"Tree with ID {tree_id_str} not found.")
    can_set_active = False
    if tree.created_by == user_id or tree.is_public: can_set_active = True
    else:
        if db.query(TreeAccess).filter(TreeAccess.tree_id == tree_id_uuid, TreeAccess.user_id == user_id).first():
            can_set_active = True
    if not can_set_active: abort(403, f"No permission to access tree {tree_id_str}.")
    session['active_tree_id'] = tree_id_str
    logger.info("Active tree set.", user_id=user_id, tree_id=tree_id_str)
    return jsonify({"message": "Active tree set.", "active_tree_id": tree_id_str}), 200

@trees_bp.route('/tree_data', methods=['GET'])
@require_tree_access('view')
@limiter.limit("10 per minute")
"""
    GET /api/tree_data
    Retrieves data for the currently active tree, formatted for visualization.
    Requires 'view' access to the active tree.
"""
def get_tree_data_endpoint():
    db = g.db; tree_id = g.active_tree_id
    logger.info("Get tree_data for visualization", tree_id=tree_id)
    try:
        return jsonify(get_tree_data_for_visualization_db(db, tree_id)), 200
    except Exception as e:
        logger.error("Error fetching tree_data for viz.", tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching tree data for visualization.")
        raise
