# backend/blueprints/admin.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort

from ..decorators import require_admin
from ..services.user_service import get_all_users_db, delete_user_db, update_user_role_db
from ..utils import get_pagination_params # For pagination

logger = structlog.get_logger(__name__)
admin_bp = Blueprint('admin_api', __name__, url_prefix='/api/users') # Base prefix for user admin

@admin_bp.route('', methods=['GET'])
@require_admin
def get_all_users_endpoint():
    """Admin endpoint to get a paginated list of all users."""
    db = g.db
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "username" # Default sort for users
    
    logger.info("Admin: Get all users request", page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
    try:
        users_page = get_all_users_db(db, page, per_page, sort_by, sort_order)
        return jsonify(users_page), 200
    except Exception as e: # Catch any unexpected error from service layer if not HTTPException
        logger.error("Admin: Unexpected error in get_all_users endpoint.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching all users.")


@admin_bp.route('/<uuid:user_id_param>', methods=['DELETE'])
@require_admin
def delete_user_endpoint(user_id_param: uuid.UUID):
    """Admin endpoint to delete a user."""
    current_admin_user_id_str = session.get('user_id')
    
    if current_admin_user_id_str and uuid.UUID(current_admin_user_id_str) == user_id_param:
        logger.warning("Admin attempted to delete their own account.", admin_user_id=current_admin_user_id_str)
        abort(403, description="Administrators cannot delete their own account using this endpoint.")
    
    db = g.db
    logger.info("Admin: Delete user request", target_user_id=user_id_param, admin_user_id=current_admin_user_id_str)
    try:
        delete_user_db(db, user_id_param) # Service function handles _get_or_404 and integrity errors
        return '', 204
    except Exception as e:
        logger.error("Admin: Unexpected error in delete_user endpoint.", exc_info=True)
        # If delete_user_db doesn't raise HTTPException, wrap it
        if not isinstance(e, HTTPException):
             abort(500, description="An unexpected error occurred while deleting the user.")
        raise # Re-raise HTTPException


@admin_bp.route('/<uuid:user_id_param>/role', methods=['PUT'])
@require_admin
def set_user_role_endpoint(user_id_param: uuid.UUID):
    """Admin endpoint to set a user's role."""
    data = request.get_json()
    if not data or 'role' not in data:
        abort(400, description="The 'role' field (e.g., 'user', 'admin') is required.")
    
    new_role_str = data['role']
    current_admin_user_id_str = session.get('user_id')

    if current_admin_user_id_str and uuid.UUID(current_admin_user_id_str) == user_id_param:
        logger.warning("Admin attempted to change their own role.", admin_user_id=current_admin_user_id_str)
        abort(403, description="Administrators cannot change their own role via this endpoint.")
    
    db = g.db
    logger.info("Admin: Set user role request", target_user_id=user_id_param, new_role=new_role_str, admin_user_id=current_admin_user_id_str)
    try:
        updated_user_obj = update_user_role_db(db, user_id_param, new_role_str) # Service handles validation
        return jsonify(updated_user_obj), 200
    except Exception as e:
        logger.error("Admin: Unexpected error in set_user_role endpoint.", exc_info=True)
        if not isinstance(e, HTTPException):
            abort(500, description="An unexpected error occurred while setting the user role.")
        raise
