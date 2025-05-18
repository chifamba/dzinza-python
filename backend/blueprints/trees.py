# backend/blueprints/trees.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort

from ..decorators import require_auth, require_tree_access # require_tree_access for /tree_data
from ..services.tree_service import (
    create_tree_db, get_user_trees_db,
    get_tree_data_for_visualization_db # Renamed for clarity
)
from ..services.user_service import get_all_users_db # Example if needed, though not typical for /trees
from ..utils import get_pagination_params
from ..extensions import limiter # Import limiter instance
from ..models import Tree, TreeAccess # For direct queries if needed (e.g. set_active_tree)

logger = structlog.get_logger(__name__)
trees_bp = Blueprint('trees_api', __name__, url_prefix='/api') # Base prefix /api

@trees_bp.route('/trees', methods=['POST'])
@require_auth
def create_tree_endpoint():
    data = request.get_json()
    if not data: abort(400, description="Request body cannot be empty.")
    
    user_id = uuid.UUID(session['user_id'])
    db = g.db
    logger.info("Create tree request", user_id=user_id, data_keys=list(data.keys()))
    try:
        new_tree = create_tree_db(db, user_id, data) # Service handles validation
        session['active_tree_id'] = str(new_tree['id'])
        logger.info(f"New tree {new_tree['id']} set as active for user {user_id}")
        return jsonify(new_tree), 201
    except Exception as e:
        logger.error("Unexpected error in create_tree endpoint.", user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error creating tree.")
        raise

@trees_bp.route('/trees', methods=['GET'])
@require_auth
def get_user_trees_endpoint():
    user_id = uuid.UUID(session['user_id'])
    db = g.db
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "name"
    sort_order = sort_order or "asc"
    
    logger.info("Get user trees request", user_id=user_id, page=page, per_page=per_page)
    try:
        trees_page = get_user_trees_db(db, user_id, page, per_page, sort_by, sort_order)
        return jsonify(trees_page), 200
    except Exception as e:
        logger.error("Unexpected error in get_user_trees endpoint.", user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error fetching user's trees.")
        raise

@trees_bp.route('/session/active_tree', methods=['PUT'])
@require_auth
def set_active_tree_endpoint():
    data = request.get_json()
    if not data or 'tree_id' not in data:
        abort(400, description="tree_id is required in the request body.")
    
    tree_id_str = data['tree_id']
    user_id = uuid.UUID(session['user_id'])
    db = g.db

    try:
        tree_id_uuid = uuid.UUID(tree_id_str)
    except ValueError:
        abort(400, description="Invalid UUID format for tree_id.")

    tree = db.query(Tree).filter(Tree.id == tree_id_uuid).one_or_none()
    if not tree:
        abort(404, description=f"Tree with ID {tree_id_str} not found.")

    # Verify user has access (owner, public, or via TreeAccess)
    can_set_active = False
    if tree.created_by == user_id or tree.is_public:
        can_set_active = True
    else:
        tree_access_obj = db.query(TreeAccess).filter(
            TreeAccess.tree_id == tree_id_uuid, TreeAccess.user_id == user_id
        ).first()
        if tree_access_obj: can_set_active = True
            
    if not can_set_active:
        abort(403, description=f"You do not have permission to access tree {tree_id_str}.")

    session['active_tree_id'] = tree_id_str
    logger.info("Active tree set in session.", user_id=user_id, tree_id=tree_id_str)
    return jsonify({"message": "Active tree set successfully.", "active_tree_id": tree_id_str}), 200

@trees_bp.route('/tree_data', methods=['GET']) # This implies active tree from session
@require_tree_access('view') # Ensures active tree is set and user has view access
@limiter.limit("10 per minute") # Stricter limit for this potentially heavy endpoint
def get_tree_data_endpoint():
    db = g.db
    tree_id = g.active_tree_id # Set by require_tree_access
    
    logger.info("Get tree_data request for visualization", tree_id=tree_id)
    try:
        tree_data_result = get_tree_data_for_visualization_db(db, tree_id)
        return jsonify(tree_data_result), 200
    except Exception as e:
        logger.error("Unexpected error in get_tree_data endpoint.", tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, "Error fetching tree data for visualization.")
        raise
