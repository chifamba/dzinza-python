# backend/blueprints/admin.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort

# Absolute imports from the app root
from decorators import require_admin
from services.user_service import get_all_users_db, delete_user_db, update_user_role_db
from utils import get_pagination_params # For pagination

logger = structlog.get_logger(__name__)
admin_bp = Blueprint('admin_api', __name__, url_prefix='/api/users')

@admin_bp.route('', methods=['GET'])
@require_admin
def get_all_users_endpoint():
    db = g.db
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "username"
    logger.info("Admin: Get all users", page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
    try:
        users_page = get_all_users_db(db, page, per_page, sort_by, sort_order)
        return jsonify(users_page), 200
    except Exception as e:
        logger.error("Admin: Error in get_all_users.", exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching all users.")
        raise

@admin_bp.route('/<uuid:user_id_param>', methods=['DELETE'])
@require_admin
def delete_user_endpoint(user_id_param: uuid.UUID):
    current_admin_id = session.get('user_id')
    if current_admin_id and uuid.UUID(current_admin_id) == user_id_param:
        abort(403, "Admins cannot delete their own account via this endpoint.")
    db = g.db
    logger.info("Admin: Delete user", target_user_id=user_id_param, admin_user_id=current_admin_id)
    try:
        delete_user_db(db, user_id_param)
        return '', 204
    except Exception as e:
        logger.error("Admin: Error deleting user.", exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error deleting user.")
        raise

@admin_bp.route('/<uuid:user_id_param>/role', methods=['PUT'])
@require_admin
def set_user_role_endpoint(user_id_param: uuid.UUID):
    data = request.get_json()
    if not data or 'role' not in data: abort(400, "'role' field is required.")
    new_role_str = data['role']
    current_admin_id = session.get('user_id')
    if current_admin_id and uuid.UUID(current_admin_id) == user_id_param:
        abort(403, "Admins cannot change their own role via this endpoint.")
    db = g.db
    logger.info("Admin: Set user role", target_user_id=user_id_param, new_role=new_role_str, admin_user_id=current_admin_id)
    try:
        updated_user = update_user_role_db(db, user_id_param, new_role_str)
        return jsonify(updated_user), 200
    except Exception as e:
        logger.error("Admin: Error setting user role.", exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error setting user role.")
        raise
